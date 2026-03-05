import streamlit as st

# Configuração da página
st.set_page_config(page_title="Zelador Virtual", page_icon="🏢")

st.title("📋 Zelador Virtual")
st.markdown("Selecione a área e realize a inspeção técnica.")

# Dicionário de Estrutura: Áreas -> Subdivisões -> Itens de Inspeção
ESTRUTURA = {
    "Sede Social": {
        "subdivisões": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "subdivisões": [
            "Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", 
            "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# 1. Seleção da Área Principal
area_selecionada = st.selectbox("Escolha a Área Principal:", list(ESTRUTURA.keys()))

# 2. Seleção da Subdivisão
sub_selecionada = st.selectbox(f"Selecione o local em {area_selecionada}:", ESTRUTURA[area_selecionada]["subdivisões"])

st.divider()
st.subheader(f"Checklist: {sub_selecionada}")

# Dicionário para armazenar resultados
resultados = {}

# 3. Geração dinâmica do Checklist
for item in ESTRUTURA[area_selecionada]["itens"]:
    st.write(f"**{item}**")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Opções de conformidade
        status = st.radio(f"Status {item}", ["Conforme", "Não Conforme"], key=f"radio_{item}", label_visibility="collapsed")
    
    obs = ""
    if status == "Não Conforme":
        with col2:
            obs = st.text_input(f"Descreva a não conformidade ({item}):", key=f"obs_{item}")
    
    resultados[item] = {"status": status, "observacao": obs}

st.divider()

# 4. Finalização
if st.button("Finalizar Inspeção", type="primary"):
    st.success(f"Inspeção de '{sub_selecionada}' concluída com sucesso!")
    # Aqui você poderia adicionar lógica para salvar em um banco de dados ou CSV
    st.json(resultados)
