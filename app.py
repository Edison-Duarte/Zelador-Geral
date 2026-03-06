import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")

# --- BANCO DE DADOS TEMPORÁRIO (Simulação) ---
if 'historico' not in st.session_state:
    st.session_state['historico'] = []

# --- DICIONÁRIOS DE CONFIGURAÇÃO ---
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
st.title("🏛️ Zelador Virtual - Inspeção")

aba1, aba2 = st.tabs(["📋 Nova Inspeção", "📜 Histórico"])

with aba1:
    # 1. Identificação e Área
    col1, col2 = st.columns(2)
    with col1:
        usuario = st.text_input("Identificação do Usuário (Nome)")
    with col2:
        area_selecionada = st.selectbox("Selecione a Área", list(AREAS.keys()))

    # 2. Validação de Senha
    senha_input = st.text_input("Digite a senha da área", type="password")

    if senha_input == AREAS[area_selecionada]["senha"]:
        st.success(f"Acesso liberado para {area_selecionada}")
        
        sub_area = st.selectbox("Subdivisão", AREAS[area_selecionada]["subdivisoes"])
        
        st.divider()
        st.subheader(f"Checklist: {sub_area}")
        
        relatorio_atual = []

        # 3. Gerando os Itens de Inspeção
        for item in AREAS[area_selecionada]["itens"]:
            st.write(f"**Item: {item}**")
            status = st.radio(f"Status de {item}", ["Conforme", "Não Conforme"], key=f"status_{item}", horizontal=True)
            
            detalhes_nc = {}
            if status == "Não Conforme":
                col_cat, col_obs = st.columns(2)
                with col_cat:
                    acao = st.selectbox("Ação Necessária", ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], key=f"acao_{item}")
                with col_obs:
                    obs = st.text_input("Observação (Opcional)", key=f"obs_{item}")
                
                foto = st.file_uploader(f"Foto da Não Conformidade ({item})", type=['png', 'jpg', 'jpeg'], key=f"foto_{item}")
                
                detalhes_nc = {
                    "Item": item,
                    "Status": status,
                    "Ação": acao,
                    "Observação": obs,
                    "Foto": foto.name if foto else "Sem foto"
                }
                relatorio_atual.append(detalhes_nc)
            st.divider()

        # 4. Finalização
        if st.button("Finalizar Inspeção"):
            if not usuario:
                st.error("Por favor, identifique-se antes de finalizar.")
            else:
                data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
                dados_final = {
                    "Data": data_hora,
                    "Usuário": usuario,
                    "Área": area_selecionada,
                    "Subdivisão": sub_area,
                    "Não Conformidades": relatorio_atual
                }
                st.session_state['historico'].append(dados_final)
                st.balloons()
                st.success("Relatório gerado com sucesso!")
                
                if relatorio_atual:
                    st.warning("⚠️ Foram encontradas não conformidades. Veja o histórico para exportar.")
                else:
                    st.info("Tudo em ordem! Nenhuma não conformidade registrada.")

    elif senha_input != "":
        st.error("Senha incorreta.")

with aba2:
    st.subheader("Histórico de Inspeções")
    if not st.session_state['historico']:
        st.write("Nenhuma inspeção realizada ainda.")
    else:
        for idx, insp in enumerate(reversed(st.session_state['historico'])):
            with st.expander(f"{insp['Data']} - {insp['Área']} ({insp['Subdivisão']})"):
                st.write(f"**Inspecionado por:** {insp['Usuário']}")
                if insp['Não Conformidades']:
                    df_nc = pd.DataFrame(insp['Não Conformidades'])
                    st.table(df_nc)
                    
                    # Simulação de Botões de Exportação
                    st.write("---")
                    st.button(f"Gerar PDF ({idx})", help="Função para gerar PDF")
                    st.write(f"[Enviar via WhatsApp](https://wa.me/?text=Relatório%20de%20Inspeção%20{insp['Subdivisão']})")
                else:
                    st.write("Nenhuma não conformidade registrada.")
