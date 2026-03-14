import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Zelador Virtual", layout="wide")

HISTORICO_FILE = "historico_inspecoes.csv"

if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Acao", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

AREAS = {
    "Sede Social": {"senha": "SSICS", "subs": ["Terraço", "1º Andar", "2º Andar"], 
                    "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
                    "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]}
}

st.title("🏛️ Zelador Virtual")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    nome_usuario = st.text_input("Nome do Inspetor:", key="nome_user")
    area_sel = st.selectbox("Área Principal:", ["Selecione..."] + list(AREAS.keys()))

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox("Subdivisão:", AREAS[area_sel]["subs"])
            
            st.info("ℹ️ Cada item é salvo assim que você clica no botão abaixo dele.")
            
            for item in AREAS[area_sel]["itens"]:
                with st.expander(f"🔍 Inspecionar: {item}", expanded=True):
                    status = st.radio(f"Status - {item}", ["Conforme", "Não Conforme"], key=f"rad_{item}")
                    
                    foto_path = ""
                    acao_val = "N/A"
                    detalhe = ""
                    
                    if status == "Não Conforme":
                        acao_val = st.selectbox("Ação:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        detalhe = st.text_input("Obs:", key=f"det_{item}")
                        
                        # Componente de câmera direto na página (mais estável)
                        foto_data = st.camera_input(f"Tirar foto de {item}", key=f"cam_{item}")
                        if foto_data:
                            os.makedirs("fotos", exist_ok=True)
                            foto_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            with open(foto_path, "wb") as f:
                                f.write(foto_data.getvalue())
                            st.success("✅ Foto capturada!")

                    if st.button(f"Confirmar Item: {item}", key=f"btn_{item}"):
                        if not nome_usuario:
                            st.error("Digite seu nome no topo da página primeiro!")
                        else:
                            novo_dado = [
                                datetime.now().strftime("%d/%m/%Y %H:%M"),
                                nome_usuario, area_sel, sub_area, 
                                item, status, acao_val, detalhe, foto_path
                            ]
                            df_h = pd.read_csv(HISTORICO_FILE)
                            df_novo = pd.DataFrame([novo_dado], columns=df_h.columns)
                            pd.concat([df_h, df_novo]).to_csv(HISTORICO_FILE, index=False)
                            st.balloons()
                            st.success(f"Item {item} enviado ao histórico!")

elif menu == "Histórico":
    st.header("📂 Histórico")
    if os.path.exists(HISTORICO_FILE):
        df = pd.read_csv(HISTORICO_FILE)
        # Filtro simples para ver o que já foi feito
        area_f = st.selectbox("Filtrar área:", ["Todas", "Sede Social", "Operacional"])
        df_view = df if area_f == "Todas" else df[df["Area"] == area_f]
        
        for idx, row in df_view.iloc[::-1].iterrows():
            with st.expander(f"{row['Data']} - {row['Item']} ({row['Status']})"):
                st.write(f"**Ação:** {row['Acao']} | **Obs:** {row['Detalhes']}")
                if row['Foto_Path'] and os.path.exists(str(row['Foto_Path'])):
                    st.image(row['Foto_Path'])
