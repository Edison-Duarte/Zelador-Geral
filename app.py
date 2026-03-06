import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

HISTORICO_FILE = "historico_inspecoes.csv"

# Inicializa o CSV se não existir
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
                
                # SÓ EXIBE AVISO SE JÁ EXISTIR UMA PRIMEIRA INSPEÇÃO (conforme solicitado)
                if not ultima.empty:
                    data_ultima = ultima['Data_dt'].max()
                    dias_passados = (hoje - data_ultima).days
                    if dias_passados >= prazo:
                        pendencias.append(f"🔴 **{area} - {sub}** (Última há {dias_passados} dias)")
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
    
    pdf.set_font("Helvetica", "B", 12)
    for item in ncs:
        pdf.cell(0, 10, txt=f"Item: {item['Item']}", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, txt=f"Tipo de Falha: {item['Tipo_Falha']}", ln=True)
        pdf.cell(0, 8, txt=f"Observacoes: {item['Detalhes']}", ln=True)
        pdf.ln(5)
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.header("📋 Check-list de Inspeção")
    
    # --- 1. AVISO DE ÁREAS VENCIDAS ---
    pendentes = verificar_pendencias()
    if pendentes:
        st.warning("### ⚠️ Hoje devem ser inspecionadas as áreas:")
        for p in pendentes:
            st.write(p)
    else:
        st.success("✅ Nenhuma inspeção agendada para hoje (todas as áreas em dia).")

    # --- 2. QUADRO DE PERIODICIDADE ---
    with st.expander("📅 Quadro de Periodicidade (Regras de Inspeção)"):
        dados_quadro = []
        for area, info in AREAS.items():
            dados_quadro.append({
                "Área Principal": area,
                "Periodicidade": f"A cada {info['periodicidade_dias']} dias",
                "Subáreas incluídas": ", ".join(info['subs'])
            })
        st.table(dados_quadro)
    
    st.divider()

    # --- 3. FORMULÁRIO DE INSPEÇÃO ---
    nome_usuario = st.text_input("Seu nome (Inspetor):")
    area_selecionada = st.selectbox("Selecione a Área Principal:", ["Selecione..."] + list(AREAS.keys()))

    if area_selecionada != "Selecione...":
        senha_input = st.text_input("Senha da Área:", type="password")
        
        if senha_input == AREAS[area_selecionada]["senha"]:
            st.success("Acesso Liberado!")
            sub_area = st.selectbox(f"Subdivisão de {area_selecionada}:", AREAS[area_selecionada]["subs"])
            st.divider()
            
            respostas = []
            for item in AREAS[area_selecionada]["itens"]:
                col1, col2 = st.columns([1, 2])
                with col1:
                    status = st.radio(f"**{item}**", ["Conforme", "Não Conforme"], key=item)
                
                falha_tipo, detalhe, foto_nome = "", "", ""
                if status == "Não Conforme":
                    with col2:
                        falha_tipo = st.selectbox(f"Tipo de falha ({item})", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"t_{item}")
                        detalhe = st.text_input(f"Observações ({item})", key=f"o_{item}")
                        foto = st.file_uploader(f"Foto ({item})", type=["jpg", "png", "jpeg"], key=f"f_{item}")
                        if foto:
                            foto_nome = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            os.makedirs("fotos", exist_ok=True)
                            with open(foto_nome, "wb") as f: f.write(foto.getbuffer())
                
                respostas.append({"Item": item, "Status": status, "Tipo_Falha": falha_tipo, "Detalhes": detalhe, "Foto_Path": foto_nome})

            if st.button("Finalizar e Gerar Relatório"):
                if not nome_usuario:
                    st.error("Por favor, digite seu nome.")
                else:
                    ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    novo_registro = [[data_atual, nome_usuario, area_selecionada, sub_area, r["Item"], r["Status"], r["Tipo_Falha"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                    df_hist = pd.read_csv(HISTORICO_FILE)
                    pd.concat([df_hist, pd.DataFrame(novo_registro, columns=df_hist.columns)]).to_csv(HISTORICO_FILE, index=False)

                    if ncs:
                        st.warning(f"⚠️ {len(ncs)} Não Conformidades encontradas!")
                        pdf_bytes = gerar_pdf(ncs, area_selecionada, sub_area, nome_usuario)
                        st.download_button("📥 1º Baixar PDF do Relatório", pdf_bytes, f"Relatorio_{sub_area}.pdf", "application/pdf")
                        
                        corpo_msg = f"Relatório de Inspeção\nLocal: {area_selecionada} ({sub_area})\nInspetor: {nome_usuario}\n\n"
                        for nc in ncs:
                            corpo_msg += f"• {nc['Item']}: {nc['Tipo_Falha']}\n  Obs: {nc['Detalhes']}\n\n"
                        
                        link_mailto = f"mailto:?subject=Manutencao%20{sub_area}&body={urllib.parse.quote(corpo_msg)}"
                        st.link_button("📧 2º Abrir meu E-mail", link_mailto)
                        link_zap = f"https://api.whatsapp.com/send?text={urllib.parse.quote(corpo_msg)}"
                        st.link_button("💬 Enviar via WhatsApp", link_zap)
                    else:
                        st.success(f"Tudo em conformidade! Registrado por {nome_usuario}.")

elif menu == "Histórico":
    st.header("📂 Histórico de Inspeções")
    if os.path.exists(HISTORICO_FILE):
        df_hist = pd.read_csv(HISTORICO_FILE)
        df_ncs = df_hist[df_hist["Status"] == "Não Conforme"]
        if not df_ncs.empty:
            for idx, row in df_ncs.iloc[::-1].iterrows():
                with st.expander(f"🗓️ {row['Data']} | {row['Item']} - {row['Subdivisao']} (Por: {row['Usuario']})"):
                    col_info, col_img = st.columns([2, 1])
                    with col_info:
                        st.write(f"**👤 Inspetor:** {row['Usuario']}")
                        st.write(f"**📍 Área:** {row['Area']} - {row['Subdivisao']}")
                        st.write(f"**🛠️ Falha:** {row['Tipo_Falha']}")
                        st.write(f"**📝 Detalhes:** {row['Detalhes']}")
                    with col_img:
                        if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                            st.image(row['Foto_Path'], use_container_width=True)
        else:
            st.info("Nenhuma falha registrada.")
            
