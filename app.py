import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import io

# --- CONEXÃO SEGURA ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_creds():
    creds_info = st.secrets["gcp_service_account"].to_dict()
    if "\\n" in creds_info["private_key"]:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    return Credentials.from_service_account_info(creds_info, scopes=scope)

creds = get_creds()
client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

sheet_id = st.secrets["spreadsheet"]["id"]
sh = client.open_by_key(sheet_id)
worksheet = sh.get_worksheet(0)

# --- FUNÇÃO PARA UPLOAD NO DRIVE AJUSTADA ---
def upload_para_drive(file_buffer, file_name):
    if file_buffer is None:
        return ""
    try:
        # Limpa o ID de qualquer sujeira de texto
        f_id_dest = st.secrets["spreadsheet"]["folder_id"].strip().replace('"', '').replace("'", "")
        
        file_metadata = {
            'name': file_name,
            'parents': [f_id_dest]
        }
        
        # Prepara o arquivo
        media = MediaIoBaseUpload(
            io.BytesIO(file_buffer.getvalue()), 
            mimetype='image/jpeg', 
            resumable=True
        )
        
        # Tenta criar o arquivo
        file = drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        
        file_id = file.get('id')
        
        # Torna a imagem visível para o App
        try:
            drive_service.permissions().create(
                fileId=file_id, 
                body={'type': 'anyone', 'role': 'viewer'}
            ).execute()
        except:
            pass
            
        return file_id
    except Exception as e:
        # Isso vai imprimir o erro detalhado no seu App para investigarmos
        st.error(f"Tentativa de upload falhou. Pasta ID usada: {f_id_dest}")
        st.error(f"Erro detalhado: {e}")
        return "ERRO_TECNICO"

# --- CONFIGURAÇÃO ---
AREAS = {
    "Sede Social": {"senha": "SSICS", "subs": ["Terraço", "1º Andar", "2º Andar"], 
                    "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
                    "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]}
}

st.title("🏛️ Zelador Virtual")
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
                        with c1: acao = st.selectbox("Ação:", ["Limpeza", "Reparo", "Troca"], key=f"ac_{item}")
                        with c2: obs = st.text_input("Obs:", key=f"ob_{item}")
                        foto = st.file_uploader(f"📸 Foto", type=["jpg", "png", "jpeg"], key=f"ft_{item}")
                    respostas_temp.append({"Item": item, "Status": status, "Acao": acao, "Detalhes": obs, "Foto": foto})

            if st.button("🚀 SALVAR"):
                with st.spinner("Enviando para Planilha e Drive..."):
                    linhas = []
                    for r in respostas_temp:
                        # Upload da foto e pega o ID
                        f_id = upload_para_drive(r["Foto"], f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{r['Item']}.jpg")
                        
                        linhas.append([
                            datetime.now().strftime("%d/%m/%Y %H:%M"),
                            nome_usuario, area_sel, sub_area,
                            r["Item"], r["Status"], r["Acao"], r["Detalhes"], f_id
                        ])
                    worksheet.append_rows(linhas)
                    st.success("✅ Salvo!")

elif menu == "Histórico":
    st.header("📂 Histórico")
    records = worksheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        for idx, row in df.iloc[::-1].iterrows():
            with st.expander(f"{row['Data']} - {row['Item']}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**Local:** {row['Subdivisao']} | **Ação:** {row['Acao']}")
                    st.write(f"**Obs:** {row['Detalhes']}")
                with col2:
                    f_id = str(row.get('Foto_Path', ""))
                    if f_id and len(f_id) > 5:
                        # Link direto para visualizar imagem do Drive
                        st.image(f"https://docs.google.com/uc?id={f_id}")
