import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import base64
from io import BytesIO

# --- CONEXÃO SEGURA ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_gspread_client():
    creds_info = st.secrets["gcp_service_account"].to_dict()
    if "\\n" in creds_info["private_key"]:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(credentials)

client = get_gspread_client()
sheet_id = st.secrets["spreadsheet"]["id"]
sh = client.open_by_key(sheet_id)
worksheet = sh.get_worksheet(0)

# --- FUNÇÃO PARA CONVERTER FOTO EM TEXTO ---
def converter_foto_para_base64(foto_file):
    if foto_file is not None:
        return base64.b64encode(foto_file.getvalue()).decode()
    return ""

# --- CONFIGURAÇÃO ---
AREAS = {
    "Sede Social": {"senha": "SSICS", "subs": ["Terraço", "1º Andar", "2º Andar"], 
                    "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
                    "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]}
}

st.title("🏛️ Zelador Virtual - Cloud")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    nome_usuario = st.text_input("Nome do Inspetor:")
    area_sel = st.selectbox("Área Principal:", ["Selecione..."] + list(AREAS.keys()))

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
                        with c1: acao = st.selectbox("Ação:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        with c2: obs = st.text_input("Obs:", key=f"ob_{item}")
                        foto = st.file_uploader(f"📸 Foto de {item}", type=["jpg", "png", "jpeg"], key=f"ft_{item}")
                    
                    respostas_temp.append({"Item": item, "Status": status, "Acao": acao, "Detalhes": obs, "Foto": foto})

            if st.button("🚀 FINALIZAR E SALVAR NA PLANILHA"):
                if not nome_usuario:
                    st.error("Preencha o nome do inspetor.")
                else:
                    with st.spinner("Salvando dados e imagens..."):
                        dados_para_planilha = []
                        for r in respostas_temp:
                            # Converte a foto em texto aqui
                            foto_serializada = converter_foto_para_base64(r["Foto"])
                            
                            dados_para_planilha.append([
                                datetime.now().strftime("%d/%m/%Y %H:%M"),
                                nome_usuario, area_sel, sub_area,
                                r["Item"], r["Status"], r["Acao"], r["Detalhes"], foto_serializada
                            ])
                        
                        worksheet.append_rows(dados_para_planilha)
                        st.success("✅ Tudo salvo na planilha (incluindo fotos)!")
                        st.balloons()

elif menu == "Histórico":
    st.header("📂 Histórico com Fotos")
    records = worksheet.get_all_records()
    if not records:
        st.info("Nenhum dado encontrado.")
    else:
        df = pd.DataFrame(records)
        for idx, row in df.iloc[::-1].iterrows():
            emoji = "✅" if row['Status'] == "Conforme" else "🔴"
            with st.expander(f"{emoji} {row['Data']} - {row['Item']} ({row['Subdivisao']})"):
                col_txt, col_img = st.columns([2, 1])
                with col_txt:
                    st.write(f"**Inspetor:** {row['Usuario']}")
                    st.write(f"**Ação:** {row['Acao']}")
                    st.write(f"**Detalhes:** {row['Detalhes']}")
                
                with col_img:
                    # Se houver texto de imagem, transforma de volta em foto
                    foto_b64 = row.get('Foto_Path', "")
                    if foto_b64 and len(str(foto_b64)) > 100:
                        st.image(base64.b64decode(foto_b64), caption="Foto da Ocorrência")
                    else:
                        st.write("Sem foto.")
