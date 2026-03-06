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

# --- BANCO DE DADOS COM CRITÉRIOS DE PERIODICIDADE ---
# frequencia: 1 (Todo dia), 7 (Semanal), 30 (Mensal)
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "frequencia": 1, 
        "subs": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "frequencia": 7,
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- FUNÇÕES DE APOIO ---
def carregar_historico():
    return pd.read_csv(HISTORICO_FILE)

def verificar_agenda():
    df = carregar_historico()
    hoje = datetime.now()
    inspeções_necessarias = []

    for area_nome, info in AREAS.items():
        for sub in info["subs"]:
            # Filtrar histórico desta sub-área
            filtro = df[(df["Area"] == area_nome) & (df["Subdivisao"] == sub)].copy()
            
            pode_fazer = False
            motivo = ""
            
            if filtro.empty:
                pode_fazer = True
                motivo = "Nunca realizada"
            else:
                # Conversão segura da data
                datas = pd.to_datetime(filtro["Data"], format="%d/%m/%Y %H:%M", errors='coerce')
                ultima_data = datas.max()
                
                if pd.notnull(ultima_data):
                    dias_desde_ultima = (hoje - ultima_data).days
                    if dias_desde_ultima >= info["frequencia"]:
                        pode_fazer = True
                        motivo = f"Última há {dias_desde_ultima} dias"
                else:
                    pode_fazer = True # Erro na data, assume que precisa fazer

            if pode_fazer:
                inspeções_necessarias.append({"area": area_nome, "sub": sub, "motivo": motivo})
    
    return inspeções_necessarias

def gerar_pdf(ncs, area, subarea, usuario):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, txt="Relatorio de Nao Conformidades", ln=True, align='C')
    pdf.set_font("Helvetica", size=12)
    pdf.ln(10)
    pdf.cell(0, 10, txt=f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, txt=f"Local: {area} - {subarea} | Inspetor: {usuario}", ln=True)
    pdf.ln(10)
    for item in ncs:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, txt=f"Item: {item['Item']}", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, txt=f"Falha: {item['Tipo_Falha']} | Obs: {item['Detalhes']}", ln=True)
        pdf.cell(0, 5, txt="-"*50, ln=True)
    return bytes(pdf.output())

# --- INTERFACE ---
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Ir para:", ["📅 Agenda de Hoje", "📂 Histórico Geral"])

if menu == "📅 Agenda de Hoje":
    st.header("🗓️ Cronograma de Inspeções")
    
    pendencias = verificar_agenda()
    
    if not pendencias:
        st.success("✅ Todas as áreas estão com as inspeções em dia!")
    else:
        st.info(f"Atenção: Você tem {len(pendencias)} áreas aguardando inspeção.")
        
        # Exibir Alertas Dinâmicos
        for p in pendencias:
            with st.container():
                col1, col2 = st.columns([3, 1])
                col1.warning(f"🔔 **Hoje deve ser feita a inspeção do {p['sub']}** ({p['area']})")
                col1.caption(f"Motivo: {p['motivo']}")
                
                if col2.button(f"Iniciar {p['sub']}", key=f"btn_{p['sub']}"):
                    st.session_state["em_inspecao"] = True
                    st.session_state["area_ativa"] = p['area']
                    st.session_state["sub_ativa"] = p['sub']

    # Formulário de Inspeção (Só aparece se clicar em Iniciar)
    if st.session_state.get("em_inspecao"):
        st.divider()
        st.subheader(f"📝 Formulário: {st.session_state['sub_ativa']}")
        
        nome = st.text_input("Seu Nome:")
        senha = st.text_input("Senha da Área:", type="password")
        
        if senha == AREAS[st.session_state["area_ativa"]]["senha"]:
            respostas = []
            for item in AREAS[st.session_state["area_ativa"]]["itens"]:
                c1, c2 = st.columns([1, 2])
                with c1:
                    status = st.radio(f"**{item}**", ["Conforme", "Não Conforme"], key=f"s_{item}")
                
                tp, obs, foto_p = "", "", ""
                if status == "Não Conforme":
                    with c2:
                        tp = st.selectbox("Tipo", ["Limpeza", "Pintura", "Reparo", "Troca"], key=f"t_{item}")
                        obs = st.text_input("Observação", key=f"o_{item}")
                        f = st.file_uploader("Foto", type=["jpg", "png"], key=f"f_{item}")
                        if f:
                            foto_p = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            os.makedirs("fotos", exist_ok=True)
                            with open(foto_p, "wb") as file: file.write(f.getbuffer())
                
                respostas.append({"Item": item, "Status": status, "Tipo_Falha": tp, "Detalhes": obs, "Foto_Path": foto_p})

            if st.button("Finalizar e Registrar"):
                if not nome:
                    st.error("Identifique-se primeiro.")
                else:
                    data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                    linhas = [[data_hoje, nome, st.session_state['area_ativa'], st.session_state['sub_ativa'], r["Item"], r["Status"], r["Tipo_Falha"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                    df_h = carregar_historico()
                    pd.concat([df_h, pd.DataFrame(linhas, columns=df_h.columns)]).to_csv(HISTORICO_FILE, index=False)
                    
                    st.success("Inspeção salva!")
                    
                    # Notificações de falha
                    ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                    if ncs:
                        pdf = gerar_pdf(ncs, st.session_state['area_ativa'], st.session_state['sub_ativa'], nome)
                        st.download_button("📥 Baixar PDF das Falhas", pdf, "Relatorio.pdf")
                        
                        msg = f"Atenção: Falhas no {st.session_state['sub_ativa']}\nInspetor: {nome}\n"
                        for n in ncs: msg += f"- {n['Item']}: {n['Tipo_Falha']}\n"
                        
                        st.link_button("📧 Abrir E-mail", f"mailto:?subject=Falhas&body={urllib.parse.quote(msg)}")
                    
                    st.session_state["em_inspecao"] = False
                    st.rerun()

elif menu == "📂 Histórico Geral":
    st.header("📂 Últimas Não Conformidades")
    df = carregar_historico()
    df_ncs = df[df["Status"] == "Não Conforme"]
    for _, row in df_ncs.iloc[::-1].iterrows():
        with st.expander(f"⚠️ {row['Data']} - {row['Subdivisao']} (Por: {row['Usuario']})"):
            st.write(f"**Item:** {row['Item']} | **Falha:** {row['Tipo_Falha']}")
            st.write(f"**Detalhes:** {row['Detalhes']}")
            if str(row['Foto_Path']) != "nan": st.image(row['Foto_Path'], width=250)
