import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")

# --- BANCO DE DADOS FICTÍCIO (EM MEMÓRIA) ---
if 'historico' not in st.session_state:
    st.session_state.historico = []

# --- DICIONÁRIOS DE CONFIGURAÇÃO ---
AREAS_CONFIG = {
    "Sede Social": {
        "senha": "SSICS",
        "subdivisoes": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "subdivisoes": [
            "Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", 
            "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")

# 1. Identificação e Área
col1, col2 = st.columns(2)
with col1:
    area_selecionada = st.selectbox("Selecione a Área:", list(AREAS_CONFIG.keys()))
with col2:
    usuario = st.text_input("Identifique-se (Nome):")

# 2. Validação de Senha
senha_digitada = st.text_input("Digite a senha da área:", type="password")

if senha_digitada == AREAS_CONFIG[area_selecionada]["senha"]:
    st.success(f"Acesso liberado para {area_selecionada}")
    
    sub_area = st.selectbox("Selecione a Subdivisão:", AREAS_CONFIG[area_selecionada]["subdivisoes"])
    
    st.divider()
    st.subheader(f"Checklist: {sub_area}")
    
    respostas = {}
    
    for item in AREAS_CONFIG[area_selecionada]["itens"]:
        st.write(f"**{item}**")
        status = st.radio(f"Status para {item}", ["Conforme", "Não Conforme"], key=f"status_{item}", horizontal=True)
        
        detalhes = {"status": status, "acao": None, "obs": ""}
        
        if status == "Não Conforme":
            detalhes["acao"] = st.selectbox(
                "Ação necessária:", 
                ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], 
                key=f"acao_{item}"
            )
            detalhes["obs"] = st.text_input("Observação (opcional):", key=f"obs_{item}")
        
        respostas[item] = detalhes
        st.divider()

    # Botão Finalizar
    if st.button("Finalizar Inspeção"):
        nao_conformidades = {k: v for k, v in respostas.items() if v["status"] == "Não Conforme"}
        
        if nao_conformidades:
            registro = {
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Usuário": usuario,
                "Área": area_selecionada,
                "Subdivisão": sub_area,
                "Problemas": nao_conformidades
            }
            st.session_state.historico.append(registro)
            st.warning("Relatório de Não Conformidades Gerado!")
            st.write(nao_conformidades)
            
            # Simulação de exportação
            st.info("Opções de envio: [WhatsApp] [E-mail] [Gerar PDF]")
        else:
            st.success("Tudo em conformidade! Nenhuma ação necessária.")

elif senha_digitada != "":
    st.error("Senha incorreta.")

# --- SEÇÃO DE HISTÓRICO ---
st.sidebar.title("Navegação")
if st.sidebar.checkbox("Ver Histórico de Inspeções"):
    st.divider()
    st.header("📜 Histórico")
    if st.session_state.historico:
        st.table(pd.DataFrame(st.session_state.historico))
    else:
        st.write("Nenhum registro encontrado.")
