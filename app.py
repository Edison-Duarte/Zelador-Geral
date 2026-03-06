import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io

# Configurações de Página
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")

# Simulação de Banco de Dados (Em produção, usar algo como SQLite ou Google Sheets)
if 'historico' not in st.session_state:
    st.session_state.historico = []

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
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", 
            "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")

menu = st.sidebar.selectbox("Menu", ["Nova Inspeção", "Histórico de NC"])

if menu == "Nova Inspeção":
    st.header("📋 Checklist de Inspeção")
    
    # Identificação
    nome_usuario = st.text_input("Nome do Inspetor:")
    area_selecionada = st.selectbox("Selecione a Área:", list(AREAS.keys()))
    
    # Validação de Senha
    senha_input = st.text_input("Senha da Área:", type="password")
    
    if senha_input == AREAS[area_selecionada]["senha"]:
        st.success("Acesso Liberado")
        subdivisao = st.selectbox("Local Específico:", AREAS[area_selecionada]["subdivisoes"])
        
        # Formulário de Inspeção
        respostas = {}
        st.divider()
        
        for item in AREAS[area_selecionada]["itens"]:
            st.subheader(f"Item: {item}")
            status = st.radio(f"Status para {item}:", ["Conforme", "Não Conforme"], key=f"status_{item}")
            
            detalhes = {}
            if status == "Não Conforme":
                detalhes['acao'] = st.selectbox("Ação Necessária:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca de Componentes"], key=f"acao_{item}")
                detalhes['obs'] = st.text_area("Observações (Opcional):", key=f"obs_{item}")
                detalhes['foto'] = st.file_uploader("Upload da Foto:", type=['jpg', 'png', 'jpeg'], key=f"foto_{item}")
            
            respostas[item] = {"status": status, "detalhes": detalhes}
            st.divider()

        if st.button("Finalizar Inspeção"):
            nc_encontradas = []
            data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            for item, dados in respostas.items():
                if dados['status'] == "Não Conforme":
                    # Salvar imagem se houver
                    img_url = None
                    if dados['detalhes']['foto']:
                        img_url = Image.open(dados['detalhes']['foto'])
                    
                    nc_encontradas.append({
                        "Data": data_atual,
                        "Inspetor": nome_usuario,
                        "Area": area_selecionada,
                        "Local": subdivisao,
                        "Item": item,
                        "Acao": dados['detalhes']['acao'],
                        "Obs": dados['detalhes']['obs'],
                        "Foto": img_url
                    })
            
            if nc_encontradas:
                st.session_state.historico.extend(nc_encontradas)
                st.warning("Relatório Gerado: Não Conformidades Detectadas!")
                st.table(pd.DataFrame(nc_encontradas).drop(columns=['Foto']))
                
                # Opções de exportação (Simulação)
                st.info("Para enviar via WhatsApp/E-mail ou PDF em nuvem, integre APIs como Twilio ou ReportLab.")
            else:
                st.success("Inspeção concluída! Tudo em conformidade.")

    elif senha_input != "":
        st.error("Senha incorreta.")

elif menu == "Histórico de NC":
    st.header("📂 Histórico de Não Conformidades")
    if st.session_state.historico:
        df_hist = pd.DataFrame(st.session_state.historico)
        st.dataframe(df_hist.drop(columns=['Foto']))
        
        st.subheader("Visualizar Fotos")
        idx = st.number_input("Digite o índice da linha para ver a foto:", min_value=0, max_value=len(st.session_state.historico)-1, step=1)
        if st.session_state.historico[idx]['Foto']:
            st.image(st.session_state.historico[idx]['Foto'], caption=f"NC em {st.session_state.historico[idx]['Item']}")
        else:
            st.write("Sem foto para este registro.")
    else:
        st.write("Nenhum registro encontrado.")
