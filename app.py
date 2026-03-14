import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

# --- CONEXÃO COM GOOGLE SHEETS ---
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

# --- FUNÇÃO DE COMPACTAÇÃO DE IMAGEM ---
def preparar_foto_para_planilha(foto_file):
    """Reduz o tamanho da imagem para caber em uma célula do Google Sheets (limite 50k caracteres)"""
    if foto_file is None:
        return ""
    try:
        img = Image.open(foto_file)
        # Redimensiona mantendo a proporção (máximo 400px)
        img.thumbnail((400, 400))
        
        # Converte para JPEG com compressão
        buffer = BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=50)
        
        # Transforma em Base64 (texto)
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        st.warning(f"Não foi possível processar a imagem: {e}")
        return ""

# --- CONFIGURAÇÕES DO NEGÓCIO ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS", 
        "subs": ["Terraço", "1º Andar", "2º Andar"], 
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS", 
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- INTERFACE ---
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
                        with c1:
                            acao = st.selectbox("Ação Necessária:", ["Limpeza", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        with c2:
                            obs = st.text_input("Observações:", key=f"ob_{item}")
                        
                        foto = st.file_uploader(f"📸 Foto de {item}", type=["jpg", "jpeg", "png"], key=f"ft_{item}")
                    
                    respostas_temp.append({
                        "Item": item, "Status": status, "Acao": acao, "Detalhes": obs, "Foto": foto
                    })

            if st.button("🚀 FINALIZAR E SALVAR", use_container_width=True):
                if not nome_usuario:
                    st.error("⚠️ Digite o seu nome.")
                else:
                    with st.spinner("Sincronizando com a planilha..."):
                        dados_para_salvar = []
                        for r in respostas_temp:
                            # Compacta a foto aqui antes de enviar
                            foto_texto = preparar_foto_para_planilha(r["Foto"])
                            
                            dados_para_salvar.append([
                                datetime.now().strftime("%d/%m/%Y %H:%M"),
                                nome_usuario, area_sel, sub_area,
                                r["Item"], r["Status"], r["Acao"], r["Detalhes"], foto_texto
                            ])
                        
                        worksheet.append_rows(dados_para_salvar)
                        st.success("✅ Inspeção salva com sucesso!")
                        st.balloons()

elif menu == "Histórico":
    st.header("📂 Histórico Cloud")
    try:
        records = worksheet.get_all_records()
        if not records:
            st.info("Nenhum registro encontrado.")
        else:
            df = pd.DataFrame(records)
            for idx, row in df.iloc[::-1].iterrows():
                emoji = "✅" if row['Status'] == "Conforme" else "🔴"
                with st.expander(f"{emoji} {row['Data']} - {row['Item']} ({row['Subdivisao']})"):
                    col_txt, col_img = st.columns([2, 1])
                    with col_txt:
                        st.write(f"**Inspetor:** {row['Usuario']}")
                        st.write(f"**Área:** {row['Area']}")
                        st.write(f"**Ação:** {row['Acao']}")
                        st.write(f"**Detalhes:** {row['Detalhes']}")
                    
                    with col_img:
                        foto_b64 = row.get('Foto_Path', "")
                        if foto_b64 and len(str(foto_b64)) > 100:
                            try:
                                st.image(base64.b64decode(foto_b64), caption="Foto da Ocorrência")
                            except:
                                st.write("Erro ao carregar imagem.")
                        else:
                            st.write("Sem foto.")
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")
