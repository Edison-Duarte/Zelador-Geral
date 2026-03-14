import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image, ImageOps
from fpdf import FPDF
import urllib.parse

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

# --- 2. CONEXÃO GOOGLE SHEETS ---
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"].to_dict()
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return None

client = get_gspread_client()
sheet_id = st.secrets["spreadsheet"]["id"]
sh = client.open_by_key(sheet_id)
worksheet = sh.get_worksheet(0)

# --- 3. PROCESSAMENTO DE IMAGEM ---
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

# --- 4. FUNÇÃO PARA GERAR PDF ---
def gerar_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatório de Zeladoria", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    for _, row in dataframe.iterrows():
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 8, f"Item: {row['Item']} - {row['Status']}", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(190, 6, f"Data: {row['Data']}\nLocal: {row['Area']} ({row['Subdivisao']})\nInspetor: {row['Usuario']}\nAção: {row['Acao']}\nObs: {row['Detalhes']}")
        pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 5. INTERFACE ---
AREAS = {
    "Sede Social": {"senha": "SSICS", "subs": ["Terraço", "1º Andar", "2º Andar"], "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"], "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]}
}

st.title("🏛️ Zelador Virtual")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    nome_usuario = st.text_input("Nome do Inspetor:")
    area_sel = st.selectbox("Área Principal:", ["Selecione..."] + list(AREAS.keys()))

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox("Subdivisão:", AREAS[area_sel]["subs"])
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
                        origem = st.radio("Origem foto:", ["Câmera", "Galeria"], key=f"ori_{item}", horizontal=True)
                        foto = st.camera_input(f"Foto {item}", key=f"cam_{item}") if origem == "Câmera" else st.file_uploader(f"Arquivo {item}", type=["jpg","png"], key=f"fl_{item}")
                    respostas_temp.append({"Item": item, "Status": status, "Acao": acao, "Detalhes": obs, "Foto": foto})

            if st.button("🚀 FINALIZAR"):
                with st.spinner("Gravando..."):
                    dados = []
                    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                    for r in respostas_temp:
                        foto_txt = preparar_foto_para_planilha(r["Foto"])
                        dados.append([agora, nome_usuario, area_sel, sub_area, r["Item"], r["Status"], r["Acao"], r["Detalhes"], foto_txt])
                    worksheet.append_rows(dados)
                    st.success("Salvo!")

elif menu == "Histórico":
    st.header("📂 Histórico Filtrado")
    try:
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            df['Data_dt'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M", errors='coerce')
            
            with st.expander("🔍 Filtros e Exportação", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1: data_inicio = st.date_input("Início", datetime.now().replace(day=1))
                with c2: data_fim = st.date_input("Fim", datetime.now())
                with c3: filtro_status = st.multiselect("Status", ["Conforme", "Não Conforme"], default=["Conforme", "Não Conforme"])
                
                df_f = df[(df['Data_dt'].dt.date >= data_inicio) & (df['Data_dt'].dt.date <= data_fim) & (df['Status'].isin(filtro_status))]
                
                # --- BOTÕES DE EXPORTAÇÃO ---
                st.divider()
                col_pdf, col_wpp, col_mail = st.columns(3)
                
                if not df_f.empty:
                    # PDF
                    pdf_bytes = gerar_pdf(df_f)
                    col_pdf.download_button("📥 Baixar PDF", data=pdf_bytes, file_name="relatorio_zeladoria.pdf", mime="application/pdf")
                    
                    # WHATSAPP
                    msg_wpp = f"Relatório de Zeladoria ({data_inicio} a {data_fim}): {len(df_f)} itens registrados."
                    link_wpp = f"https://wa.me/?text={urllib.parse.quote(msg_wpp)}"
                    col_wpp.link_button("📲 Enviar Resumo via WhatsApp", link_wpp)
                    
                    # EMAIL
                    corpo_email = f"Relatorio de Zeladoria\nPeriodo: {data_inicio} a {data_fim}\nItens: {len(df_f)}"
                    link_mail = f"mailto:?subject=Relatorio Zeladoria&body={urllib.parse.quote(corpo_email)}"
                    col_mail.link_button("📧 Enviar por E-mail", link_mail)

            for _, row in df_f.iloc[::-1].iterrows():
                emoji = "✅" if row['Status'] == "Conforme" else "🔴"
                with st.expander(f"{emoji} {row['Data']} - {row['Item']}"):
                    c_info, c_img = st.columns([2, 1])
                    with c_info:
                        st.write(f"**Status:** {row['Status']} | **Inspetor:** {row['Usuario']}\n\n**Obs:** {row['Detalhes']}")
                    with c_img:
                        f_b64 = row.get('Foto_Path', "")
                        if f_b64 and len(str(f_b64)) > 100:
                            st.image(base64.b64decode(f_b64), use_container_width=True)
    except Exception as e:
        st.error(f"Erro: {e}")
