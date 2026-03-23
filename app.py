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
    "Sede Social": {"senha": "SSICS", "subs": ["Terraco", "1º Andar", "2º Andar"], "itens": ["Lampadas", "Piso", "Corrimãos", "Janelas", "Limpeza", "Pintura", "Estrutura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes", "Canteiro de Obras", "Patio Novo", "Pátio", "Estacionamento"], "itens": ["Piso", "Caixas de energia", "Lampadas/Iluminacao", "Estrutura", "Limpeza", "Pintura"]},
    "Flats": {"senha": "FLATS", "subs": ["Bloco A - Terreo", "Bloco A - 1º Andar", "Bloco A - 2º Andar", "Bloco A - 3º Andar", "Bloco A - 4º Andar", "Bloco A - Terraco", "Bloco A - Garagem", "Bloco B - Terreo", "Bloco B - 1º Andar", "Bloco B - 2º Andar", "Bloco B - 3º Andar", "Bloco B - 4º Andar", "Bloco B - Terraco", "Bloco B - Garagem"], "itens": ["Lampadas/Iluminacao", "Piso/Escadarias", "Pintura", "Limpeza", "Interfones", "Extintores"]},
    "Predios ADM": {"senha": "ADMICS", "subs": ["Secretaria Nautica", "Administracao Marina ICS", "1º andar (RH/TI)", "Predio Sala Radio", "Vestiários", "Deck de Madeira", "Portaria de Serviço"], "itens": ["Ar-condicionado", "Iluminacao", "Limpeza", "Mobiliario", "Pintura", "Portas/Vidros","Estrutura"]}
}

# --- 3. CONEXÃO E AUXILIARES ---
@st.cache_resource
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"].to_dict()
        if "private_key" in creds_info: creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scope))
    except: return None

client = get_gspread_client()
sheet_id = st.secrets["spreadsheet"]["id"]
sh = client.open_by_key(sheet_id)
worksheet = sh.get_worksheet(0)

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
        pdf.cell(190, 8, f"{r.get('Item', 'Item')} - {r.get('Status', 'Status')}", ln=True, fill=True)
        pdf.multi_cell(190, 5, f"Data: {r.get('Data','')}\nLocal: {r.get('Area','')} ({r.get('Subdivisao','')})\nResolvido: {r.get('Resolvido','N/A')}\nObs Acomp: {r.get('Obs_Acompanhamento','')}\n")
        pdf.ln(2)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def formatar_corpo_email(df):
    corpo = "RELATORIO DE ZELADORIA\n\n"
    for _, r in df.iterrows():
        status_txt = r.get('Status', 'N/A')
        simbolo = "[OK]" if status_txt == "Conforme" else "[!]" if status_txt == "Não Conforme" else "[-]"
        corpo += f"{simbolo} {r.get('Item', '')}: {status_txt}\n   Resolvido: {r.get('Resolvido', 'N/A')}\n   Andamento: {r.get('Obs_Acompanhamento', '')}\n\n"
    return corpo

# --- 4. TELA INICIAL ---
hoje_br = get_data_hora_brasil()
dia_semana_idx = hoje_br.weekday()

st.title("🏛️ Zelador Virtual")

if dia_semana_idx < 5:
    missao = INFO_CRONOGRAMA[dia_semana_idx]
    with st.container(border=True):
        st.subheader(f"📅 Missão de Hoje: {hoje_br.strftime('%A')}")
        st.info(f"📍 **Área:** {missao['area']} | **Locais:** {missao['detalhes']}")
else:
    st.success("🌴 Final de semana!")

st.divider()

menu = st.sidebar.radio("Navegação:", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    area_sugerida = INFO_CRONOGRAMA[dia_semana_idx]["area"] if dia_semana_idx < 5 else "Selecione..."
    nome_usuario = st.text_input("Nome do Inspetor:")
    lista_areas = ["Selecione..."] + list(AREAS.keys())
    idx_init = lista_areas.index(area_sugerida) if area_sugerida in lista_areas else 0
    area_sel = st.selectbox("Área Principal:", lista_areas, index=idx_init)

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox("Subdivisão:", AREAS[area_sel]["subs"])
            respostas_form = []
            for item in AREAS[area_sel]["itens"]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    status = st.radio(f"Situação {item}", ["Conforme", "Não Conforme", "N/A"], key=f"r_{item}", horizontal=True)
                    acao, obs, foto = "N/A", "", None
                    if status == "Não Conforme":
                        c1, c2 = st.columns(2)
                        with c1: acao = st.selectbox("Ação", ["Limpeza", "Reparo", "Troca", "Pintura"], key=f"ac_{item}")
                        with c2: obs = st.text_input("Obs Inicial", key=f"ob_{item}")
                        origem_foto = st.radio("Origem da foto:", ["Câmera", "Galeria"], key=f"ori_{item}", horizontal=True)
                        if origem_foto == "Câmera": foto = st.camera_input("Tirar Foto", key=f"cam_{item}")
                        else: foto = st.file_uploader("Escolher da Galeria", type=['jpg', 'jpeg', 'png'], key=f"gal_{item}")
                    respostas_form.append({"item": item, "status": status, "acao": acao, "obs": obs, "foto": foto})

            if st.button("🚀 SALVAR INSPEÇÃO", use_container_width=True):
                if not nome_usuario: st.error("Nome do inspetor obrigatório.")
                else:
                    with st.spinner("Gravando..."):
                        ts = hoje_br.strftime("%d/%m/%Y %H:%M")
                        # Colunas: Data, Usuario, Area, Subdivisao, Item, Status, Acao, Detalhes, Foto_Path, Resolvido, Obs_Acompanhamento
                        dados = [[ts, nome_usuario, area_sel, sub_area, r["item"], r["status"], r["acao"], r["obs"], preparar_foto(r["foto"]), "Não", ""] for r in respostas_form]
                        worksheet.append_rows(dados)
                        st.success("✅ Salvo com sucesso!")

elif menu == "Histórico":
    st.subheader("📂 Gestão de Não Conformidades")
    try:
        # Forçamos a atualização dos dados para garantir que ele veja a coluna K
        dados_brutos = worksheet.get_all_values()
        
        if len(dados_brutos) > 1:
            colunas = [c.strip() for c in dados_brutos[0]]
            df = pd.DataFrame(dados_brutos[1:], columns=colunas)
            df['Data_dt'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')

            # Verificação de segurança: se a coluna não vier no DataFrame, forçamos a existência dela
            if "Obs_Acompanhamento" not in df.columns:
                df["Obs_Acompanhamento"] = ""

            with st.expander("🔍 Filtros Avançados", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1: d_ini = st.date_input("Início", hoje_br.date().replace(day=1))
                with c2: d_fim = st.date_input("Fim", hoje_br.date())
                with c3: f_area = st.multiselect("Áreas:", df['Area'].unique().tolist(), default=df['Area'].unique().tolist())
                
                opcoes_filtro = ["Apenas Pendentes (Não Conforme)", "Apenas Resolvidos", "Todos os Registos"]
                f_resol = st.radio("Exibir no Histórico:", opcoes_filtro, index=0, horizontal=True)

            mask = (df['Data_dt'].dt.date >= d_ini) & (df['Data_dt'].dt.date <= d_fim) & (df['Area'].isin(f_area))
            
            if f_resol == "Apenas Pendentes (Não Conforme)":
                mask = mask & (df['Status'] == "Não Conforme") & (df['Resolvido'] == "Não")
            elif f_resol == "Apenas Resolvidos":
                mask = mask & (df['Resolvido'] == "Sim")
            
            df_f = df.loc[mask]

            if not df_f.empty:
                st.write(f"🔍 Registros encontrados: **{len(df_f)}**")
                ce1, ce2, ce3 = st.columns(3)
                ce1.download_button("📥 PDF", gerar_pdf(df_f), "relatorio.pdf", use_container_width=True)
                ce2.link_button("📲 WhatsApp", f"https://wa.me/", use_container_width=True)
                ce3.link_button("📧 E-mail", f"mailto:?body={urllib.parse.quote(formatar_corpo_email(df_f))}", use_container_width=True)
                
                st.divider()
                for index, row in df_f.iloc[::-1].iterrows():
                    emoji = "✅" if row['Status'] == "Conforme" else "🔴" if row['Status'] == "Não Conforme" else "⚪"
                    txt_res = " (RESOLVIDO)" if row.get('Resolvido') == "Sim" else " (PENDENTE)" if row['Status'] == "Não Conforme" else ""
                    
                    with st.expander(f"{emoji}{txt_res} {row['Data']} - {row['Area']} - {row['Item']}"):
                        col_info, col_img = st.columns([2, 1])
                        with col_info:
                            st.write(f"**Local:** {row['Subdivisao']} | **Ação:** {row['Acao']}")
                            st.write(f"**Obs Inicial:** {row['Detalhes']}")
                            
                            # Campo de Observação
                            obs_atual = row.get('Obs_Acompanhamento', "")
                            # Usamos um formulário simples para o campo de texto para evitar recargas acidentais
                            with st.container():
                                nova_obs = st.text_area("Andamento / Observações Técnicas:", value=obs_atual, key=f"txt_{index}", height=100)
                                
                                ca1, ca2 = st.columns(2)
                                with ca1:
                                    if st.button("💾 Atualizar Observação", key=f"sav_{index}", use_container_width=True):
                                        # Lógica de salvamento robusta
                                        try:
                                            # Encontrar o índice da coluna K dinamicamente
                                            col_idx = colunas.index("Obs_Acompanhamento") + 1
                                            # index + 2 porque o pandas começa em 0 e a planilha tem cabeçalho
                                            worksheet.update_cell(index + 2, col_idx, str(nova_obs))
                                            st.success("Salvo com sucesso!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro técnico: {e}")
                                
                                with ca2:
                                    if row['Status'] == "Não Conforme" and row.get('Resolvido') == "Não":
                                        if st.button(f"✅ Marcar Regularizada", key=f"reg_{index}", use_container_width=True):
                                            col_res_idx = colunas.index("Resolvido") + 1
                                            worksheet.update_cell(index + 2, col_res_idx, "Sim")
                                            st.success("Regularizada!")
                                            st.rerun()

                        with col_img:
                            f_data = row.get('Foto_Path', row.get('Foto', ""))
                            if f_data and len(str(f_data)) > 100:
                                st.image(base64.b64decode(f_data), use_container_width=True)
            else:
                st.info("Nenhum item encontrado.")
    except Exception as e:
        st.error(f"Erro geral: {e}")
