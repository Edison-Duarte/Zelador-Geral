import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

HISTORICO_FILE = "historico_inspecoes.csv"

# Inicialização do arquivo (sem alterações)
if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Acao", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

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
            
            # USO DE FORMULÁRIO PARA EVITAR RECARREGAMENTOS ACIDENTAIS
            with st.form("form_inspecao"):
                st.write("---")
                respostas_input = []
                for item in AREAS[area_sel]["itens"]:
                    st.markdown(f"**{item}**")
                    status = st.radio("Status:", ["Conforme", "Não Conforme"], key=f"s_{item}", horizontal=True)
                    
                    # Campos de NC sempre visíveis no formulário para não mudar o layout
                    acao_val = st.selectbox("Ação (se NC):", ["N/A", "Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"a_{item}")
                    detalhe = st.text_input("Obs (se NC):", key=f"o_{item}")
                    foto = st.file_uploader("📸 Foto (se NC)", type=["jpg", "jpeg", "png"], key=f"f_{item}")
                    
                    respostas_input.append({
                        "Item": item, 
                        "Status": status, 
                        "Acao": acao_val, 
                        "Detalhes": detalhe, 
                        "Foto_Upload": foto
                    })
                    st.write("---")
                
                enviar = st.form_submit_button("🚀 SALVAR INSPECÇÃO")

            if enviar:
                if not nome_usuario:
                    st.error("Por favor, preencha o nome antes de salvar.")
                else:
                    ncs_para_pdf = []
                    dados_para_csv = []
                    os.makedirs("fotos", exist_ok=True)

                    for r in respostas_input:
                        f_path = ""
                        # Só processa a foto e a ação se o status for Não Conforme
                        if r["Status"] == "Não Conforme":
                            if r["Foto_Upload"]:
                                f_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{r['Item']}.jpg"
                                with open(f_path, "wb") as f:
                                    f.write(r["Foto_Upload"].getbuffer())
                            
                            ncs_para_pdf.append({
                                "Item": r["Item"], 
                                "Acao": r["Acao"], 
                                "Detalhes": r["Detalhes"]
                            })
                        
                        dados_para_csv.append([
                            datetime.now().strftime("%d/%m/%Y %H:%M"),
                            nome_usuario, area_sel, sub_area, 
                            r["Item"], r["Status"], r["Acao"], r["Detalhes"], f_path
                        ])

                    # Salva no CSV
                    df_h = pd.read_csv(HISTORICO_FILE)
                    df_novo = pd.DataFrame(dados_para_csv, columns=df_h.columns)
                    pd.concat([df_h, df_novo]).to_csv(HISTORICO_FILE, index=False)
                    
                    st.success("✅ Inspeção salva com sucesso!")
                    
                    if ncs_para_pdf:
                        pdf = gerar_pdf(ncs_para_pdf, area_sel, sub_area, nome_usuario)
                        st.download_button("📥 Baixar PDF do Relatório", pdf, f"Relatorio_{sub_area}.pdf")

elif menu == "Histórico":
    # (Código do histórico permanece o mesmo da versão anterior)
    st.header("📂 Histórico")
    if os.path.exists(HISTORICO_FILE):
        df = pd.read_csv(HISTORICO_FILE)
        df_display = df[df["Status"] == "Não Conforme"].copy()
        for idx, row in df_display.iloc[::-1].iterrows():
            with st.expander(f"🗓️ {row['Data']} | {row['Item']}"):
                st.write(f"**Ação:** {row['Acao']}")
                st.write(f"**Obs:** {row['Detalhes']}")
                if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                    st.image(row['Foto_Path'])
