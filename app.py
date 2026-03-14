import streamlit as st
import pandas as pd
from datetime import datetime
import os

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
            
            respostas_temp = []
            for item in AREAS[area_sel]["itens"]:
                with st.container(border=True):
                    st.subheader(f"📍 {item}")
                    status = st.radio(f"Situação {item}:", ["Conforme", "Não Conforme"], key=f"st_{item}", horizontal=True)
                    
                    acao_item, obs_item, foto_item = "N/A", "", None
                    if status == "Não Conforme":
                        c1, c2 = st.columns(2)
                        with c1:
                            acao_item = st.selectbox("Ação Necessária:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                        with c2:
                            obs_item = st.text_input("Observações:", key=f"ob_{item}")
                        foto_item = st.file_uploader(f"📸 Foto de {item}", type=["jpg", "jpeg", "png"], key=f"ft_{item}")
                    
                    respostas_temp.append({"Item": item, "Status": status, "Acao": acao_item, "Detalhes": obs_item, "Foto": foto_item})

            if st.button("🚀 FINALIZAR E SALVAR TODA A INSPEÇÃO", use_container_width=True):
                if not nome_usuario:
                    st.error("⚠️ Preencha o nome do inspetor no topo.")
                else:
                    dados_final = []
                    os.makedirs("fotos", exist_ok=True)
                    for r in respostas_temp:
                        f_path = ""
                        if r["Status"] == "Não Conforme" and r["Foto"]:
                            f_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{r['Item']}.jpg"
                            with open(f_path, "wb") as f: f.write(r["Foto"].getbuffer())
                        dados_final.append([datetime.now().strftime("%d/%m/%Y %H:%M"), nome_usuario, area_sel, sub_area, r["Item"], r["Status"], r["Acao"], r["Detalhes"], f_path])
                    
                    df_h = pd.read_csv(HISTORICO_FILE)
                    pd.concat([df_h, pd.DataFrame(dados_final, columns=df_h.columns)]).to_csv(HISTORICO_FILE, index=False)
                    st.success("✅ Inspeção salva!")
                    st.rerun()

elif menu == "Histórico":
    st.header("📂 Histórico de Ocorrências")
    if os.path.exists(HISTORICO_FILE):
        df = pd.read_csv(HISTORICO_FILE)
        area_f = st.selectbox("Filtrar por Área:", ["Todas", "Sede Social", "Operacional"])
        ver_c = st.checkbox("Mostrar itens 'Conforme'")
        
        df_v = df.copy()
        if area_f != "Todas": df_v = df_v[df_v["Area"] == area_f]
        if not ver_c: df_v = df_v[df_v["Status"] == "Não Conforme"]

        if df_v.empty:
            st.info("Nenhum registro encontrado.")
        else:
            for idx, row in df_v.iloc[::-1].iterrows():
                emoji = "✅" if row['Status'] == "Conforme" else "🔴"
                with st.expander(f"{emoji} {row['Data']} - {row['Item']} ({row['Subdivisao']})"):
                    col_txt, col_img = st.columns([2, 1])
                    
                    with col_txt:
                        st.write(f"**Inspetor:** {row['Usuario']}")
                        st.write(f"**Ação Definida:** {row['Acao']}")
                        st.write(f"**Observações:** {row['Detalhes']}")
                        
                        st.divider()
                        
                        # --- SEÇÃO DE EDIÇÃO ---
                        if st.checkbox("✏️ Editar este registro", key=f"check_edit_{idx}"):
                            senha_edit = st.text_input("Senha para editar:", type="password", key=f"pw_edit_{idx}")
                            if senha_edit == AREAS[row['Area']]["senha"]:
                                nova_acao = st.selectbox("Nova Ação:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"new_ac_{idx}")
                                nova_obs = st.text_area("Novas Observações:", value=row['Detalhes'], key=f"new_ob_{idx}")
                                nova_foto = st.file_uploader("Substituir Foto:", type=["jpg","png","jpeg"], key=f"new_ft_{idx}")
                                
                                if st.button("Salvar Alterações", key=f"btn_save_{idx}"):
                                    df_full = pd.read_csv(HISTORICO_FILE)
                                    df_full.at[idx, 'Acao'] = nova_acao
                                    df_full.at[idx, 'Detalhes'] = nova_obs
                                    if nova_foto:
                                        path = f"fotos/edit_{datetime.now().strftime('%H%M%S')}.jpg"
                                        with open(path, "wb") as f: f.write(nova_foto.getbuffer())
                                        df_full.at[idx, 'Foto_Path'] = path
                                    df_full.to_csv(HISTORICO_FILE, index=False)
                                    st.success("Registro atualizado com sucesso!")
                                    st.rerun()
                            elif senha_edit:
                                st.error("Senha incorreta!")

                        # --- SEÇÃO DE EXCLUSÃO ---
                        if st.checkbox("🗑️ Apagar este registro", key=f"check_del_{idx}"):
                            senha_del = st.text_input("Senha para apagar:", type="password", key=f"pw_del_{idx}")
                            if st.button("Confirmar Exclusão", key=f"btn_del_{idx}"):
                                if senha_del == AREAS[row['Area']]["senha"]:
                                    df_full = pd.read_csv(HISTORICO_FILE)
                                    df_full = df_full.drop(idx)
                                    df_full.to_csv(HISTORICO_FILE, index=False)
                                    st.success("Apagado!")
                                    st.rerun()
                                else:
                                    st.error("Senha incorreta!")
                    
                    with col_img:
                        if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                            st.image(row['Foto_Path'], use_container_width=True)
