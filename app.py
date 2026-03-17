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

# --- 2. CONFIGURAÇÃO DE FUSO HORÁRIO E CRONOGRAMA ---
def get_data_hora_brasil():
    fuso_brasil = timezone(timedelta(hours=-3))
    return datetime.now(fuso_brasil)

# 0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta
CRONOGRAMA = {
    0: "Sede Social",
    1: "Operacional",
    2: "Flats",
    3: "Predios ADM",
    4: "Operacional" # Segunda parte ou revisão
}

# --- 3. CONEXÃO GOOGLE SHEETS ---
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"].to_dict()
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Erro na conexão com Google Sheets: {e}")
        return None

client = get_gspread_client()
sheet_id = st.secrets["spreadsheet"]["id"]
sh = client.open_by_key(sheet_id)
worksheet = sh.get_worksheet(0)

# --- 4. PROCESSAMENTO DE IMAGEM ---
def preparar_foto_para_planilha(foto_file):
    if foto_file is None: return ""
    try:
        img = Image.open(foto_file)
        img = ImageOps.exif_transpose(img) 
        img.thumbnail((400, 400)) 
        buffer = BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=40)
        return base64.b64encode(buffer.getvalue()).decode()
    except: return ""

# --- 5. FUNÇÕES DE RELATÓRIO ---
def gerar_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatorio de Zeladoria", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    agora_br = get_data_hora_brasil().strftime('%d/%m/%Y %H:%M')
    pdf.cell(190, 10, f"Gerado em: {agora_br}", ln=True, align="C")
    pdf.ln(10)

    for _, row in dataframe.iterrows():
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 8, f"Item: {row['Item']} - {row['Status']}", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(190, 6, f"Data: {row['Data']}\nLocal: {row['Area']} ({row['Subdivisao']})\nInspetor: {row['Usuario']}\nAcao: {row['Acao']}\nObs: {row['Detalhes']}")
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def formatar_corpo_email(dataframe):
    agora_br = get_data_hora_brasil().strftime('%d/%m/%Y %H:%M')
    corpo = f"RELATORIO DE ZELADORIA - {agora_br}\n" + "-"*30 + "\n\n"
    for _, r in dataframe.iterrows():
        simbolo = " [!] " if r['Status'] == "Não Conforme" else " [OK] "
        corpo += f"{simbolo} {r['Item']}: {r['Status']}\n   Local: {r['Area']} ({r['Subdivisao']})\n   Ação: {r['Acao']}\n   Obs: {r['Detalhes']}\n\n"
    return corpo

# --- 6. ESTRUTURA DE DADOS ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS", 
        "subs": ["Terraco", "1º Andar", "2º Andar"], 
        "itens": ["Lampadas", "Piso", "Corrimoes", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS", 
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes", "Canteiro de Obras", "Patio Novo"],
        "itens": ["Piso", "Caixas de energia", "Lampadas/Iluminacao", "Estrutura", "Limpeza", "Pintura"]
    },
    "Flats": {
        "senha": "FLATS",
        "subs": [
            "Bloco A - Terreo", "Bloco A - 1º Andar", "Bloco A - 2º Andar", "Bloco A - 3º Andar", "Bloco A - 4º Andar", "Bloco A - Terraco", "Bloco A - Garagem",
            "Bloco B - Terreo", "Bloco B - 1º Andar", "Bloco B - 2º Andar", "Bloco B - 3º Andar", "Bloco B - 4º Andar", "Bloco B - Terraco", "Bloco B - Garagem"
        ],
        "itens": ["Lampadas/Iluminacao", "Piso/Escadarias", "Pintura", "Limpeza", "Interfones", "Extintores"]
    },
    "Predios ADM": {
        "senha": "ADMICS",
        "subs": ["Secretaria Nautica", "Administracao Marina ICS", "1º andar (RH/TI)", "Predio Sala Radio"],
        "itens": ["Ar-condicionado", "Iluminacao", "Limpeza", "Mobiliario", "Pintura", "Portas/Vidros"]
    }
}

# --- 7. INTERFACE ---
st.title("🏛️ Zelador Virtual")

# Lógica do Cronograma
hoje_br = get_data_hora_brasil()
dia_semana = hoje_br.weekday()
area_sugerida = CRONOGRAMA.get(dia_semana, "Livre")

with st.sidebar:
    st.header("📅 Cronograma")
    if dia_semana < 5:
        st.warning(f"**Hoje é {hoje_br.strftime('%A')}**\n\nFoco: **{area_sugerida}**")
    else:
        st.success("Fim de semana! Planeje a próxima segunda.")
    
    st.divider()
    menu = st.radio("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.subheader("📝 Nova Verificação")
    nome_usuario = st.text_input("Nome do Inspetor:")
    
    # Pre-seleção baseada no dia
    lista_opcoes = ["Selecione..."] + list(AREAS.keys())
    idx_sugerido = lista_opcoes.index(area_sugerida) if area_sugerida in lista_opcoes else 0
    
    area_sel = st.selectbox("Área Principal:", lista_opcoes, index=idx_sugerido)

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha da Área:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox("Subdivisão:", AREAS[area_sel]["subs"])
            st.divider()
            
            respostas_temp = []
            for item in AREAS[area_sel]["itens"]:
                with st.container(border=True):
                    st.subheader(f"📍 {item}")
                    status = st.radio(f"Situação {item}:", ["Conforme", "Não Conforme"], key=f"st_{item}", horizontal=True)
                    acao, obs, foto = "N/A", "", None
                    
                    if status == "Não Conforme":
                        c1, c2 = st.columns(2)
                        with c1: acao = st.selectbox("Ação:", ["Limpeza", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        with c2: obs = st.text_input("Obs:", key=f"ob_{item}")
                        
                        ori = st.radio("Origem da foto:", ["Câmera", "Galeria"], key=f"ori_{item}", horizontal=True)
                        if ori == "Câmera":
                            foto = st.camera_input(f"Foto {item}", key=f"cam_{item}")
                        else:
                            foto = st.file_uploader(f"Anexar {item}", type=["jpg","png","jpeg"], key=f"fl_{item}")
                    
                    respostas_temp.append({"Item": item, "Status": status, "Acao": acao, "Detalhes": obs, "Foto": foto})

            if st.button("🚀 FINALIZAR E SALVAR", use_container_width=True):
                if not nome_usuario:
                    st.error("Por favor, preencha o nome do inspetor.")
                else:
                    with st.spinner("Salvando inspeção..."):
                        dados_salvar = []
                        timestamp = get_data_hora_brasil().strftime("%d/%m/%Y %H:%M")
                        for r in respostas_temp:
                            f_txt = preparar_foto_para_planilha(r["Foto"])
                            dados_salvar.append([timestamp, nome_usuario, area_sel, sub_area, r["Item"], r["Status"], r["Acao"], r["Detalhes"], f_txt])
                        
                        worksheet.append_rows(dados_salvar)
                        st.success("✅ Inspeção salva com sucesso!")
                        
                        # Opções de compartilhamento imediato
                        st.divider()
                        st.subheader("📦 Compartilhar agora:")
                        df_atual = pd.DataFrame(dados_salvar, columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Acao", "Detalhes", "Foto_Path"])
                        c1, c2, c3 = st.columns(3)
                        c1.download_button("📥 PDF", gerar_pdf(df_atual), "inspecao.pdf")
                        c2.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(f'Inspeção finalizada: {area_sel} ({sub_area})')}")
                        c3.link_button("📧 E-mail", f"mailto:?subject=Inspecao&body={urllib.parse.quote(formatar_corpo_email(df_atual))}")

elif menu == "Histórico":
    st.header("📂 Histórico Cloud")
    try:
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            df['Data_dt'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            
            with st.expander("🔍 Filtros de Busca e Relatórios", expanded=True):
                f1, f2, f3 = st.columns(3)
                hoje_br_date = get_data_hora_brasil().date()
                with f1: d_ini = st.date_input("Início", hoje_br_date.replace(day=1))
                with f2: d_fim = st.date_input("Fim", hoje_br_date)
                with f3: stt = st.multiselect("Status", ["Conforme", "Não Conforme"], default=["Conforme", "Não Conforme"])
                
                f4, f5 = st.columns(2)
                with f4: a_sel = st.multiselect("Áreas:", list(AREAS.keys()), default=list(AREAS.keys()))
                with f5:
                    op_subs = []
                    for a in a_sel: op_subs.extend(AREAS[a]["subs"])
                    s_sel = st.multiselect("Subdivisões:", op_subs, default=op_subs)

                mask = (df['Data_dt'].dt.date >= d_ini) & (df['Data_dt'].dt.date <= d_fim) & \
                       (df['Status'].isin(stt)) & (df['Area'].isin(a_sel)) & (df['Subdivisao'].isin(s_sel))
                df_f = df.loc[mask]

                if not df_f.empty:
                    st.divider()
                    st.write(f"📊 **{len(df_f)}** registros encontrados.")
                    cp, cw, ce = st.columns(3)
                    cp.download_button("📥 Baixar PDF Filtrado", gerar_pdf(df_f), "relatorio_geral.pdf")
                    cw.link_button("📲 WhatsApp", f"https://wa.me/?text=Relatorio")
                    ce.link_button("📧 E-mail Detalhado", f"mailto:?subject=Relatorio&body={urllib.parse.quote(formatar_corpo_email(df_f))}")

            for _, row in df_f.iloc[::-1].iterrows():
                emoji = "✅" if row['Status'] == "Conforme" else "🔴"
                with st.expander(f"{emoji} {row['Data']} - {row['Area']} ({row['Subdivisao']})"):
                    col_t, col_i = st.columns([2, 1])
                    with col_t:
                        st.write(f"**Item:** {row['Item']}\n**Inspetor:** {row['Usuario']}")
                        st.write(f"**Ação:** {row['Acao']}\n**Observação:** {row['Detalhes']}")
                    with col_i:
                        f_b64 = row.get('Foto_Path', "")
                        if f_b64 and len(str(f_b64)) > 100:
                            st.image(base64.b64decode(f_b64), use_container_width=True)
        else:
            st.info("Planilha vazia.")
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
