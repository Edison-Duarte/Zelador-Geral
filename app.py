import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Zelador Virtual - Cloud", layout="wide", page_icon="🏛️")

# --- CONEXÃO COM GOOGLE SHEETS ---
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Converte os secrets para dicionário
        creds_info = st.secrets["gcp_service_account"].to_dict()
        
        # Limpeza da chave privada para evitar erros de formatação comum
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            
        credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
        return None

client = get_gspread_client()

# Tenta abrir a planilha usando o ID dos Secrets
try:
    sheet_id = st.secrets["spreadsheet"]["id"]
    sh = client.open_by_key(sheet_id)
    worksheet = sh.get_worksheet(0) # Abre a primeira página (aba)
except Exception as e:
    st.error(f"Não foi possível acessar a planilha: {e}")
    st.info("Dica: Verifique se o e-mail do robô (client_email) foi adicionado como EDITOR na sua planilha.")
    st.stop()

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
    nome_usuario = st.text_input("Nome do Inspetor:", key="nome_user")
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
                    
                    acao_item, obs_item = "N/A", ""
                    
                    if status == "Não Conforme":
                        c1, c2 = st.columns(2)
                        with c1:
                            acao_item = st.selectbox("Ação Necessária:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        with c2:
                            obs_item = st.text_input("Observações:", key=f"ob_{item}")
                        
                        st.file_uploader(f"📸 Foto de {item}", type=["jpg", "jpeg", "png"], key=f"ft_{item}")
                    
                    respostas_temp.append({
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Usuario": nome_usuario,
                        "Area": area_sel,
                        "Subdivisao": sub_area,
                        "Item": item,
                        "Status": status,
                        "Acao": acao_item,
                        "Detalhes": obs_item,
                        "Foto_Path": "" # Por enquanto sem armazenamento externo de fotos
                    })

            st.write("---")
            if st.button("🚀 FINALIZAR E SALVAR NA PLANILHA", use_container_width=True):
                if not nome_usuario:
                    st.error("⚠️ Por favor, preencha o nome do inspetor.")
                else:
                    with st.spinner("Sincronizando com Google Sheets..."):
                        try:
                            # Converte a lista de dicionários em lista de listas para o gspread
                            dados_para_salvar = [list(r.values()) for r in respostas_temp]
                            worksheet.append_rows(dados_para_salvar)
                            st.success("✅ Inspeção salva com sucesso na nuvem!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

elif menu == "Histórico":
    st.header("📂 Histórico (Google Sheets)")
    
    with st.spinner("Carregando dados..."):
        try:
            # Busca todos os dados da planilha
            records = worksheet.get_all_records()
            if not records:
                st.info("Nenhum registro encontrado na planilha.")
            else:
                df = pd.DataFrame(records)
                
                # Filtros
                area_f = st.selectbox("Filtrar por Área:", ["Todas", "Sede Social", "Operacional"])
                ver_c = st.checkbox("Mostrar itens 'Conforme'")
                
                df_v = df.copy()
                if area_f != "Todas": df_v = df_v[df_v["Area"] == area_f]
                if not ver_c: df_v = df_v[df_v["Status"] == "Não Conforme"]

                for idx, row in df_v.iloc[::-1].iterrows():
                    emoji = "✅" if row['Status'] == "Conforme" else "🔴"
                    with st.expander(f"{emoji} {row['Data']} - {row['Item']} ({row['Subdivisao']})"):
                        st.write(f"**Inspetor:** {row['Usuario']}")
                        st.write(f"**Ação:** {row['Acao']}")
                        st.write(f"**Detalhes:** {row['Detalhes']}")
                        
                        st.divider()
                        
                        # --- BOTÃO EDITAR (Simplificado para Planilha) ---
                        if st.checkbox("✏️ Editar", key=f"ed_{idx}"):
                            nova_obs = st.text_area("Nova Observação:", value=row['Detalhes'], key=f"new_ob_{idx}")
                            if st.button("Confirmar Edição", key=f"btn_{idx}"):
                                # O gspread usa índice 1-based e tem cabeçalho, então idx+2
                                worksheet.update_cell(idx + 2, 8, nova_obs) # Coluna 8 é Detalhes
                                st.success("Atualizado!")
                                st.rerun()

        except Exception as e:
            st.error(f"Erro ao ler histórico: {e}")
            st.info("Verifique se a primeira linha da sua planilha contém os cabeçalhos corretos.")
