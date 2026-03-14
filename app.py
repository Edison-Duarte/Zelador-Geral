import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
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
    nome_usuario = st.text_input("Nome do Inspetor:", key="nome_user")
    area_sel = st.selectbox("Área Principal:", ["Selecione..."] + list(AREAS.keys()))

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha da Área:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            sub_area = st.selectbox("Subdivisão:", AREAS[area_sel]["subs"])
            
            st.divider()
            
            # Formulário Único para salvar apenas no final
            with st.form("inspecao_completa", clear_on_submit=True):
                lista_respostas = []
                
                for item in AREAS[area_sel]["itens"]:
                    st.subheader(f"📍 {item}")
                    status = st.radio(f"Situação {item}:", ["Conforme", "Não Conforme"], key=f"st_{item}", horizontal=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        acao = st.selectbox("Ação:", ["N/A", "Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"ac_{item}")
                    with col2:
                        obs = st.text_input("Obs:", key=f"ob_{item}")
                    
                    # Usando file_uploader que é mais leve que camera_input para formulários longos
                    foto = st.file_uploader(f"📸 Foto de {item}", type=["jpg", "jpeg", "png"], key=f"ft_{item}")
                    
                    lista_respostas.append({
                        "Item": item, "Status": status, "Acao": acao, "Detalhes": obs, "Foto": foto
                    })
                    st.write("---")

                btn_finalizar = st.form_submit_button("🚀 FINALIZAR E SALVAR TUDO")

            if btn_finalizar:
                if not nome_usuario:
                    st.error("Por favor, preencha o nome do inspetor no topo da página.")
                else:
                    dados_final = []
                    ncs_relatorio = []
                    os.makedirs("fotos", exist_ok=True)
                    
                    for r in lista_respostas:
                        f_path = ""
                        if r["Status"] == "Não Conforme":
                            if r["Foto"]:
                                f_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{r['Item']}.jpg"
                                with open(f_path, "wb") as f:
                                    f.write(r["Foto"].getbuffer())
                            
                            ncs_relatorio.append({"Item": r["Item"], "Acao": r["Acao"], "Detalhes": r["Detalhes"]})
                        
                        dados_final.append([
                            datetime.now().strftime("%d/%m/%Y %H:%M"),
                            nome_usuario, area_sel, sub_area, 
                            r["Item"], r["Status"], r["Acao"], r["Detalhes"], f_path
                        ])
                    
                    # Salva no arquivo CSV de uma vez só
                    df_h = pd.read_csv(HISTORICO_FILE)
                    df_novos = pd.DataFrame(dados_final, columns=df_h.columns)
                    pd.concat([df_h, df_novos]).to_csv(HISTORICO_FILE, index=False)
                    
                    st.success("✅ Inspeção completa salva com sucesso!")
                    
                    if ncs_relatorio:
                        pdf = gerar_pdf(ncs_relatorio, area_sel, sub_area, nome_usuario)
                        st.download_button("📥 Baixar Relatório PDF", pdf, f"Relatorio_{sub_area}.pdf")

elif menu == "Histórico":
    st.header("📂 Histórico de Ocorrências")
    if os.path.exists(HISTORICO_FILE):
        df = pd.read_csv(HISTORICO_FILE)
        
        filtro_area = st.selectbox("Filtrar por Área:", ["Todas", "Sede Social", "Operacional"])
        ver_conforme = st.checkbox("Mostrar itens 'Conforme'")
        
        df_view = df.copy()
        if filtro_area != "Todas":
            df_view = df_view[df_view["Area"] == filtro_area]
        if not ver_conforme:
            df_view = df_view[df_view["Status"] == "Não Conforme"]

        for idx, row in df_view.iloc[::-1].iterrows():
            emoji = "✅" if row['Status'] == "Conforme" else "🔴"
            with st.expander(f"{emoji} {row['Data']} - {row['Item']} ({row['Subdivisao']})"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Inspetor:** {row['Usuario']}")
                    st.write(f"**Ação:** {row['Acao']}")
                    st.write(f"**Obs:** {row['Detalhes']}")
                    
                    st.divider()
                    if st.checkbox("🗑️ Apagar", key=f"del_{idx}"):
                        senha = st.text_input("Senha:", type="password", key=f"pw_{idx}")
                        if st.button("Confirmar", key=f"bt_{idx}"):
                            if senha == AREAS[row['Area']]["senha"]:
                                df_full = pd.read_csv(HISTORICO_FILE).drop(idx)
                                df_full.to_csv(HISTORICO_FILE, index=False)
                                st.rerun()
                with c2:
                    if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                        st.image(row['Foto_Path'])
