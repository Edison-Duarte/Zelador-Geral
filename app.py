import streamlit as st
from datetime import datetime

# Configurações de página
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")

# --- DADOS DE CONFIGURAÇÃO ---
AREAS_INFO = {
    "Sede Social": {
        "senha": "SSICS",
        "subdivisoes": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OICS",
        "subdivisoes": [
            "Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", 
            "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- ESTADO DO APLICATIVO ---
if 'relatorio' not in st.session_state:
    st.session_state.relatorio = []
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")
st.subheader("Checklist de Inspeção")

# 1. Identificação e Seleção de Área
col1, col2 = st.columns(2)
with col1:
    nome_usuario = st.text_input("Nome do Inspetor:")
with col2:
    area_selecionada = st.selectbox("Selecione a Área:", ["Selecione...", "Sede Social", "Operacional"])

if area_selecionada != "Selecione...":
    senha_input = st.text_input("Digite a senha da área:", type="password")
    
    if senha_input == AREAS_INFO[area_selecionada]["senha"]:
        st.success(f"Acesso liberado para {area_selecionada}")
        
        # 2. Subdivisão
        subdivisao = st.selectbox("Selecione o local específico:", AREAS_INFO[area_selecionada]["subdivisoes"])
        
        st.divider()
        st.write(f"### Inspecionando: {subdivisao}")
        
        # Form de Inspeção
        resultados = {}
        for item in AREAS_INFO[area_selecionada]["itens"]:
            st.write(f"**{item}**")
            status = st.radio(f"Status de {item}", ["Conforme", "Não Conforme"], key=f"radio_{item}", horizontal=True)
            
            if status == "Não Conforme":
                acao = st.selectbox(f"Ação necessária para {item}", ["Limpeza Imediata", "Reparo", "Troca de componentes"], key=f"acao_{item}")
                obs = st.text_input(f"Observação (opcional)", key=f"obs_{item}")
                resultados[item] = {"status": status, "acao": acao, "obs": obs}
            else:
                resultados[item] = {"status": status}
            st.divider()

        # 3. Finalização
        if st.button("Finalizar Checklist"):
            nao_conformidades = []
            for item, dados in resultados.items():
                if dados["status"] == "Não Conforme":
                    nao_conformidades.append(f"- {item}: {dados['acao']} ({dados.get('obs', 'Sem obs')})")
            
            if not nome_usuario:
                st.error("Por favor, identifique-se antes de finalizar.")
            else:
                st.session_state.relatorio_final = {
                    "inspetor": nome_usuario,
                    "area": area_selecionada,
                    "local": subdivisao,
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "falhas": nao_conformidades
                }
                st.session_state.finalizado = True

# --- RELATÓRIO E EXPORTAÇÃO ---
if 'finalizado' in st.session_state:
    rel = st.session_state.relatorio_final
    st.success("✅ Checklist Finalizado!")
    
    conteudo_relatorio = f"RELATÓRIO DE NÃO CONFORMIDADE\n" \
                         f"Data: {rel['data']}\n" \
                         f"Inspetor: {rel['inspetor']}\n" \
                         f"Local: {rel['area']} - {rel['local']}\n\n" \
                         f"FALHAS ENCONTRADAS:\n" + "\n".join(rel['falhas'])

    st.text_area("Resumo do Relatório", conteudo_relatorio, height=200)

    # Opções de Envio (Simulação e Links)
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        # Link para WhatsApp
        msg_wp = f"https://wa.me/?text={conteudo_relatorio.replace(' ', '%20').replace('\n', '%0A')}"
        st.link_button("📲 WhatsApp", msg_wp)
        
    with col_b:
        # Link para Email
        mailto = f"mailto:?subject=Relatorio_{rel['local']}&body={conteudo_relatorio.replace(' ', '%20').replace('\n', '%0A')}"
        st.link_button("📧 E-mail", mailto)
        
    with col_c:
        st.info("Para PDF: Use 'Imprimir' (Ctrl+P) e salvar como PDF.")

    if st.button("Novo Checklist"):
        del st.session_state.finalizado
        st.rerun()
