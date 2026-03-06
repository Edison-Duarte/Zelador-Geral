import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configurações Iniciais
st.set_page_config(page_title="Zelador Virtual", layout="centered")

# Simulação de Banco de Dados Local (Para persistência no Streamlit Cloud, use Google Sheets ou Supabase no futuro)
DB_FILE = "historico_inspecoes.csv"
IMG_DIR = "fotos_inspecoes"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

def salvar_dados(dados):
    df = pd.DataFrame([dados])
    if not os.path.exists(DB_FILE):
        df.to_csv(DB_FILE, index=False)
    else:
        df.to_csv(DB_FILE, mode='a', header=False, index=False)

# --- Lógica de Áreas e Senhas ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "subs": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", 
                 "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- Interface ---
st.title("🏛️ Zelador Virtual")

menu = st.sidebar.selectbox("Menu", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    area_sel = st.selectbox("Selecione a Área", ["Selecione..."] + list(AREAS.keys()))
    
    if area_sel != "Selecione...":
        nome_usuario = st.text_input("Seu Nome/Identificação")
        senha = st.text_input("Senha da Área", type="password")
        
        if senha == AREAS[area_sel]["senha"]:
            st.success("Acesso Liberado")
            sub_sel = st.selectbox("Subdivisão", AREAS[area_sel]["subs"])
            
            st.divider()
            nao_conformidades = []
            
            for item in AREAS[area_sel]["itens"]:
                st.subheader(f"Item: {item}")
                status = st.radio(f"Status para {item}", ["Conforme", "Não Conforme"], key=f"status_{item}")
                
                if status == "Não Conforme":
                    acao = st.selectbox("Ação Necessária", ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], key=f"acao_{item}")
                    obs = st.text_area("Especificação (Opcional)", key=f"obs_{item}")
                    foto = st.file_uploader(f"Foto da não conformidade ({item})", type=["jpg", "png", "jpeg"], key=f"foto_{item}")
                    
                    foto_path = ""
                    if foto:
                        foto_path = os.path.join(IMG_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg")
                        with open(foto_path, "wb") as f:
                            f.write(foto.getbuffer())
                    
                    nao_conformidades.append({
                        "Item": item,
                        "Ação": acao,
                        "Obs": obs,
                        "Foto": foto_path
                    })
            
            if st.button("Finalizar Inspeção"):
                data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
                # Salva cada não conformidade no histórico
                for nc in nao_conformidades:
                    nc.update({"Data": data_hora, "Area": area_sel, "Sub": sub_sel, "Inspetor": nome_usuario})
                    salvar_dados(nc)
                
                st.success("Relatório Gerado com Sucesso!")
                
                # --- Seção de Exportação ---
                resumo_texto = f"Relatório de Não Conformidade - {area_sel} ({sub_sel})\nInspetor: {nome_usuario}\n\n"
                for nc in nao_conformidades:
                    resumo_texto += f"- {nc['Item']}: {nc['Ação']} ({nc['Obs']})\n"

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.download_button("📄 Baixar PDF (Simulado)", data=resumo_texto, file_name="relatorio.txt")
                with col2:
                    st.link_button("💬 WhatsApp", f"https://wa.me/?text={resumo_texto.replace(' ', '%20')}")
                with col3:
                    st.link_button("📧 Email", f"mailto:?subject=Inspeção&body={resumo_texto.replace(' ', '%20')}")

        elif senha != "":
            st.error("Senha Incorreta")

elif menu == "Histórico":
    st.header("📋 Histórico de Não Conformidades")
    if os.path.exists(DB_FILE):
        df_hist = pd.read_csv(DB_FILE)
        for i, row in df_hist.iterrows():
            with st.expander(f"{row['Data']} - {row['Area']} ({row['Sub']})"):
                st.write(f"**Item:** {row['Item']}")
                st.write(f"**Problema/Ação:** {row['Ação']}")
                st.write(f"**Obs:** {row['Obs']}")
                if pd.notna(row['Foto']) and row['Foto'] != "":
                    st.image(row['Foto'], caption="Foto da Ocorrência")
    else:
        st.info("Nenhum histórico encontrado.")
