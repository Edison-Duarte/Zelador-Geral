import streamlit as st
import pandas as pd
from datetime import datetime
import os
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Zelador Virtual Cloud", layout="wide", page_icon="🏛️")

# CONEXÃO COM GOOGLE SHEETS
# O Streamlit busca automaticamente os dados que você colou nos "Secrets"
conn = st.connection("gsheets", type=GSheetsConnection)

def ler_dados():
    try:
        # ttl=0 garante que ele busque o dado mais recente da planilha sem usar memória antiga
        return conn.read(ttl=0)
    except:
        # Caso a planilha esteja totalmente vazia, cria um esqueleto
        return pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Acao", "Detalhes", "Foto_Path"])

def salvar_dados(df_novo):
    df_atual = ler_dados()
    # Limpa linhas vazias que o Google Sheets às vezes gera
    df_atual = df_atual.dropna(how="all")
    df_final = pd.concat([df_atual, df_novo], ignore_index=True)
    conn.update(data=df_final)

AREAS = {
    "Sede Social": {"senha": "SSICS", "subs": ["Terraço", "1º Andar", "2º Andar"], 
                    "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
                    "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]}
}

st.title("🏛️ Zelador Virtual - Cloud Sync")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    nome_usuario = st.text_input("Nome do Inspetor:")
    area_sel = st.selectbox("Área Principal:", ["Selecione..."] + list(AREAS.keys()))

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha da Área:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox("Subdivisão:", AREAS[area_sel]["subs"])
            st.divider()
            
            respostas_temp = []
            for item in AREAS[area_sel]["itens"]:
                with st.container(border=True):
                    st.subheader(f"📍 {item}")
                    status = st.radio(f"Situação {item}:", ["Conforme", "Não Conforme"], key=f"st_{item}", horizontal=True)
                    
                    acao_item, obs_item, foto_item = "N/A", "", None
                    if status == "Não Conforme":
                        col1, col2 = st.columns(2)
                        with col1:
                            acao_item = st.selectbox("Ação:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        with col2:
                            obs_item = st.text_input("Obs:", key=f"ob_{item}")
                        foto_item = st.file_uploader(f"📸 Foto", type=["jpg", "jpeg", "png"], key=f"ft_{item}")
                    
                    respostas_temp.append({"Item": item, "Status": status, "Acao": acao_item, "Detalhes": obs_item, "Foto": foto_item})

            if st.button("🚀 FINALIZAR E SALVAR NA PLANILHA", use_container_width=True):
                if not nome_usuario:
                    st.error("Preencha o nome do inspetor.")
                else:
                    with st.spinner("Enviando para o Google Sheets..."):
                        novas_linhas = []
                        os.makedirs("fotos", exist_ok=True)
                        for r in respostas_temp:
                            f_path = ""
                            if r["Status"] == "Não Conforme" and r["Foto"]:
                                f_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{r['Item']}.jpg"
                                with open(f_path, "wb") as f: f.write(r["Foto"].getbuffer())
                            
                            novas_linhas.append({
                                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "Usuario": nome_usuario, "Area": area_sel, "Subdivisao": sub_area,
                                "Item": r["Item"], "Status": r["Status"], "Acao": r["Acao"],
                                "Detalhes": r["Detalhes"], "Foto_Path": f_path
                            })
                        
                        df_novo = pd.DataFrame(novas_linhas)
                        salvar_dados(df_novo)
                        st.success("✅ Tudo salvo na nuvem!")
                        st.balloons()

elif menu == "Histórico":
    st.header("📂 Histórico Real-Time")
    df = ler_dados()
    if df.empty or len(df) == 0:
        st.info("A planilha está vazia.")
    else:
        # Mostra apenas o que não está conforme para agilizar
        df_nc = df[df["Status"] == "Não Conforme"]
        for idx, row in df_nc.iloc[::-1].iterrows():
            with st.expander(f"🔴 {row['Data']} - {row['Item']}"):
                st.write(f"**Local:** {row['Subdivisao']} | **Ação:** {row['Acao']}")
                if row['Foto_Path'] and os.path.exists(str(row['Foto_Path'])):
                    st.image(row['Foto_Path'])
