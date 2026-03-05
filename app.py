import streamlit as st
import pandas as pd
from datetime import datetime

# Configurações iniciais da página
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")

# --- BANCO DE DADOS SIMULADO (Histórico) ---
if 'historico' not in st.session_state:
    st.session_state['historico'] = []

# --- DICIONÁRIO DE DADOS ---
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
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", 
            "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- INTERFACE ---
st.title("🏗️ Zelador Virtual - Checklist de Inspeção")

aba1, aba2, aba3 = st.tabs(["Inspeção", "Histórico", "Cronograma"])

with aba1:
    # 1. Identificação
    area_selecionada = st.selectbox("Selecione a Área", list(AREAS.keys()))
    usuario = st.text_input("Nome do Inspetor")
    senha = st.text_input("Senha da Área", type="password")

    if senha == AREAS[area_selecionada]["senha"]:
        st.success(f"Acesso liberado para {area_selecionada}")
        
        subdivisao = st.selectbox("Subdivisão", AREAS[area_selecionada]["subdivisoes"])
        
        st.divider()
        st.subheader(f"Checklist: {subdivisao}")
        
        respostas = {}
        
        for item in AREAS[area_selecionada]["itens"]:
            col1, col2 = st.columns([1, 1])
            with col1:
                status = st.radio(f"{item}:", ["Conforme", "Não Conforme"], key=item)
            
            detalhes = None
            obs = ""
            
            if status == "Não Conforme":
                with col2:
                    detalhes = st.selectbox(f"Ação para {item}", 
                                         ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"],
                                         key=f"det_{item}")
                    obs = st.text_input(f"Obs. adicional ({item})", key=f"obs_{item}")
            
            respostas[item] = {"status": status, "acao": detalhes, "obs": obs}

        if st.button("Finalizar Inspeção"):
            # Filtrar apenas Não Conformidades
            nao_conformes = {k: v for k, v in respostas.items() if v["status"] == "Não Conforme"}
            
            relatorio_texto = f"RELATÓRIO DE NÃO CONFORMIDADE - {area_selecionada}\n"
            relatorio_texto += f"Local: {subdivisao} | Inspetor: {usuario}\n"
            relatorio_texto += f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            for item, dados in nao_conformes.items():
                relatorio_texto += f"- {item}: {dados['acao']} ({dados['obs']})\n"

            # Salvar no histórico
            st.session_state['historico'].append({
                "Data": datetime.now().strftime('%d/%m/%Y'),
                "Área": area_selecionada,
                "Local": subdivisao,
                "Problemas": len(nao_conformes)
            })

            st.subheader("Relatório Gerado")
            st.text_area("Cópia do Relatório:", relatorio_texto, height=200)
            
            # Botões de ação (Simulados para Web)
            st.info("Para enviar via WhatsApp ou E-mail, copie o texto acima.")
            st.download_button("Baixar Relatório (PDF/TXT)", relatorio_texto, file_name="relatorio.txt")
            
    elif senha != "":
        st.error("Senha incorreta para esta área.")

with aba2:
    st.subheader("Histórico de Inspeções")
    if st.session_state['historico']:
        df = pd.DataFrame(st.session_state['historico'])
        st.table(df)
    else:
        st.write("Nenhuma inspeção realizada ainda.")

with aba3:
    st.subheader("Cronograma Sugerido")
    cronograma = {
        "Área": ["Sede Social", "Hangaragem", "Cais e Bacias", "Áreas Comuns"],
        "Frequência": ["Diária", "Semanal", "Quinzenal", "Mensal"],
        "Critério": ["Fluxo de sócios", "Segurança técnica", "Exposição marítima", "Estética"]
    }
    st.table(pd.DataFrame(cronograma))
