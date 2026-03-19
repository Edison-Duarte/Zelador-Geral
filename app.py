import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone
import base64
from io import BytesIO
from PIL import Image, ImageOps
from fpdf import FPDF
import urllib.parse

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

# --- 2. FUSO HORÁRIO E CRONOGRAMA ---
def get_data_hora_brasil():
    fuso_brasil = timezone(timedelta(hours=-3))
    return datetime.now(fuso_brasil)

INFO_CRONOGRAMA = {
    0: {"area": "Sede Social", "detalhes": "Terraço, 1º Andar e 2º Andar."},
    1: {"area": "Operacional", "detalhes": "Cais, Bacia IV, Hangares 1-7 e Boxes."},
    2: {"area": "Flats", "detalhes": "Blocos A e B (Garagens, Pisos e Terraços)."},
    3: {"area": "Predios ADM", "detalhes": "Secretaria, Adm, RH/TI e Sala do Rádio."},
    4: {"area": "Operacional", "detalhes": "Canteiro de Obras e Pátio Novo."}
}

AREAS = {
    "Sede Social": {"senha": "SSICS", "subs": ["Terraco", "1º Andar", "2º Andar"], "itens": ["Lampadas", "Piso", "Corrimoes", "Janelas", "Limpeza", "Pintura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes", "Canteiro de Obras", "Patio Novo"], "itens": ["Piso", "Caixas de energia", "Lampadas/Iluminacao", "Estrutura", "Limpeza", "Pintura"]},
    "Flats": {"senha": "FLATS", "subs": ["Bloco A - Terreo", "Bloco A - 1º Andar", "Bloco A - 2º Andar", "Bloco A - 3º Andar", "Bloco A - 4º Andar", "Bloco A - Terraco", "Bloco A - Garagem", "Bloco B - Terreo", "Bloco B - 1º Andar", "Bloco B - 2º Andar", "Bloco B - 3º Andar", "Bloco B - 4º Andar", "Bloco B - Terraco", "Bloco B - Garagem"], "itens": ["Lampadas/Iluminacao", "Piso/Escadarias", "Pintura", "Limpeza", "Interfones", "Extintores"]},
    "Predios ADM": {"senha": "ADMICS", "subs": ["Secretaria Nautica", "Administracao Marina ICS", "1º andar (RH/TI)", "Predio Sala Radio"], "itens": ["Ar-condicionado", "Iluminacao", "Limpeza", "Mobiliario", "Pintura", "Portas/Vidros"]}
}

# --- 3. FUNÇÕES AUXILIARES ---
@st.cache_resource
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"].to_dict()
        if "private_key" in creds_info: creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scope))
    except: return None

def preparar_foto(foto_file):
    if foto_file is None: return ""
    try:
        img = Image.open(foto_file)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((400, 400))
        buffer = BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=40)
        return base64.b64encode(buffer.getvalue()).decode()
    except: return ""

def gerar_pdf(df):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "Relatorio de Zeladoria", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    for _, r in df.iterrows():
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(190, 8, f"{r['Item']} - {r['Status']}", ln=True, fill=True)
        pdf.multi_cell(190, 5, f"Local: {r['Area']} ({r['Subdivisao']})\nAcao: {r['Acao']}\nObs: {r['Detalhes']}\n")
        pdf.ln(2)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def formatar_corpo_email(df):
    corpo = "RELATORIO DE ZELADORIA\n\n"
    for _, r in df.iterrows():
        status_txt = r['Status']
        simbolo = "[OK]" if status_txt == "Conforme" else "[!]" if status_txt == "Não Conforme" else "[-]"
        corpo += f"{simbolo} {r['Item']} ({r['Subdivisao']}): {status_txt}\nObs: {r['Detalhes']}\n\n"
    return corpo

# --- 4. CARREGAMENTO INICIAL ---
client = get_gspread_client()
sheet_id = st.secrets["spreadsheet"]["id"]
sh = client.open_by_key(sheet_id)
worksheet = sh.get_worksheet(0)

# --- 5. TELA INICIAL (MISSÃO DO DIA) ---
hoje_br = get_data_hora_brasil()
dia_semana_idx = hoje_br.weekday()

st.title("🏛️ Zelador Virtual")

if dia_semana_idx < 5:
    missao = INFO_CRONOGRAMA[dia_semana_idx]
    with st.container(border=True):
        st.subheader(f"📅 Missão de Hoje: {hoje_br.strftime('%A')}")
        st.info(f"📍 **Inspecionar:** {missao['area']}\n\n🔍 **Locais:** {missao['detalhes']}")
else:
    st.success("🌴 Final de semana! Sem inspeções obrigatórias.")

st.divider()

# --- 6. MENU LATERAL ---
menu = st.sidebar.radio("Navegação:", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    area_sugerida = INFO_CRONOGRAMA[dia_semana_idx]["area"] if dia_semana_idx < 5 else "Selecione..."
    nome_usuario = st.text_input("Nome do Inspetor:")
    lista_areas = ["Selecione..."] + list(AREAS.keys())
    idx_init = lista_areas.index(area_sugerida) if area_sugerida in lista_areas else 0
    area_sel = st.selectbox("Área Principal:", lista_areas, index=idx_init)

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha da Área:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox("Subdivisão:", AREAS[area_sel]["subs"])
            respostas_form = []
            
            for item in AREAS[area_sel]["itens"]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    # ADICIONADO N/A AQUI
                    status = st.radio(f"Situação {item}", ["Conforme", "Não Conforme", "N/A"], key=f"rad_{item}", horizontal=True)
                    acao, obs, foto = "N/A", "", None
                    
                    if status == "Não Conforme":
                        c1, c2 = st.columns(2)
                        with c1: acao = st.selectbox("Ação", ["Limpeza", "Reparo", "Troca", "Pintura"], key=f"ac_{item}")
                        with c2: obs = st.text_input("Obs", key=f"ob_{item}")
                        ori = st.radio("Foto", ["Câmera", "Galeria"], key=f"or_{item}", horizontal=True)
                        foto = st.camera_input("Foto", key=f"cp_{item}") if ori == "Câmera" else st.file_uploader("Arquivo", type=['jpg','png'], key=f"up_{item}")
                    
                    respostas_form.append({"item": item, "status": status, "acao": acao, "obs": obs, "foto": foto})

            if st.button("🚀 FINALIZAR E SALVAR", use_container_width=True):
                if not nome_usuario:
                    st.error("Por favor, introduza o nome do inspetor.")
                else:
                    with st.spinner("Gravando na base de dados..."):
                        ts = hoje_br.strftime("%d/%m/%Y %H:%M")
                        dados_para_sheet = []
                        for r in respostas_form:
                            f_txt = preparar_foto(r["foto"])
                            dados_para_sheet.append([ts, nome_usuario, area_sel, sub_area, r["item"], r["status"], r["acao"], r["obs"], f_txt])
                        
                        worksheet.append_rows(dados_para_sheet)
                        st.success("✅ Inspeção salva com sucesso!")
                        
                        df_at = pd.DataFrame(dados_para_sheet, columns=["Data","Usuario","Area","Subdivisao","Item","Status","Acao","Detalhes","Foto"])
                        c1, c2, c3 = st.columns(3)
                        c1.download_button("📥 PDF", gerar_pdf(df_at), "inspecao.pdf")
                        c2.link_button("📲 WhatsApp", f"https://wa.me/?text=Inspecao%20Concluida")
                        c3.link_button("📧 E-mail", f"mailto:?subject=Inspecao&body={urllib.parse.quote(formatar_corpo_email(df_at))}")

elif menu == "Histórico":
    st.subheader("📂 Consulta de Registos")
    try:
        # MÉTODO ROBUSTO DE LEITURA
        dados_brutos = worksheet.get_all_values()
        if len(dados_brutos) > 1:
            df = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
            df['Data_dt'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')

            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                with c1: d_ini = st.date_input("De:", hoje_br.date().replace(day=1))
                with c2: d_fim = st.date_input("Até:", hoje_br.date())
                # FILTRO DE STATUS ATUALIZADO
                with c3: f_status = st.multiselect("Status:", ["Conforme", "Não Conforme", "N/A"], default=["Conforme", "Não Conforme", "N/A"])
                
                c4, c5 = st.columns(2)
                areas_unicas = df['Area'].unique().tolist()
                with c4: f_area = st.multiselect("Áreas:", areas_unicas, default=areas_unicas)
                with c5:
                    subs_unicas = df[df['Area'].isin(f_area)]['Subdivisao'].unique().tolist()
                    f_sub = st.multiselect("Subdivisões:", subs_unicas, default=subs_unicas)

            # APLICAÇÃO DOS FILTROS
            mask = (df['Data_dt'].dt.date >= d_ini) & (df['Data_dt'].dt.date <= d_fim) & \
                   (df['Status'].isin(f_status)) & (df['Area'].isin(f_area)) & (df['Subdivisao'].isin(f_sub))
            df_f = df.loc[mask]

            if not df_f.empty:
                st.write(f"🔍 Encontrados **{len(df_f)}** registos.")
                st.divider()
                
                for _, row in df_f.iloc[::-1].iterrows():
                    # Lógica de ícone
                    emoji = "✅" if row['Status'] == "Conforme" else "🔴" if row['Status'] == "Não Conforme" else "⚪"
                    with st.expander(f"{emoji} {row['Data']} - {row['Area']} ({row['Subdivisao']})"):
                        st.write(f"**Item:** {row['Item']} | **Status:** {row['Status']}")
                        st.write(f"**Inspetor:** {row['Usuario']} | **Ação:** {row['Acao']}")
                        if row['Detalhes']: st.write(f"**Observação:** {row['Detalhes']}")
                        
                        # Recuperar foto (tenta Foto ou Foto_Path)
                        foto_val = row.get('Foto_Path', row.get('Foto', ""))
                        if foto_val and len(str(foto_val)) > 100:
                            st.image(base64.b64decode(foto_val), width=350)
            else:
                st.info("Nenhum dado encontrado para os filtros aplicados.")
        else:
            st.info("A base de dados ainda não possui registos.")
    except Exception as e:
        st.error(f"Erro ao carregar o histórico: {e}")
