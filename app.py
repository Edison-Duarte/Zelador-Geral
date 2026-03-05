import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

# Configuração da página
st.set_page_config(page_title="Zelador Virtual", page_icon="🏢")

# --- BANCO DE DADOS TEMPORÁRIO (Simulado) ---
if 'historico' not in st.session_state:
    st.session_state['historico'] = []

# --- CONFIGURAÇÕES DE DADOS ---
AREAS = {
    "Sede Social": {
        "sub": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"],
        "senha": "SSICS"
    },
    "Operacional": {
        "sub": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
                "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", 
                "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"],
        "senha": "OPICS"
    }
}

# --- INTERFACE ---
st.title("🏢 Zelador Virtual")
tab1, tab2 = st.tabs(["Nova Inspeção", "Histórico"])

with tab1:
    # 1. Identificação e Área
    col1, col2 = st.columns(2)
    with col1:
        nome_usuario = st.text_input("Seu Nome/Identificação:")
    with col2:
        area_sel = st.selectbox("Selecione a Área:", [""] + list(AREAS.keys()))

    if area_sel:
        # 2. Validação de Senha
        senha_input = st.text_input(f"Digite a senha para {area_sel}:", type="password")
        
        if senha_input == AREAS[area_sel]["senha"]:
            st.success("Acesso Liberado")
            sub_area = st.selectbox(f"Selecione o local de {area_sel}:", AREAS[area_sel]["sub"])
            
            st.divider()
            st.subheader(f"Checklist: {sub_area}")
            
            # 3. Formulário de Inspeção
            respostas = {}
            for item in AREAS[area_sel]["itens"]:
                st.write(f"**Item: {item}**")
                status = st.radio(f"Status para {item}", ["Conforme", "Não Conforme"], key=f"rad_{item}", horizontal=True)
                
                detalhes = {"status": status, "acao": "", "obs": ""}
                
                if status == "Não Conforme":
                    detalhes["acao"] = st.selectbox("Ação necessária:", 
                                                   ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"],
                                                   key=f"sel_{item}")
                    detalhes["obs"] = st.text_input("Observação (Opcional):", key=f"txt_{item}")
                
                respostas[item] = detalhes
                st.divider()

            # 4. Finalização
            if st.button("Finalizar Inspeção"):
                nao_conformidades = [
                    {"Item": k, "Ação": v["acao"], "Obs": v["obs"]} 
                    for k, v in respostas.items() if v["status"] == "Não Conforme"
                ]
                
                registro = {
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Usuário": nome_usuario,
                    "Área": area_sel,
                    "Sub-área": sub_area,
                    "Problemas": nao_conformidades
                }
                
                st.session_state['historico'].append(registro)
                st.balloons()
                st.success("Inspeção salva com sucesso!")

                # Exibição do Relatório de Não Conformidades
                if nao_conformidades:
                    st.warning("### Relatório de Não Conformidades")
                    df_nc = pd.DataFrame(nao_conformidades)
                    st.table(df_nc)
                    
                    # Simulação de botões de exportação
                    st.write("---")
                    st.write("**Exportar Relatório:**")
                    c1, c2, c3 = st.columns(3)
                    c1.button("📩 Enviar por E-mail")
                    c2.button("💬 Enviar WhatsApp")
                    c3.button("📄 Gerar PDF (Download)")
                else:
                    st.info("Tudo em conformidade! Nenhum reparo necessário.")

        elif senha_input != "":
            st.error("Senha incorreta.")

with tab2:
    st.header("📋 Histórico de Inspeções")
    if st.session_state['historico']:
        for i, insp in enumerate(reversed(st.session_state['historico'])):
            with st.expander(f"{insp['Data']} - {insp['Área']} ({insp['Sub-área']})"):
                st.write(f"**Inspetor:** {insp['Usuário']}")
                if insp['Problemas']:
                    st.table(pd.DataFrame(insp['Problemas']))
                else:
                    st.write("Sem não conformidades.")
    else:
        st.write("Nenhuma inspeção realizada ainda.")
