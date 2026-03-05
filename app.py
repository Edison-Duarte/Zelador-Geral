import streamlit as st
from datetime import datetime
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Zelador Virtual", page_icon="🏢")

st.title("🏢 Zelador Virtual - Checklist de Inspeção")
st.write(f"Data: {datetime.now().strftime('%d/%m/%Y')}")

# 1. Definição da Estrutura de Dados
areas = {
    "Sede Social": {
        "Subdivisões": ["Terraço", "1º Andar", "2º Andar"],
        "Itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "Subdivisões": [
            "Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", 
            "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "Itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# 2. Seleção de Área e Subdivisão
col1, col2 = st.columns(2)
with col1:
    area_sel = st.selectbox("Selecione a Área:", list(areas.keys()))
with col2:
    sub_sel = st.selectbox("Selecione a Subdivisão:", areas[area_sel]["Subdivisões"])

st.divider()

# 3. Formulário de Inspeção
st.subheader(f"Inspecionando: {sub_sel}")
respostas = {}

for item in areas[area_sel]["Itens"]:
    st.write(f"**{item}**")
    status = st.radio(f"Status para {item}", ["Conforme", "Não Conforme"], key=f"status_{item}", horizontal=True, label_visibility="collapsed")
    
    obs = ""
    if status == "Não Conforme":
        obs = st.text_input(f"Descreva a não conformidade ({item}):", key=f"obs_{item}")
    
    respostas[item] = {"Status": status, "Observação": obs}

# 4. Processamento do Relatório
if st.button("Finalizar Relatório"):
    nao_conformidades = [
        {"Item": k, "Problema": v["Observação"]} 
        for k, v in respostas.items() if v["Status"] == "Não Conforme"
    ]
    
    if not nao_conformidades:
        st.success("Tudo conforme! Nenhuma pendência registrada.")
    else:
        st.warning("Relatório de Não Conformidades Gerado:")
        df_nc = pd.DataFrame(nao_conformidades)
        st.table(df_nc)
        
        # Texto formatado para WhatsApp/E-mail
        texto_relatorio = f"Relatório de Inspeção - {sub_sel}\n"
        for nc in nao_conformidades:
            texto_relatorio += f"- {nc['Item']}: {nc['Problema']}\n"
        
        # Botões de Ação
        col_a, col_b, col_c = st.columns(3)
        
        # WhatsApp (Link API)
        url_wpp = f"https://wa.me/?text={texto_relatorio.replace(' ', '%20')}"
        col_a.link_button("📲 Enviar WhatsApp", url_wpp)
        
        # E-mail (Link mailto)
        url_mail = f"mailto:?subject=Relatorio%20Inspeção&body={texto_relatorio.replace(' ', '%20')}"
        col_b.link_button("📧 Enviar E-mail", url_mail)
        
        # PDF (Simulação simples via CSV para o Streamlit Cloud)
        col_c.download_button("📄 Baixar Relatório (CSV)", data=df_nc.to_csv(index=False), file_name="relatorio.csv")
