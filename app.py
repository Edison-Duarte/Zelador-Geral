import streamlit as st
import pandas as pd
from datetime import datetime
import os
from fpdf import FPDF

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

HISTORICO_FILE = "historico_inspecoes.csv"

if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Acao", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

AREAS = {
    "Sede Social": {"senha": "SSICS", "subs": ["Terraço", "1º Andar", "2º Andar"], 
                    "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]},
    "Operacional": {"senha": "OPICS", "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
                    "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]}
}

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    nome_usuario = st.text_input("Nome do Inspetor:", key="nome_user")
    area_sel = st.selectbox("Área Principal:", ["Selecione..."] + list(AREAS.keys()))

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha da Área:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox("Subdivisão:", AREAS[area_sel]["subs"])
            st.divider()
            
            # Lista para armazenar as escolhas do usuário fora de um st.form para permitir interatividade
            respostas_temp = []
            
            for item in AREAS[area_sel]["itens"]:
                # Criamos um container visual para cada item
                with st.container(border=True):
                    st.subheader(f"📍 {item}")
                    status = st.radio(f"Situação {item}:", ["Conforme", "Não Conforme"], key=f"st_{item}", horizontal=True)
                    
                    acao_item = "N/A"
                    obs_item = ""
                    foto_item = None
                    
                    # Agora a condicional volta a funcionar em tempo real!
                    if status == "Não Conforme":
                        c1, c2 = st.columns(2)
                        with c1:
                            acao_item = st.selectbox("Ação Necessária:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        with c2:
                            obs_item = st.text_input("Observações:", key=f"ob_{item}")
                        
                        foto_item = st.file_uploader(f"📸 Foto de {item}", type=["jpg", "jpeg", "png"], key=f"ft_{item}")
                    
                    respostas_temp.append({
                        "Item": item, "Status": status, "Acao": acao_item, "Detalhes": obs_item, "Foto": foto_item
                    })

            st.write("---")
            # Botão de finalizar fora do form, mas processando a lista completa
            if st.button("🚀 FINALIZAR E SALVAR TODA A INSPEÇÃO", use_container_width=True):
                if not nome_usuario:
                    st.error("⚠️ Por favor, preencha o nome do inspetor no topo.")
                else:
                    with st.spinner("Salvando dados..."):
                        dados_final = []
                        os.makedirs("fotos", exist_ok=True)
                        
                        for r in respostas_temp:
                            f_path = ""
                            if r["Status"] == "Não Conforme" and r["Foto"]:
                                f_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{r['Item']}.jpg"
                                with open(f_path, "wb") as f:
                                    f.write(r["Foto"].getbuffer())
                            
                            dados_final.append([
                                datetime.now().strftime("%d/%m/%Y %H:%M"),
                                nome_usuario, area_sel, sub_area, 
                                r["Item"], r["Status"], r["Acao"], r["Detalhes"], f_path
                            ])
                        
                        df_h = pd.read_csv(HISTORICO_FILE)
                        df_novos = pd.DataFrame(dados_final, columns=df_h.columns)
                        pd.concat([df_h, df_novos]).to_csv(HISTORICO_FILE, index=False)
                        
                        st.success("✅ Inspeção completa salva com sucesso!")
                        st.balloons()

elif menu == "Histórico":
    st.header("📂 Histórico de Ocorrências")
    if os.path.exists(HISTORICO_FILE):
        df = pd.read_csv(HISTORICO_FILE)
        
        area_f = st.selectbox("Filtrar por Área:", ["Todas", "Sede Social", "Operacional"])
        ver_c = st.checkbox("Mostrar itens 'Conforme'")
        
        df_v = df.copy()
        if area_f != "Todas": df_v = df_v[df_v["Area"] == area_f]
        if not ver_c: df_v = df_v[df_v["Status"] == "Não Conforme"]

        for idx, row in df_v.iloc[::-1].iterrows():
            emoji = "✅" if row['Status'] == "Conforme" else "🔴"
            with st.expander(f"{emoji} {row['Data']} - {row['Item']}"):
                st.write(f"**Ação:** {row['Acao']} | **Obs:** {row['Detalhes']}")
                if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                    st.image(row['Foto_Path'])
                
                # Opção de apagar (mesma lógica)
                if st.checkbox("Apagar", key=f"d_{idx}"):
                    if st.button("Confirmar", key=f"b_{idx}"):
                        # (Lógica de exclusão aqui)
                        pass
