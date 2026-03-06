import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

HISTORICO_FILE = "historico_inspecoes.csv"
if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Tipo_Falha", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

# --- BANCO DE DADOS DE ÁREAS COM PERIODICIDADE (EM DIAS) ---
# periodicidade: 1 = todo dia, 7 = uma vez por semana, 15 = quinzenal
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "periodicidade": 1, 
        "subs": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "periodicidade": 7,
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- FUNÇÕES DE APOIO ---
def carregar_historico():
    df = pd.read_csv(HISTORICO_FILE)
    if not df.empty:
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    return df

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
        pdf.cell(0, 5, txt="-"*50, ln=True)
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")

# Menu Lateral
menu = st.sidebar.selectbox("Navegação", ["📅 Agenda do Dia", "📝 Nova Inspeção", "📂 Histórico"])

# --- LÓGICA DA AGENDA DO DIA (CRONOGRAMA) ---
if menu == "📅 Agenda do Dia":
    st.header("📅 Cronograma de Inspeções")
    df_hist = carregar_historico()
    hoje = datetime.now()
    pendencias = []

    for area_nome, dados in AREAS.items():
        for sub in dados["subs"]:
            # Filtrar última inspeção dessa subárea
            ult_inspeção = df_hist[df_hist['Subdivisao'] == sub]
            
            if ult_inspeção.empty:
                pendencias.append({"area": area_nome, "sub": sub, "motivo": "Nunca inspecionado"})
            else:
                data_ult = ult_inspeção['Data'].max()
                dias_passados = (hoje - data_ult).days
                if dias_passados >= dados["periodicidade"]:
                    pendencias.append({"area": area_nome, "sub": sub, "motivo": f"Atrasado há {dias_passados} dias"})

    if pendencias:
        st.info(f"Olá! Você tem {len(pendencias)} inspeções sugeridas para hoje.")
        for p in pendencias:
            with st.container():
                col1, col2 = st.columns([3, 1])
                col1.warning(f"🚨 **Hoje deve ser feita a inspeção do {p['sub']}** ({p['area']})")
                if col2.button(f"Fazer Agora", key=f"btn_{p['sub']}"):
                    st.session_state['area_direta'] = p['area']
                    st.session_state['sub_direta'] = p['sub']
                    st.write("Vá para a aba 'Nova Inspeção' (A área já foi selecionada para você).")
    else:
        st.success("✅ Todas as áreas foram inspecionadas recentemente. Bom trabalho!")

# --- NOVA INSPEÇÃO ---
elif menu == "📝 Nova Inspeção":
    st.header("📋 Check-list de Inspeção")
    
    nome_usuario = st.text_input("Seu nome (Inspetor):")
    
    # Preenchimento automático vindo da Agenda
    area_default = st.session_state.get('area_direta', "Selecione...")
    area_selecionada = st.selectbox("Selecione a Área:", ["Selecione..."] + list(AREAS.keys()), index=(list(AREAS.keys()).index(area_default)+1 if area_default in AREAS else 0))

    if area_selecionada != "Selecione...":
        senha_input = st.text_input("Senha da Área:", type="password")
        
        if senha_input == AREAS[area_selecionada]["senha"]:
            st.success("Acesso Liberado!")
            sub_default = st.session_state.get('sub_direta', AREAS[area_selecionada]["subs"][0])
            sub_area = st.selectbox(f"Subdivisão:", AREAS[area_selecionada]["subs"], index=(AREAS[area_selecionada]["subs"].index(sub_default) if sub_default in AREAS[area_selecionada]["subs"] else 0))
            st.divider()
            
            respostas = []
            for item in AREAS[area_selecionada]["itens"]:
                col1, col2 = st.columns([1, 2])
                with col1:
                    status = st.radio(f"**{item}**", ["Conforme", "Não Conforme"], key=item)
                
                falha_tipo, detalhe, foto_nome = "", "", ""
                if status == "Não Conforme":
                    with col2:
                        falha_tipo = st.selectbox(f"Falha em {item}", ["Limpeza", "Pintura", "Reparo", "Troca"], key=f"t_{item}")
                        detalhe = st.text_input(f"Obs ({item})", key=f"o_{item}")
                        foto = st.file_uploader(f"Foto ({item})", type=["jpg", "png", "jpeg"], key=f"f_{item}")
                        if foto:
                            foto_nome = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            os.makedirs("fotos", exist_ok=True)
                            with open(foto_nome, "wb") as f: f.write(foto.getbuffer())
                
                respostas.append({"Item": item, "Status": status, "Tipo_Falha": falha_tipo, "Detalhes": detalhe, "Foto_Path": foto_nome})

            if st.button("Finalizar e Salvar"):
                if not nome_usuario:
                    st.error("Nome do inspetor é obrigatório.")
                else:
                    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                    novo_registro = [[data_atual, nome_usuario, area_selecionada, sub_area, r["Item"], r["Status"], r["Tipo_Falha"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                    df_hist = pd.read_csv(HISTORICO_FILE)
                    pd.concat([df_hist, pd.DataFrame(novo_registro, columns=df_hist.columns)]).to_csv(HISTORICO_FILE, index=False)
                    
                    st.success("Inspeção Salva com Sucesso!")
                    # Limpar seleção da agenda após salvar
                    if 'area_direta' in st.session_state: del st.session_state['area_direta']
                    if 'sub_direta' in st.session_state: del st.session_state['sub_direta']

                    ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                    if ncs:
                        pdf_bytes = gerar_pdf(ncs, area_selecionada, sub_area, nome_usuario)
                        st.download_button("📥 Baixar PDF das Falhas", pdf_bytes, f"Alerta_{sub_area}.pdf")
                        
                        corpo_msg = f"Falhas em: {sub_area}\nInspetor: {nome_usuario}\n"
                        for n in ncs: corpo_msg += f"- {n['Item']}: {n['Tipo_Falha']}\n"
                        
                        st.link_button("💬 Enviar no WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(corpo_msg)}")

# --- HISTÓRICO ---
elif menu == "📂 Histórico":
    st.header("📂 Histórico de Ocorrências")
    df = carregar_historico()
    if not df.empty:
        df_ncs = df[df["Status"] == "Não Conforme"]
        for idx, row in df_ncs.iloc[::-1].iterrows():
            with st.expander(f"🗓️ {row['Data'].strftime('%d/%m/%Y')} | {row['Subdivisao']} - {row['Item']}"):
                st.write(f"**Inspetor:** {row['Usuario']}")
                st.write(f"**Falha:** {row['Tipo_Falha']} | **Obs:** {row['Detalhes']}")
                if str(row['Foto_Path']) != "nan":
                    st.image(row['Foto_Path'], width=300)
    else:
        st.info("Ainda não há registros no histórico.")
