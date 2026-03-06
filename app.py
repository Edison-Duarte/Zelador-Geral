import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")

# Simulação de banco de dados local
DB_FILE = "historico_inspecoes.csv"

def salvar_dados(dados):
    df = pd.DataFrame(dados)
    if not os.path.isfile(DB_FILE):
        df.to_csv(DB_FILE, index=False)
    else:
        df.to_csv(DB_FILE, mode='a', header=False, index=False)

# --- ESTRUTURA DE DADOS ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "subdivisoes": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "subdivisoes": [
            "Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", 
            "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")

menu = ["Nova Inspeção", "Histórico"]
escolha_menu = st.sidebar.selectbox("Menu", menu)

if escolha_menu == "Nova Inspeção":
    st.header("📋 Checklists de Inspeção")
    
    usuario = st.text_input("Nome do Inspetor:")
    area_sel = st.selectbox("Selecione a Área:", list(AREAS.keys()))
    
    senha_digitada = st.text_input("Senha de Acesso:", type="password")
    
    if senha_digitada == AREAS[area_sel]["senha"]:
        st.success(f"Acesso liberado para {area_sel}")
        sub_sel = st.selectbox("Subdivisão:", AREAS[area_sel]["subdivisoes"])
        
        st.divider()
        respostas = []
        
        for item in AREAS[area_sel]["itens"]:
            st.subheader(f"Item: {item}")
            status = st.radio(f"Status para {item}", ["Conforme", "Não Conforme"], key=f"status_{item}")
            
            dados_item = {"item": item, "status": status, "acao": "", "obs": "", "foto": None}
            
            if status == "Não Conforme":
                dados_item["acao"] = st.selectbox("Ação Necessária:", 
                                                 ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], 
                                                 key=f"acao_{item}")
                dados_item["obs"] = st.text_area("Especificação da Não Conformidade (opcional):", key=f"obs_{item}")
                foto = st.file_uploader(f"Upload de foto para {item}", type=["jpg", "png", "jpeg"], key=f"foto_{item}")
                if foto:
                    # Em um app real, salvaríamos a foto em um storage (S3/Cloudinary)
                    dados_item["foto"] = foto.name 
            
            respostas.append(dados_item)
            st.divider()

        if st.button("Finalizar Inspeção"):
            data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            nao_conformes = [r for r in respostas if r["status"] == "Não Conforme"]
            
            # Preparar para salvar no histórico
            registros = []
            for nc in nao_conformes:
                registros.append({
                    "Data": data_hora,
                    "Inspetor": usuario,
                    "Area": area_sel,
                    "Local": sub_sel,
                    "Item": nc["item"],
                    "Ação": nc["acao"],
                    "Detalhes": nc["obs"],
                    "Foto": nc["foto"]
                })
            
            if registros:
                salvar_dados(registros)
                st.warning("Relatório de Não Conformidades Gerado!")
                st.table(pd.DataFrame(registros))
                
                # Botões de ação (Simulação)
                st.info("Opcionais de envio:")
                col1, col2, col3 = st.columns(3)
                col1.button("Enviar via WhatsApp")
                col2.button("Enviar por E-mail")
                col3.button("Gerar PDF")
            else:
                st.success("Tudo em conformidade! Nenhuma ação necessária.")

    elif senha_digitada != "":
        st.error("Senha incorreta.")

elif escolha_menu == "Histórico":
    st.header("📂 Histórico de Inspeções")
    if os.path.isfile(DB_FILE):
        df_hist = pd.read_csv(DB_FILE)
        st.dataframe(df_hist)
    else:
        st.info("Nenhum registro encontrado.")
