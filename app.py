import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import io

# --- CONEXÃO ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_creds():
    creds_info = st.secrets["gcp_service_account"].to_dict()
    if "\\n" in creds_info["private_key"]:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    return Credentials.from_service_account_info(creds_info, scopes=scope)

creds = get_creds()
client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

# Abre a planilha
sheet_id = st.secrets["spreadsheet"]["id"]
sh = client.open_by_key(sheet_id)
worksheet = sh.get_worksheet(0)

# Função para fazer upload da foto para o Google Drive
def upload_foto_drive(foto_file, nome_arquivo):
    try:
        file_metadata = {'name': nome_arquivo}
        media = MediaIoBaseUpload(io.BytesIO(foto_file.getvalue()), mimetype='image/jpeg')
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        # Torna a foto pública para que o Streamlit consiga exibir
        drive_service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'viewer'}).execute()
        return f"https://lh3.googleusercontent.com/u/0/d/{file.get('id')}"
    except:
        return ""

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual + Drive Sync")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    nome_usuario = st.text_input("Nome do Inspetor:")
    area_sel = st.selectbox("Área:", ["Sede Social", "Operacional"])
    
    # ... (restante do código de seleção de itens igual ao anterior) ...
    # Exemplo simplificado do loop de salvamento:
    
    if st.button("🚀 FINALIZAR"):
        with st.spinner("Enviando dados e fotos..."):
            dados_finais = []
            for item in respostas_temp: # respostas_temp é sua lista de itens
                link_foto = ""
                if item["Foto"]:
                    nome_f = f"{datetime.now().strftime('%Y%m%d')}_{item['Item']}.jpg"
                    link_foto = upload_foto_drive(item["Foto"], nome_f)
                
                dados_finais.append([
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                    nome_usuario, area_sel, item["Subdivisao"],
                    item["Item"], item["Status"], item["Acao"], item["Detalhes"], link_foto
                ])
            
            worksheet.append_rows(dados_finais)
            st.success("Salvo com sucesso!")

elif menu == "Histórico":
    st.header("📂 Histórico com Fotos")
    records = worksheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        for idx, row in df.iloc[::-1].iterrows():
            with st.expander(f"{row['Data']} - {row['Item']}"):
                st.write(f"**Status:** {row['Status']} | **Ação:** {row['Acao']}")
                # AQUI EXIBE A FOTO VINDA DO LINK DO DRIVE
                if row['Foto_Path'] and "http" in str(row['Foto_Path']):
                    st.image(row['Foto_Path'], caption="Foto da Ocorrência")
                else:
                    st.info("Sem foto disponível.")
