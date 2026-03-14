import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image, ImageOps

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Zelador Virtual", 
    layout="wide", 
    page_icon="🏛️"
)

# --- 2. CONEXÃO COM GOOGLE SHEETS ---
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
    if foto_file is None:
        return ""
    try:
        img = Image.open(foto_file)
        img = ImageOps.exif_transpose(img) 
        img.thumbnail((400, 400)) 
        
        buffer = BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=40)
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        st.warning(f"Erro ao processar imagem: {e}")
        return ""

# --- 4. DADOS DO NEGÓCIO ---
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

# --- 5. INTERFACE PRINCIPAL ---
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
                            acao = st.selectbox("Ação:", ["Limpeza", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        with c2:
                            obs = st.text_input("Obs:", key=f"ob_{item}")
                        
                        origem_foto = st.radio("Origem da foto:", ["Câmera", "Galeria"], key=f"origem_{item}", horizontal=True)
                        if origem_foto == "Câmera":
                            foto = st.camera_input(f"Capturar {item}", key=f"cam_{item}")
                        else:
                            foto = st.file_uploader(f"Anexar de {item}", type=["jpg", "jpeg", "png"], key=f"file_{item}")
                    
                    respostas_temp.append({
                        "Item": item, "Status": status, "Acao": acao, "Detalhes": obs, "Foto": foto
                    })

            if st.button("🚀 FINALIZAR E SALVAR", use_container_width=True):
                if not nome_usuario:
                    st.error("⚠️ Preencha o nome do inspetor.")
                else:
                    with st.spinner("Gravando dados..."):
                        dados_para_salvar = []
                        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                        for r in respostas_temp:
                            foto_texto = preparar_foto_para_planilha(r["Foto"])
                            dados_para_salvar.append([
                                agora, nome_usuario, area_sel, sub_area,
                                r["Item"], r["Status"], r["Acao"], r["Detalhes"], foto_texto
                            ])
                        
                        worksheet.append_rows(dados_para_salvar)
                        st.success("✅ Inspeção salva!")
                        st.balloons()

elif menu == "Histórico":
    st.header("📂 Histórico de Inspeções")
    
    try:
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            
            # Converter a coluna 'Data' para o formato datetime para filtrar
            df['Data_dt'] = pd.to_datetime(df['Data'], format="%d/%m/%Y %H:%M", errors='coerce')
            
            # --- FILTROS NO TOPO DO HISTÓRICO ---
            with st.expander("🔍 Filtros de Busca", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    data_inicio = st.date_input("Data Início", value=datetime.now().replace(day=1))
                with c2:
                    data_fim = st.date_input("Data Fim", value=datetime.now())
                with c3:
                    filtro_status = st.multiselect("Filtrar Status:", ["Conforme", "Não Conforme"], default=["Conforme", "Não Conforme"])
            
            # Aplicar filtros
            mask = (df['Data_dt'].dt.date >= data_inicio) & \
                   (df['Data_dt'].dt.date <= data_fim) & \
                   (df['Status'].isin(filtro_status))
            df_filtrado = df.loc[mask]

            if df_filtrado.empty:
                st.info("Nenhum registro encontrado para os filtros selecionados.")
            else:
                st.write(f"Exibindo **{len(df_filtrado)}** registros:")
                
                # Listar do mais recente para o mais antigo
                for idx, row in df_filtrado.iloc[::-1].iterrows():
                    cor = "green" if row['Status'] == "Conforme" else "red"
                    emoji = "✅" if row['Status'] == "Conforme" else "🔴"
                    
                    with st.expander(f"{emoji} {row['Data']} | {row['Area']} - {row['Item']}"):
                        col_info, col_img = st.columns([2, 1])
                        with col_info:
                            st.markdown(f"**Status:** :{cor}[{row['Status']}]")
                            st.write(f"**Inspetor:** {row['Usuario']}")
                            st.write(f"**Subdivisão:** {row['Subdivisao']}")
                            st.write(f"**Ação Necessária:** {row['Acao']}")
                            st.write(f"**Observações:** {row['Detalhes']}")
                        
                        with col_img:
                            f_b64 = row.get('Foto_Path', "")
                            if f_b64 and len(str(f_b64)) > 100:
                                st.image(base64.b64decode(f_b64), use_container_width=True)
                            else:
                                st.caption("Sem foto disponível.")
        else:
            st.info("A planilha está vazia.")
            
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
