import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

HISTORICO_FILE = "historico_inspecoes.csv"

# --- LÓGICA DE INICIALIZAÇÃO ---
if os.path.exists(HISTORICO_FILE):
    try:
        df_fix = pd.read_csv(HISTORICO_FILE)
        if "Tipo_Falha" in df_fix.columns:
            df_fix = df_fix.rename(columns={"Tipo_Falha": "Acao"})
            df_fix.to_csv(HISTORICO_FILE, index=False)
    except: pass
else:
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Acao", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

# --- BANCO DE DADOS DE ÁREAS ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "subs": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"],
        "periodicidade_dias": 15
    },
    "Operacional": {
        "senha": "OPICS",
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"],
        "periodicidade_dias": 7 
    }
}

# --- FUNÇÕES ---
def gerar_pdf(ncs, area, subarea, usuario):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, txt="Relatorio de Nao Conformidades", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, txt=f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, txt=f"Local: {area} - {subarea}", ln=True)
    pdf.cell(0, 10, txt=f"Inspetor: {usuario}", ln=True)
    pdf.ln(10)
    for item in ncs:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, txt=f"Item: {item['Item']}", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, txt=f"Acao: {item['Acao']}", ln=True)
        obs = str(item['Detalhes']).encode('latin-1', 'ignore').decode('latin-1')
        pdf.cell(0, 8, txt=f"Obs: {obs}", ln=True)
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.header("📋 Check-list de Inspeção")
    
    nome_usuario = st.text_input("Nome do Inspetor:")
    area_sel = st.selectbox("Área Principal:", ["Selecione..."] + list(AREAS.keys()))

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha da Área:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox(f"Subdivisão:", AREAS[area_sel]["subs"])
            st.divider()
            
            respostas = []
            for item in AREAS[area_sel]["itens"]:
                st.markdown(f"#### {item}")
                status = st.radio(f"Status para {item}", ["Conforme", "Não Conforme"], key=f"s_{item}", horizontal=True)
                
                acao_val, detalhe, foto_path = "", "", ""
                if status == "Não Conforme":
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        acao_val = st.selectbox(f"Ação:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"a_{item}")
                        detalhe = st.text_input(f"Obs:", key=f"o_{item}")
                    with col2:
                        # O segredo mobile: label claro e aceitar imagens
                        foto = st.file_uploader(f"📸 Tirar Foto ou Galeria", type=["jpg", "jpeg", "png"], key=f"f_{item}")
                        if foto:
                            foto_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            os.makedirs("fotos", exist_ok=True)
                            with open(foto_path, "wb") as f: f.write(foto.getbuffer())
                            st.success("✅ Foto carregada!")
                
                respostas.append({"Item": item, "Status": status, "Acao": acao_val, "Detalhes": detalhe, "Foto_Path": foto_path})
                st.divider()

            if st.button("🚀 Finalizar e Enviar"):
                if not nome_usuario: st.error("Nome obrigatório")
                else:
                    ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                    df_h = pd.read_csv(HISTORICO_FILE)
                    novo = [[datetime.now().strftime("%d/%m/%Y %H:%M"), nome_usuario, area_sel, sub_area, r["Item"], r["Status"], r["Acao"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                    pd.concat([df_h, pd.DataFrame(novo, columns=df_h.columns)]).to_csv(HISTORICO_FILE, index=False)
                    st.success("Inspeção Salva!")
                    if ncs:
                        pdf = gerar_pdf(ncs, area_sel, sub_area, nome_usuario)
                        st.download_button("📥 Baixar PDF", pdf, f"Relatorio_{sub_area}.pdf")

elif menu == "Histórico":
    st.header("📂 Histórico")
    if os.path.exists(HISTORICO_FILE):
        df = pd.read_csv(HISTORICO_FILE)
        df_display = df[df["Status"] == "Não Conforme"].copy()
        
        for idx, row in df_display.iloc[::-1].iterrows():
            with st.expander(f"🗓️ {row['Data']} | {row['Item']} ({row['Subdivisao']})"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Ação:** {row.get('Acao', 'N/A')}")
                    st.write(f"**Obs:** {row['Detalhes']}")
                    if st.checkbox("✏️ Editar", key=f"ed_{idx}"):
                        pwd = st.text_input("Senha:", type="password", key=f"p_{idx}")
                        if pwd == AREAS[row['Area']]["senha"]:
                            # Aqui o editor permite adicionar foto se não houver
                            nova_f = st.file_uploader("Substituir Foto", type=["jpg","png","jpeg"], key=f"nf_{idx}")
                            nova_obs = st.text_area("Editar Obs:", value=row['Detalhes'], key=f"no_{idx}")
                            if st.button("Salvar", key=f"s_{idx}"):
                                df_f = pd.read_csv(HISTORICO_FILE)
                                df_f.at[idx, 'Detalhes'] = nova_obs
                                if nova_f:
                                    path = f"fotos/edit_{idx}.jpg"
                                    with open(path, "wb") as f: f.write(nova_f.getbuffer())
                                    df_f.at[idx, 'Foto_Path'] = path
                                df_f.to_csv(HISTORICO_FILE, index=False)
                                st.rerun()
                with c2:
                    if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                        st.image(row['Foto_Path'])
