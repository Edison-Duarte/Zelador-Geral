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

# --- 4. FUNÇÕES DE RELATÓRIO (PDF E E-MAIL) ---
def gerar_pdf(dados_inspecao):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatório de Inspeção Individual", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    for item in dados_inspecao:
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 8, f"Item: {item[4]} - {item[5]}", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(190, 6, f"Local: {item[2]} ({item[3]})\nInspetor: {item[1]}\nAção: {item[6]}\nObs: {item[7]}")
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def formatar_corpo_email(dados_inspecao):
    corpo = "RELATÓRIO DE INSPEÇÃO RECENTE\n" + "-"*30 + "\n\n"
    for item in dados_inspecao:
        simbolo = " [!] " if item[5] == "Não Conforme" else " [OK] "
        corpo += f"{simbolo} {item[4]}: {item[5]}\n   Ação: {item[6]}\n   Obs: {item[7]}\n\n"
    corpo += f"\nGerado via Zelador Virtual."
    return corpo

# --- 5. INTERFACE ---
AREAS = {
    "Sede Social": {"senha": "SSICS", "subs": ["Terraço", "1º Andar", "2º Andar"], "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"], "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]}
}

menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.title("🏛️ Nova Inspeção")
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
                        foto = st.camera_input(f"Capturar {item}", key=f"cam_{item}") if origem == "Câmera" else st.file_uploader(f"Anexar {item}", type=["jpg","png"], key=f"fl_{item}")
                    respostas_temp.append({"Item": item, "Status": status, "Acao": acao, "Detalhes": obs, "Foto": foto})

            if st.button("🚀 FINALIZAR", use_container_width=True):
                if not nome_usuario:
                    st.error("Digite o nome do inspetor.")
                else:
                    with st.spinner("Gravando..."):
                        dados_para_salvar = []
                        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                        for r in respostas_temp:
                            foto_txt = preparar_foto_para_planilha(r["Foto"])
                            dados_para_salvar.append([agora, nome_usuario, area_sel, sub_area, r["Item"], r["Status"], r["Acao"], r["Detalhes"], foto_txt])
                        
                        worksheet.append_rows(dados_para_salvar)
                        st.success("✅ Inspeção finalizada e salva!")
                        
                        # --- NOVAS OPÇÕES APÓS FINALIZAR ---
                        st.divider()
                        st.subheader("📦 Compartilhar esta Inspeção:")
                        c1, c2, c3 = st.columns(3)
                        
                        # PDF da inspeção atual
                        pdf_inspeção = gerar_pdf(dados_para_salvar)
                        c1.download_button("📥 Baixar PDF", pdf_inspeção, "inspecao.pdf", "application/pdf")
                        
                        # WhatsApp
                        msg_wpp = f"*Inspeção Realizada*\nInspetor: {nome_usuario}\nLocal: {area_sel}\nItens: {len(dados_para_salvar)}"
                        c2.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg_wpp)}")
                        
                        # E-mail
                        corpo_email = formatar_corpo_email(dados_para_salvar)
                        subj = urllib.parse.quote(f"Inspeção: {area_sel} - {agora}")
                        c3.link_button("📧 E-mail", f"mailto:?subject={subj}&body={urllib.parse.quote(corpo_email)}")

elif menu == "Histórico":
    st.title("📂 Histórico Cloud")
    try:
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            df['Data_dt'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M", errors='coerce')
            
            with st.expander("🔍 Filtros de Relatório"):
                c1, c2, c3 = st.columns(3)
                with c1: di = st.date_input("Início", datetime.now().replace(day=1))
                with c2: dfim = st.date_input("Fim", datetime.now())
                with c3: stt = st.multiselect("Status", ["Conforme", "Não Conforme"], default=["Conforme", "Não Conforme"])
                
                df_f = df[(df['Data_dt'].dt.date >= di) & (df['Data_dt'].dt.date <= dfim) & (df['Status'].isin(stt))]
                
                if not df_f.empty:
                    st.divider()
                    col_p, col_w, col_e = st.columns(3)
                    # Relatórios do Histórico (múltiplos itens)
                    dados_historico = df_f.values.tolist()
                    pdf_h = gerar_pdf(dados_historico)
                    col_p.download_button("📥 PDF Geral", pdf_h, "relatorio_geral.pdf")
                    col_w.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote('Relatorio Geral Disponivel')}")
                    col_e.link_button("📧 E-mail", f"mailto:?subject=Relatorio Geral&body={urllib.parse.quote(formatar_corpo_email(dados_historico))}")

            for _, row in df_f.iloc[::-1].iterrows():
                emoji = "✅" if row['Status'] == "Conforme" else "🔴"
                with st.expander(f"{emoji} {row['Data']} - {row['Item']}"):
                    c_i, c_p = st.columns([2, 1])
                    with c_i: st.write(f"**Inspetor:** {row['Usuario']}\n\n**Obs:** {row['Detalhes']}")
                    with c_p:
                        f_b64 = row.get('Foto_Path', "")
                        if f_b64 and len(str(f_b64)) > 100: st.image(base64.b64decode(f_b64), use_container_width=True)
    except Exception as e: st.error(f"Erro: {e}")
