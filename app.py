import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

HISTORICO_FILE = "historico_inspecoes.csv"

# Inicialização robusta do CSV
if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Acao", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

AREAS = {
    "Sede Social": {"senha": "SSICS", "subs": ["Terraço", "1º Andar", "2º Andar"], 
                    "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
                    "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]}
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
            
            st.warning("⚠️ Salve cada item individualmente após preencher.")
            
            for item in AREAS[area_sel]["itens"]:
                with st.expander(f"📍 {item}", expanded=True):
                    status = st.radio(f"Situação de {item}:", ["Conforme", "Não Conforme"], key=f"rad_{item}", horizontal=True)
                    
                    foto_path = ""
                    acao_val = "N/A"
                    detalhe = ""
                    
                    if status == "Não Conforme":
                        col1, col2 = st.columns(2)
                        with col1:
                            acao_val = st.selectbox("Ação Necessária:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        with col2:
                            detalhe = st.text_input("Observações:", key=f"det_{item}")
                        
                        foto_data = st.camera_input(f"Foto da falha: {item}", key=f"cam_{item}")
                        if foto_data:
                            os.makedirs("fotos", exist_ok=True)
                            foto_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            with open(foto_path, "wb") as f:
                                f.write(foto_data.getvalue())
                            st.success("✅ Foto pronta!")

                    if st.button(f"💾 Salvar {item}", key=f"btn_{item}"):
                        if not nome_usuario:
                            st.error("Escreva seu nome no topo primeiro!")
                        else:
                            novo_dado = [
                                datetime.now().strftime("%d/%m/%Y %H:%M"),
                                nome_usuario, area_sel, sub_area, 
                                item, status, acao_val, detalhe, foto_path
                            ]
                            df_h = pd.read_csv(HISTORICO_FILE)
                            df_novo = pd.DataFrame([novo_dado], columns=df_h.columns)
                            pd.concat([df_h, df_novo]).to_csv(HISTORICO_FILE, index=False)
                            st.success(f"Item '{item}' registrado com sucesso!")

elif menu == "Histórico":
    st.header("📂 Histórico de Inspeções")
    
    if os.path.exists(HISTORICO_FILE):
        df = pd.read_csv(HISTORICO_FILE)
        
        # Filtros de visualização
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_area = st.selectbox("Filtrar por Área:", ["Todas", "Sede Social", "Operacional"])
        with col_f2:
            ver_tudo = st.checkbox("Mostrar itens 'Conforme' também")

        # Aplicação dos filtros
        df_view = df.copy()
        if filtro_area != "Todas":
            df_view = df_view[df_view["Area"] == filtro_area]
        if not ver_tudo:
            df_view = df_view[df_view["Status"] == "Não Conforme"]

        if not df_view.empty:
            for idx, row in df_view.iloc[::-1].iterrows():
                # Cor do card baseada no status
                emoji = "✅" if row['Status'] == "Conforme" else "🔴"
                
                with st.expander(f"{emoji} {row['Data']} - {row['Item']} ({row['Subdivisao']})"):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.write(f"**Inspetor:** {row['Usuario']}")
                        st.write(f"**Status:** {row['Status']}")
                        if row['Status'] == "Não Conforme":
                            st.write(f"**Ação:** {row['Acao']}")
                            st.write(f"**Obs:** {row['Detalhes']}")
                        
                        # Botão de excluir com senha (mesma lógica anterior)
                        st.divider()
                        if st.checkbox("🗑️ Apagar", key=f"del_chk_{idx}"):
                            senha_ex = st.text_input("Senha da área:", type="password", key=f"pwd_{idx}")
                            if st.button("Confirmar Exclusão", key=f"btn_ex_{idx}"):
                                if senha_ex == AREAS[row['Area']]["senha"]:
                                    df_full = pd.read_csv(HISTORICO_FILE)
                                    df_full = df_full.drop(idx)
                                    df_full.to_csv(HISTORICO_FILE, index=False)
                                    st.rerun()
                                else:
                                    st.error("Senha incorreta.")
                    
                    with c2:
                        if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                            st.image(row['Foto_Path'], use_container_width=True)
        else:
            st.info("Nenhum registro encontrado para os filtros selecionados.")
