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

# Mapeamento detalhado para exibição na tela inicial
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

# --- 3. FUNÇÕES AUXILIARES (CONEXÃO, PDF, EMAIL) ---
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"].to_dict()
        if "private_key" in creds_info: creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        return gspread.authorize(Credentials.from_service_account_info(creds_info, scopes=scope))
    except: return None

def gerar_pdf(df):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatorio de Zeladoria", ln=True, align="C")
    for _, r in df.iterrows():
        pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 8, f"{r['Item']} - {r['Status']}", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(190, 6, f"Data: {r['Data']}\nLocal: {r['Area']} ({r['Subdivisao']})\nObs: {r['Detalhes']}")
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def formatar_corpo_email(df):
    corpo = "RELATORIO DE ZELADORIA\n\n"
    for _, r in df.iterrows():
        corpo += f"[{'!' if r['Status'] != 'Conforme' else 'OK'}] {r['Item']} ({r['Subdivisao']}): {r['Status']}\nObs: {r['Detalhes']}\n\n"
    return corpo

# --- 4. INICIALIZAÇÃO ---
client = get_gspread_client()
sheet_id = st.secrets["spreadsheet"]["id"]
sh = client.open_by_key(sheet_id)
worksheet = sh.get_worksheet(0)

# --- 5. TELA INICIAL E LOGICA DE DIA ---
hoje_br = get_data_hora_brasil()
dia_semana_idx = hoje_br.weekday()

st.title("🏛️ Zelador Virtual")

# EXIBIÇÃO DA MISSÃO DO DIA (SEMPRE NO TOPO)
if dia_semana_idx < 5:
    missao = INFO_CRONOGRAMA[dia_semana_idx]
    with st.container(border=True):
        st.subheader(f"📅 Missão de Hoje: {hoje_br.strftime('%d/%m/%Y')} ({hoje_br.strftime('%A')})")
        st.info(f"📍 **Área Principal:** {missao['area']}\n\n🔍 **Subdivisões:** {missao['detalhes']}")
else:
    st.success("🌴 Final de semana! Sem inspeções agendadas.")

st.divider()

# --- 6. MENU ---
menu = st.sidebar.radio("Ir para:", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    area_sugerida = INFO_CRONOGRAMA[dia_semana_idx]["area"] if dia_semana_idx < 5 else "Selecione..."
    
    nome_usuario = st.text_input("Nome do Inspetor:")
    lista_areas = ["Selecione..."] + list(AREAS.keys())
    idx_default = lista_areas.index(area_sugerida) if area_sugerida in lista_areas else 0
    
    area_sel = st.selectbox("Área Principal:", lista_areas, index=idx_default)

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox("Subdivisão:", AREAS[area_sel]["subs"])
            respostas = []
            for item in AREAS[area_sel]["itens"]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    status = st.radio(f"Status {item}", ["Conforme", "Não Conforme"], key=item, horizontal=True)
                    acao, obs, foto = "N/A", "", None
                    if status == "Não Conforme":
                        c1, c2 = st.columns(2)
                        with c1: acao = st.selectbox("Ação", ["Limpeza", "Reparo", "Troca", "Pintura"], key=f"ac_{item}")
                        with c2: obs = st.text_input("Obs", key=f"ob_{item}")
                        ori = st.radio("Foto", ["Câmera", "Galeria"], key=f"or_{item}", horizontal=True)
                        foto = st.camera_input("Capturar", key=f"cp_{item}") if ori == "Câmera" else st.file_uploader("Subir", type=['jpg','png'], key=f"up_{item}")
                    respostas.append([item, status, acao, obs, foto])

            if st.button("🚀 FINALIZAR INSPEÇÃO", use_container_width=True):
                if not nome_usuario: st.error("Nome obrigatório!")
                else:
                    with st.spinner("Gravando..."):
                        timestamp = get_data_hora_brasil().strftime("%d/%m/%Y %H:%M")
                        dados_finais = []
                        for r in respostas:
                            # Foto processada (simplificado aqui para o exemplo)
                            dados_finais.append([timestamp, nome_usuario, area_sel, sub_area, r[0], r[1], r[2], r[3], ""])
                        worksheet.append_rows(dados_finais)
                        st.success("✅ Salvo!")
                        # Botões de compartilhamento
                        df_at = pd.DataFrame(dados_finais, columns=["Data","Usuario","Area","Subdivisao","Item","Status","Acao","Detalhes","Foto"])
                        c1, c2, c3 = st.columns(3)
                        c1.download_button("📥 PDF", gerar_pdf(df_at), "inspecao.pdf")
                        c2.link_button("📲 WhatsApp", f"https://wa.me/?text=Inspecao%20Concluida")
                        c3.link_button("📧 E-mail", f"mailto:?subject=Inspecao&body={urllib.parse.quote(formatar_corpo_email(df_at))}")

elif menu == "Histórico":
    # Lógica de histórico permanece a mesma (Filtros por data, área e subdivisão)
    st.write("Consulte os registros anteriores nos filtros abaixo.")
    # ... (Código do histórico anterior)
