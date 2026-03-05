import streamlit as st
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Zelador Virtual", page_icon="🏢", layout="centered")

st.title("🏢 Zelador Virtual")
st.subheader("Sistema de Inspeção Predial e Operacional")

# --- DEFINIÇÃO DOS DADOS ---
AREAS = {
    "Sede Social": {
        "subdivisoes": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "subdivisoes": [
            "Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", 
            "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- INTERFACE DE SELEÇÃO ---
col1, col2 = st.columns(2)

with col1:
    area_selecionada = st.selectbox("Selecione a Área Principal:", list(AREAS.keys()))

with col2:
    sub_selecionada = st.selectbox("Selecione o Local Específico:", AREAS[area_selecionada]["subdivisoes"])

st.divider()

# --- FORMULÁRIO DE INSPEÇÃO ---
st.write(f"### Checklist: {sub_selecionada} ({area_selecionada})")
data_inspecao = st.date_input("Data da Inspeção", datetime.now())

# Criando os campos de status para cada item de inspeção
status_report = {}

for item in AREAS[area_selecionada]["itens"]:
    col_item, col_status = st.columns([2, 1])
    with col_item:
        st.write(f"**{item}**")
    with col_status:
        status = st.radio(f"Status {item}", ["OK", "Ajuste", "Crítico"], key=f"status_{item}", horizontal=True, label_visibility="collapsed")
    status_report[item] = status

observacoes = st.text_area("Observações Adicionais / Fotos (links):")

# --- BOTÃO DE SALVAR ---
if st.button("Finalizar Inspeção"):
    # Aqui futuramente podemos conectar a um banco de dados ou planilha Google
    st.success(f"Relatório de {sub_selecionada} enviado com sucesso!")
    st.balloons()
    
    # Exibição do resumo para conferência
    with st.expander("Visualizar Resumo do Envio"):
        st.write(f"**Data:** {data_inspecao}")
        st.write(f"**Local:** {sub_selecionada}")
        st.json(status_report)
        st.write(f"**Obs:** {observacoes}")
