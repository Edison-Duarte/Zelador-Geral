import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

# Inicialização do arquivo de histórico
HISTORICO_FILE = "historico_inspecoes.csv"
if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Tipo_Falha", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

# --- BANCO DE DADOS DE ÁREAS COM PERIODICIDADE ---
# frequencia: 1 = Diária, 7 = Semanal
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

# --- FUNÇÕES DE LÓGICA ---

def carregar_historico():
    return pd.read_csv(HISTORICO_FILE)

def verificar_pendencias():
    df = carregar_historico()
    pendencias = []
    hoje = datetime.now()

    for area_nome, info in AREAS.items():
        for sub in info["subs"]:
            # Filtra histórico para esta sub-área específica
            filtro = df[(df["Area"] == area_nome) & (df["Subdivisao"] == sub)].copy()
            
            pode_fazer = True
            ultima_data_str = "Nunca realizada"
            
            if not filtro.empty:
                # Conversão segura de data para evitar o ValueError
                datas_conv = pd.to_datetime(filtro["Data"], format="%d/%m/%Y %H:%M", errors='coerce')
                ultima_inspecao = datas_conv.max()
                
                if pd.notnull(ultima_inspecao):
                    ultima_data_str = ultima_inspecao.strftime("%d/%m/%Y")
                    dias_passados = (hoje - ultima_inspecao).days
                    
                    if dias_passados < info["frequencia"]:
                        pode_fazer = False
            
            if pode_fazer:
                pendencias.append({
                    "Area": area_nome,
                    "Subdivisao": sub,
                    "Frequencia": "Diária" if info["frequencia"] == 1 else "Semanal",
                    "Ultima": ultima_data_str
                })
    return pendencias

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

# Sidebar
menu = st.sidebar.radio("Navegação", ["📅 Inspeções do Dia", "📂 Histórico Geral"])

if menu == "📅 Inspeções do Dia":
    st.header("📅 Pendências de Hoje")
    
    lista_pendentes = verificar_pendencias()
    
    if not lista_pendentes:
        st.success("✅ Tudo em dia! Nenhuma inspeção pendente para agora.")
        if st.button("Realizar Inspeção Extra"):
            st.session_state["extra"] = True
    
    # Se houver pendências, mostrar os cartões
    for p in lista_pendentes:
        with st.expander(f"🔴 PENDENTE: {p['Area']} - {p['Subdivisao']}"):
            st.write(f"**Periodicidade:** {p['Frequencia']} | **Última vez:** {p['Ultima']}")
            if st.button(f"Iniciar Inspeção em {p['Subdivisao']}", key=f"btn_{p['Subdivisao']}"):
                st.session_state["em_inspecao"] = True
                st.session_state["area_atual"] = p['Area']
                st.session_state["sub_atual"] = p['Subdivisao']
                st.rerun()

    # Formulário de Inspeção Ativo
    if st.session_state.get("em_inspecao"):
        st.divider()
        st.subheader(f"📝 Inspecionando: {st.session_state['area_atual']} ({st.session_state['sub_atual']})")
        
        nome_inspetor = st.text_input("Seu Nome:")
        senha_valida = AREAS[st.session_state['area_atual']]["senha"]
        senha_input = st.text_input("Senha da Área:", type="password")
        
        if senha_input == senha_valida:
            st.success("Acesso Liberado!")
            respostas = []
            
            for item in AREAS[st.session_state['area_atual']]["itens"]:
                col1, col2 = st.columns([1, 2])
                with col1:
                    status = st.radio(f"**{item}**", ["Conforme", "Não Conforme"], key=f"st_{item}")
                
                falha, obs, f_path = "", "", ""
                if status == "Não Conforme":
                    with col2:
                        falha = st.selectbox("Tipo de falha", ["Limpeza", "Pintura", "Reparo", "Troca"], key=f"tp_{item}")
                        obs = st.text_input("Detalhes/Observações", key=f"ob_{item}")
                        foto = st.file_uploader("Anexar Foto", type=["jpg", "png"], key=f"ft_{item}")
                        if foto:
                            f_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            os.makedirs("fotos", exist_ok=True)
                            with open(f_path, "wb") as f: f.write(foto.getbuffer())
                
                respostas.append({"Item": item, "Status": status, "Tipo_Falha": falha, "Detalhes": obs, "Foto_Path": f_path})

            if st.button("Finalizar e Registrar"):
                if not nome_inspetor:
                    st.error("Por favor, identifique-se (Nome do Inspetor).")
                else:
                    # Gravação no CSV
                    data_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                    novas_linhas = [[data_str, nome_inspetor, st.session_state['area_atual'], st.session_state['sub_atual'], r["Item"], r["Status"], r["Tipo_Falha"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                    df_h = carregar_historico()
                    pd.concat([df_h, pd.DataFrame(novas_linhas, columns=df_h.columns)]).to_csv(HISTORICO_FILE, index=False)
                    
                    # Notificações e Ações
                    ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                    if ncs:
                        st.warning(f"Inspeção finalizada com {len(ncs)} falhas!")
                        pdf = gerar_pdf(ncs, st.session_state['area_atual'], st.session_state['sub_atual'], nome_inspetor)
                        st.download_button("📥 Baixar PDF das Falhas", pdf, "Relatorio.pdf", "application/pdf")
                        
                        # Texto para E-mail/WhatsApp
                        resumo = f"Relatorio Zeladoria - {st.session_state['sub_atual']}\nInspetor: {nome_inspetor}\n"
                        for n in ncs: resumo += f"- {n['Item']}: {n['Tipo_Falha']} ({n['Detalhes']})\n"
                        
                        st.link_button("💬 Enviar Resumo WhatsApp", f"https://api.whatsapp.com/send?text={urllib.parse.quote(resumo)}")
                        st.link_button("📧 Abrir E-mail", f"mailto:?subject=Falha%20Zeladoria&body={urllib.parse.quote(resumo)}")
                    else:
                        st.success("Inspeção finalizada! Tudo em ordem.")
                    
                    # Limpa estado e recarrega
                    st.session_state["em_inspecao"] = False
                    st.rerun()

elif menu == "📂 Histórico Geral":
    st.header("📂 Histórico de Ocorrências")
    df = carregar_historico()
    df_ncs = df[df["Status"] == "Não Conforme"]
    
    if df_ncs.empty:
        st.info("Nenhuma não conformidade registrada.")
    else:
        for _, row in df_ncs.iloc[::-1].iterrows():
            with st.expander(f"🗓️ {row['Data']} - {row['Subdivisao']} (Por: {row['Usuario']})"):
                c1, c2 = st.columns([2, 1])
                c1.write(f"**Item:** {row['Item']}")
                c1.write(f"**Tipo de Falha:** {row['Tipo_Falha']}")
                c1.write(f"**Observação:** {row['Detalhes']}")
                if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                    c2.image(row['Foto_Path'], use_container_width=True)
