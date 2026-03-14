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

# --- 4. FUNÇÕES DE RELATÓRIO ---
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

def formatar_corpo_email(dataframe):
    corpo = "RELATÓRIO DE ZELADORIA\n" + "-"*30 + "\n\n"
    for _, r in dataframe.iterrows():
        simbolo = " [!] " if r['Status'] == "Não Conforme" else " [OK] "
        corpo += f"{simbolo} {r['Item']}: {r['Status']}\n   Local: {r['Area']} ({r['Subdivisao']})\n   Obs: {r['Detalhes']}\n\n"
    return corpo

# --- 5. DADOS ---
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
                        ori = st.radio("Origem foto:", ["Câmera", "Galeria"], key=f"ori_{item}", horizontal=True)
                        foto = st.camera_input(f"Foto {item}", key=f"cam_{item}") if ori == "Câmera" else st.file_uploader(f"Anexar {item}", type=["jpg","png"], key=f"fl_{item}")
                    respostas_temp.append({"Item": item, "Status": status, "Acao": acao, "Detalhes": obs, "Foto": foto})

            if st.button("🚀 FINALIZAR"):
                if not nome_usuario: st.error("Preencha o nome.")
                else:
                    with st.spinner("Gravando..."):
                        dados_salvar = []
                        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                        for r in respostas_temp:
                            f_txt = preparar_foto_para_planilha(r["Foto"])
                            dados_salvar.append([agora, nome_usuario, area_sel, sub_area, r["Item"], r["Status"], r["Acao"], r["Detalhes"], f_txt])
                        worksheet.append_rows(dados_salvar)
                        st.success("✅ Salvo!")
                        st.divider()
                        st.subheader("📦 Compartilhar esta Inspeção:")
                        c1, c2, c3 = st.columns(3)
                        df_atual = pd.DataFrame(dados_salvar, columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Acao", "Detalhes", "Foto_Path"])
                        c1.download_button("📥 PDF", gerar_pdf(df_atual), "inspecao.pdf")
                        c2.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote('Inspeção realizada com sucesso.')}")
                        c3.link_button("📧 E-mail", f"mailto:?subject=Inspeção&body={urllib.parse.quote(formatar_corpo_email(df_atual))}")

elif menu == "Histórico":
    st.title("📂 Histórico Cloud")
    try:
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            df['Data_dt'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M", errors='coerce')
            
            with st.expander("🔍 Filtros de Busca e Relatório", expanded=True):
                # Primeira linha de filtros
                f1, f2, f3 = st.columns(3)
                with f1: data_ini = st.date_input("Início", datetime.now().replace(day=1))
                with f2: data_fim = st.date_input("Fim", datetime.now())
                with f3: f_status = st.multiselect("Status", ["Conforme", "Não Conforme"], default=["Conforme", "Não Conforme"])
                
                # Segunda linha de filtros (Áreas e Subdivisões)
                f4, f5 = st.columns(2)
                with f4:
                    f_area = st.multiselect("Filtrar Área Principal:", list(AREAS.keys()), default=list(AREAS.keys()))
                with f5:
                    # Subdivisões dinâmicas baseadas nas áreas escolhidas
                    opcoes_subs = []
                    for a in f_area:
                        opcoes_subs.extend(AREAS[a]["subs"])
                    f_sub = st.multiselect("Filtrar Subdivisões:", opcoes_subs, default=opcoes_subs)

                # Aplicação dos filtros
                mask = (df['Data_dt'].dt.date >= data_ini) & \
                       (df['Data_dt'].dt.date <= data_fim) & \
                       (df['Status'].isin(f_status)) & \
                       (df['Area'].isin(f_area)) & \
                       (df['Subdivisao'].isin(f_sub))
                df_f = df.loc[mask]

                if not df_f.empty:
                    st.divider()
                    st.write(f"📊 **{len(df_f)}** itens encontrados.")
                    c_pdf, c_wpp, c_mail = st.columns(3)
                    c_pdf.download_button("📥 PDF Filtrado", gerar_pdf(df_f), "relatorio_zeladoria.pdf")
                    msg_w = f"Relatório de Zeladoria: {len(df_f)} itens encontrados no período selecionado."
                    c_wpp.link_button("📲 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg_w)}")
                    c_mail.link_button("📧 E-mail Detalhado", f"mailto:?subject=Relatorio&body={urllib.parse.quote(formatar_corpo_email(df_f))}")

            # Exibição dos cards
            for _, row in df_f.iloc[::-1].iterrows():
                emoji = "✅" if row['Status'] == "Conforme" else "🔴"
                with st.expander(f"{emoji} {row['Data']} - {row['Area']} ({row['Subdivisao']}) - {row['Item']}"):
                    col_txt, col_img = st.columns([2, 1])
                    with col_txt:
                        st.write(f"**Inspetor:** {row['Usuario']}")
                        st.write(f"**Status:** {row['Status']}")
                        st.write(f"**Obs:** {row['Detalhes']}")
                    with col_img:
                        f_b64 = row.get('Foto_Path', "")
                        if f_b64 and len(str(f_b64)) > 100:
                            st.image(base64.b64decode(f_b64), use_container_width=True)
    except Exception as e: st.error(f"Erro ao carregar histórico: {e}")
