import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
from PIL import Image
import io

# --- CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")

def init_db():
    conn = sqlite3.connect('zeladoria_v2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inspecoes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, inspetor TEXT, 
                  area TEXT, sub_area TEXT, item TEXT, status TEXT, 
                  motivo TEXT, detalhe TEXT, foto BLOB)''')
    conn.commit()
    conn.close()

init_db()

# --- LÓGICA DE NEGÓCIO ---
areas_config = {
    "Sede Social": {
        "senha": "SSICS",
        "subs": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
                 "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", 
                 "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")

menu = st.sidebar.selectbox("Menu", ["Nova Inspeção", "Histórico de NC"])

if menu == "Nova Inspeção":
    area_sel = st.selectbox("Selecione a Área", [""] + list(areas_config.keys()))
    
    if area_sel:
        senha = st.text_input("Senha de Acesso", type="password")
        if senha == areas_config[area_sel]["senha"]:
            nome_inspetor = st.text_input("Nome do Inspetor")
            sub_sel = st.selectbox("Subdivisão", areas_config[area_sel]["subs"])
            
            st.divider()
            st.subheader(f"Checklist: {sub_sel}")
            
            respostas = []
            for item in areas_config[area_sel]["itens"]:
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.write(f"**{item}**")
                    status = st.radio(f"Status_{item}", ["Conforme", "Não Conforme"], label_visibility="collapsed", horizontal=True)
                
                detalhes_nc = {"item": item, "status": status, "motivo": None, "obs": "", "foto": None}
                
                if status == "Não Conforme":
                    with col2:
                        detalhes_nc["motivo"] = st.selectbox(f"Motivo_{item}", ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"])
                        detalhes_nc["obs"] = st.text_input(f"Obs_{item}", placeholder="Especifique o problema (opcional)")
                        detalhes_nc["foto"] = st.file_uploader(f"Foto_{item}", type=['png', 'jpg', 'jpeg'])
                
                respostas.append(detalhes_nc)
                st.divider()

            if st.button("Finalizar e Gerar Relatório"):
                if not nome_inspetor:
                    st.error("Por favor, identifique-se antes de finalizar.")
                else:
                    conn = sqlite3.connect('zeladoria_v2.db')
                    c = conn.cursor()
                    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    for r in respostas:
                        foto_data = r["foto"].read() if r["foto"] else None
                        c.execute("INSERT INTO inspecoes (data, inspetor, area, sub_area, item, status, motivo, detalhe, foto) VALUES (?,?,?,?,?,?,?,?,?)",
                                  (data_atual, nome_inspetor, area_sel, sub_sel, r['item'], r['status'], r['motivo'], r['obs'], foto_data))
                    
                    conn.commit()
                    conn.close()
                    st.success("Relatório salvo com sucesso!")
                    
                    # Filtro de NC para exibição imediata
                    ncs = [r for r in respostas if r["status"] == "Não Conforme"]
                    if ncs:
                        st.warning("⚠️ Não Conformidades Encontradas:")
                        for nc in ncs:
                            st.write(f"- {nc['item']}: {nc['motivo']} ({nc['obs']})")
                        
                        st.info("Para exportar PDF ou enviar por WhatsApp, acesse a aba 'Histórico'.")
                    else:
                        st.balloons()
        elif senha != "":
            st.error("Senha incorreta.")

elif menu == "Histórico de NC":
    st.subheader("📋 Histórico de Não Conformidades")
    conn = sqlite3.connect('zeladoria_v2.db')
    df = pd.read_sql_query("SELECT id, data, inspetor, area, sub_area, item, motivo, detalhe FROM inspecoes WHERE status = 'Não Conforme'", conn)
    
    if not df.empty:
        st.dataframe(df)
        
        id_foto = st.number_input("Digite o ID para ver a foto", min_value=int(df['id'].min()), max_value=int(df['id'].max()))
        if st.button("Visualizar Foto"):
            c = conn.cursor()
            c.execute("SELECT foto FROM inspecoes WHERE id = ?", (id_foto,))
            img_data = c.fetchone()[0]
            if img_data:
                image = Image.open(io.BytesIO(img_data))
                st.image(image, caption=f"Evidência ID {id_foto}")
            else:
                st.warning("Sem foto para este registro.")
    else:
        st.write("Nenhuma não conformidade registrada.")
    conn.close()
