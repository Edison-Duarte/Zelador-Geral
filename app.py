import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

HISTORICO_FILE = "historico_inspecoes.csv"

if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Tipo_Falha", "Detalhes", "Foto_Path"])
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
def verificar_pendencias():
    if not os.path.exists(HISTORICO_FILE): return []
    try:
        df = pd.read_csv(HISTORICO_FILE)
        if df.empty: return []
        df['Data_dt'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        pendencias = []
        hoje = datetime.now()
        for area, info in AREAS.items():
            prazo = info['periodicidade_dias']
            for sub in info['subs']:
                ultima = df[(df['Area'] == area) & (df['Subdivisao'] == sub)]
                if not ultima.empty:
                    dias = (hoje - ultima['Data_dt'].max()).days
                    if dias >= prazo:
                        pendencias.append(f"🔴 **{area} - {sub}** (Última há {dias} dias)")
        return pendencias
    except: return []

def gerar_pdf(ncs, area, subarea, usuario):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, txt="Relatorio de Nao Conformidades", ln=True, align='C')
    pdf.set_font("Helvetica", size=12)
    pdf.ln(10)
    pdf.cell(0, 10, txt=f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, txt=f"Local: {area} - {subarea}", ln=True)
    pdf.cell(0, 10, txt=f"Inspetor: {usuario}", ln=True)
    pdf.ln(10)
    for item in ncs:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, txt=f"Item: {item['Item']}", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, txt=f"Falha: {item['Tipo_Falha']}", ln=True)
        pdf.cell(0, 8, txt=f"Obs: {item['Detalhes']}", ln=True)
        pdf.ln(5)
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.header("📋 Check-list de Inspeção")
    
    # 1. Avisos de Periodicidade
    pendentes = verificar_pendencias()
    if pendentes:
        st.warning("### ⚠️ Hoje devem ser inspecionadas as áreas:")
        for p in pendentes: st.write(p)
    else:
        st.success("✅ Nenhuma inspeção pendente para hoje.")

    # 2. Quadro de Periodicidade
    with st.expander("📅 Quadro de Periodicidade"):
        dados_quadro = [{"Área Principal": a, "Frequência": f"A cada {i['periodicidade_dias']} dias", "Subdivisões": ", ".join(i['subs'])} for a, i in AREAS.items()]
        st.table(dados_quadro)
    
    st.divider()

    # 3. Formulário
    nome_usuario = st.text_input("Nome do Inspetor:")
    area_sel = st.selectbox("Área Principal:", ["Selecione..."] + list(AREAS.keys()))

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            st.success("Acesso Liberado!")
            sub_area = st.selectbox(f"Subdivisão:", AREAS[area_sel]["subs"])
            st.divider()
            
            respostas = []
            for item in AREAS[area_sel]["itens"]:
                st.markdown(f"#### {item}")
                status = st.radio(f"Status para {item}", ["Conforme", "Não Conforme"], key=f"s_{item}", horizontal=True)
                
                falha_tipo, detalhe, foto_path = "", "", ""
                if status == "Não Conforme":
                    col_nc1, col_nc2 = st.columns([1, 1])
                    with col_nc1:
                        falha_tipo = st.selectbox(f"Tipo de falha:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"t_{item}")
                        detalhe = st.text_input(f"Observações:", key=f"o_{item}")
                    
                    with col_nc2:
                        # Opção hibrida: funciona para upload no PC e abre câmera/galeria no celular
                        foto = st.file_uploader(f"Foto ({item})", type=["jpg", "png", "jpeg"], key=f"f_{item}")
                        if foto:
                            foto_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            os.makedirs("fotos", exist_ok=True)
                            with open(foto_path, "wb") as f: f.write(foto.getbuffer())
                
                respostas.append({"Item": item, "Status": status, "Tipo_Falha": falha_tipo, "Detalhes": detalhe, "Foto_Path": foto_path})
                st.divider()

            if st.button("🚀 Finalizar e Enviar Relatório"):
                if not nome_usuario:
                    st.error("Por favor, preencha o nome do inspetor.")
                else:
                    ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                    data_at = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    # Salvar Histórico
                    df_hist = pd.read_csv(HISTORICO_FILE)
                    novo_reg = [[data_at, nome_usuario, area_sel, sub_area, r["Item"], r["Status"], r["Tipo_Falha"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                    pd.concat([df_hist, pd.DataFrame(novo_reg, columns=df_hist.columns)]).to_csv(HISTORICO_FILE, index=False)

                    if ncs:
                        st.warning(f"⚠️ Encontradas {len(ncs)} não conformidades.")
                        
                        # PDF
                        pdf_bytes = gerar_pdf(ncs, area_sel, sub_area, nome_usuario)
                        st.download_button("📥 1º Baixar PDF do Relatório", pdf_bytes, f"Relatorio_{sub_area}.pdf")
                        
                        # Texto para E-mail e WhatsApp
                        corpo_msg = f"Relatorio de Inspecao - Zeladoria\nLocal: {area_sel} ({sub_area})\nInspetor: {nome_usuario}\n"
                        corpo_msg += "-"*25 + "\n\n"
                        for nc in ncs:
                            corpo_msg += f"Item: {nc['Item']}\nFalha: {nc['Tipo_Falha']}\nObs: {nc['Detalhes']}\n\n"
                        
                        # E-mail
                        assunto = f"Manutencao Urgente: {sub_area}"
                        link_email = f"mailto:?subject={urllib.parse.quote(assunto)}&body={urllib.parse.quote(corpo_msg)}"
                        st.link_button("📧 2º Abrir meu E-mail", link_email)
                        
                        # WhatsApp
                        link_zap = f"https://api.whatsapp.com/send?text={urllib.parse.quote(corpo_msg)}"
                        st.link_button("💬 Enviar via WhatsApp", link_zap)
                    else:
                        st.success(f"Inspeção finalizada sem falhas por {nome_usuario}.")

elif menu == "Histórico":
    st.header("📂 Histórico de Falhas")
    if os.path.exists(HISTORICO_FILE):
        df = pd.read_csv(HISTORICO_FILE)
        df_ncs = df[df["Status"] == "Não Conforme"]
        for _, row in df_ncs.iloc[::-1].iterrows():
            with st.expander(f"🗓️ {row['Data']} | {row['Item']} ({row['Subdivisao']})"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Inspetor:** {row['Usuario']}")
                    st.write(f"**Falha:** {row['Tipo_Falha']}")
                    st.write(f"**Detalhes:** {row['Detalhes']}")
                with c2:
                    if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                        st.image(row['Foto_Path'], use_container_width=True)
