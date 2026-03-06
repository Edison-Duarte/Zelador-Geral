import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
# Adicionado: 'periodicidade_dias' para controle automático
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
        "periodicidade_dias": 7  # Hangares a cada 7 dias
    }
}

# --- FUNÇÕES DE APOIO ---

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
    pdf.cell(0, 10, txt="ITENS PONTUADOS:", ln=True)
    pdf.ln(5)

    for item in ncs:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, txt=f"Item: {item['Item']}", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, txt=f"Tipo de Falha: {item['Tipo_Falha']}", ln=True)
        pdf.cell(0, 8, txt=f"Observacoes: {item['Detalhes']}", ln=True)
        pdf.cell(0, 5, txt="-"*50, ln=True)
        pdf.ln(2)
    
    return bytes(pdf.output())

def verificar_pendencias():
    """Analisa o histórico e retorna áreas que precisam de inspeção"""
    if not os.path.exists(HISTORICO_FILE):
        return []
    
    try:
        df = pd.read_csv(HISTORICO_FILE)
        if df.empty: return []
        
        # Converte a coluna Data para objeto datetime para cálculo
        df['Data_dt'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        pendencias = []
        hoje = datetime.now()

        for area, info in AREAS.items():
            prazo = info['periodicidade_dias']
            for sub in info['subs']:
                # Localiza a última vez que esta subdivisão foi inspecionada
                ultima = df[(df['Area'] == area) & (df['Subdivisao'] == sub)]
                
                if ultima.empty:
                    pendencias.append({"local": f"{area} - {sub}", "msg": "Nunca inspecionado", "cor": "red"})
                else:
                    data_ultima = ultima['Data_dt'].max()
                    dias_passados = (hoje - data_ultima).days
                    
                    if dias_passados >= prazo:
                        pendencias.append({"local": f"{area} - {sub}", "msg": f"Atrasado ({dias_passados} dias)", "cor": "red"})
                    elif dias_passados >= (prazo - 1): # Alerta de 1 dia de antecedência
                        pendencias.append({"local": f"{area} - {sub}", "msg": "Vence amanhã", "cor": "orange"})
        return pendencias
    except:
        return []

# --- INTERFACE STREAMLIT ---
st.title("🏛️ Zelador Virtual")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.header("📋 Check-list de Inspeção")
    
    # --- PAINEL DE ORIENTAÇÃO (PERIODICIDADE) ---
    pendencias = verificar_pendencias()
    if pendencias:
        with st.expander("⚠️ ATENÇÃO: ÁREAS PENDENTES", expanded=True):
            st.info("As seguintes áreas ultrapassaram o prazo de inspeção recomendado:")
            for p in pendencias:
                if p['cor'] == "red":
                    st.error(f"**{p['local']}**: {p['msg']}")
                else:
                    st.warning(f"**{p['local']}**: {p['msg']}")
    else:
        st.success("✅ Todas as inspeções periódicas estão em dia!")

    st.divider()

    # --- FORMULÁRIO ---
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
                    st.error("Por favor, digite seu nome antes de finalizar.")
                else:
                    ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                    
                    # Salvar no histórico (CSV)
                    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                    novo_registro = [[data_atual, nome_usuario, area_selecionada, sub_area, r["Item"], r["Status"], r["Tipo_Falha"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                    df_hist = pd.read_csv(HISTORICO_FILE)
                    pd.concat([df_hist, pd.DataFrame(novo_registro, columns=df_hist.columns)]).to_csv(HISTORICO_FILE, index=False)

                    if ncs:
                        st.warning(f"⚠️ {len(ncs)} Não Conformidades encontradas!")
                        
                        # PDF
                        pdf_bytes = gerar_pdf(ncs, area_selecionada, sub_area, nome_usuario)
                        st.download_button("📥 1º Baixar PDF do Relatório", pdf_bytes, f"Relatorio_{sub_area}.pdf", "application/pdf")

                        # Texto formatado
                        corpo_msg = f"Relatório de Inspeção - Zeladoria\n"
                        corpo_msg += f"Local: {area_selecionada} ({sub_area})\n"
                        corpo_msg += f"Inspetor Responsável: {nome_usuario}\n"
                        corpo_msg += "-"*30 + "\n\n"
                        corpo_msg += "ITENS PONTUADOS:\n"
                        for nc in ncs:
                            corpo_msg += f"• {nc['Item']}: {nc['Tipo_Falha']}\n  Obs: {nc['Detalhes']}\n\n"
                        
                        # Links de comunicação
                        assunto = f"Manutenção Urgente: {sub_area}"
                        link_mailto = f"mailto:?subject={urllib.parse.quote(assunto)}&body={urllib.parse.quote(corpo_msg)}"
                        st.link_button("📧 2º Abrir meu E-mail", link_mailto)
                        
                        link_zap = f"https://api.whatsapp.com/send?text={urllib.parse.quote(corpo_msg)}"
                        st.link_button("💬 Enviar via WhatsApp", link_zap)
                    else:
                        st.success(f"Tudo em conformidade! Registrado por {nome_usuario}.")
                        st.balloons()

elif menu == "Histórico":
    st.header("📂 Histórico de Inspeções")
    if os.path.exists(HISTORICO_FILE):
        df_hist = pd.read_csv(HISTORICO_FILE)
        
        # Filtro simples para ver apenas NCs ou tudo
        ver_tudo = st.checkbox("Mostrar itens 'Conforme' também")
        if not ver_tudo:
            df_hist = df_hist[df_hist["Status"] == "Não Conforme"]

        if not df_hist.empty:
            for idx, row in df_hist.iloc[::-1].iterrows():
                icone = "❌" if row['Status'] == "Não Conforme" else "✅"
                with st.expander(f"{icone} {row['Data']} | {row['Item']} - {row['Subdivisao']}"):
                    col_info, col_img = st.columns([2, 1])
                    with col_info:
                        st.write(f"**👤 Inspetor:** {row['Usuario']}")
                        st.write(f"**📍 Área:** {row['Area']} - {row['Subdivisao']}")
                        st.write(f"**🛠️ Status:** {row['Status']}")
                        if row['Status'] == "Não Conforme":
                            st.write(f"**⚠️ Falha:** {row['Tipo_Falha']}")
                            st.write(f"**📝 Detalhes:** {row['Detalhes']}")
                    with col_img:
                        if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                            st.image(row['Foto_Path'], use_container_width=True)
        else:
            st.info("Nenhum registro encontrado.")
