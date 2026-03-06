import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide")

HISTORICO_FILE = "historico_inspecoes.csv"
if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Tipo_Falha", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

# --- BANCO DE DADOS DE ÁREAS COM PERIODICIDADE ---
# frequencia: 1 = Diária, 7 = Semanal, 30 = Mensal
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "frequencia": 1, # Diária
        "subs": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "frequencia": 7, # Semanal
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
            # Filtra histórico para esta sub-área
            filtro = df[(df["Area"] == area_nome) & (df["Subdivisao"] == sub)]
            
            pode_fazer = True
            ultima_data_str = "Nunca realizada"
            
            if not filtro.empty:
                # Pega a data da última inspeção
                ultima_inspeção = pd.to_datetime(filtro["Data"], dayfirst=True).max()
                ultima_data_str = ultima_inspeção.strftime("%d/%m/%Y")
                dias_passados = (hoje - ultima_inspeção).days
                
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
        pdf.cell(0, 8, txt=f"Tipo: {item['Tipo_Falha']}", ln=True)
        pdf.cell(0, 8, txt=f"Obs: {item['Detalhes']}", ln=True)
        pdf.cell(0, 5, txt="-"*50, ln=True)
    return bytes(pdf.output())

# --- INTERFACE ---

# Sidebar para navegação fixa
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Ir para:", ["📅 Inspeções do Dia", "📂 Histórico Geral"])

if menu == "📅 Inspeções do Dia":
    st.header("📅 Inspeções Programadas para Hoje")
    
    lista_pendentes = verificar_pendencias()
    
    if not lista_pendentes:
        st.success("✅ Todas as inspeções estão em dia!")
        if st.button("Realizar inspeção extra"):
            st.info("Selecione uma área manualmente abaixo.")
            lista_pendentes = [{"Area": a, "Subdivisao": "Avulsa"} for a in AREAS.keys()] # Simplificação para extra

    # Mostrar pendências como cards/lista
    for p in lista_pendentes:
        with st.container():
            col_txt, col_btn = st.columns([3, 1])
            col_txt.write(f"**{p['Area']}** - {p['Subdivisao']}")
            col_txt.caption(f"Periodicidade: {p['Frequencia']} | Última: {p['Ultima']}")
            
            # Ao clicar em "Iniciar", abre o formulário
            if col_btn.button(f"Iniciar 📝", key=f"btn_{p['Area']}_{p['Subdivisao']}"):
                st.session_state["em_inspecao"] = True
                st.session_state["area_atual"] = p['Area']
                st.session_state["sub_atual"] = p['Subdivisao']

    # Se uma inspeção foi iniciada, mostrar o formulário
    if st.session_state.get("em_inspecao"):
        st.divider()
        st.subheader(f"Formulário: {st.session_state['area_atual']} ({st.session_state['sub_atual']})")
        
        nome_usuario = st.text_input("Seu nome (Inspetor):", key="nome_insp")
        senha_area = st.text_input("Senha da Área:", type="password")
        
        area_info = AREAS[st.session_state['area_atual']]
        
        if senha_area == area_info["senha"]:
            st.info("Acesso liberado. Preencha os itens abaixo:")
            
            respostas = []
            for item in area_info["itens"]:
                c1, c2 = st.columns([1, 2])
                with c1:
                    status = st.radio(f"**{item}**", ["Conforme", "Não Conforme"], key=f"status_{item}")
                
                falha, obs, foto_n = "", "", ""
                if status == "Não Conforme":
                    with c2:
                        falha = st.selectbox("Tipo de falha", ["Limpeza", "Pintura", "Reparo", "Troca"], key=f"tipo_{item}")
                        obs = st.text_input("Detalhes", key=f"obs_{item}")
                        foto = st.file_uploader("Foto", type=["jpg","png"], key=f"foto_{item}")
                        if foto:
                            foto_n = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            os.makedirs("fotos", exist_ok=True)
                            with open(foto_n, "wb") as f: f.write(foto.getbuffer())
                
                respostas.append({"Item": item, "Status": status, "Tipo_Falha": falha, "Detalhes": obs, "Foto_Path": foto_n})

            if st.button("Finalizar Inspeção"):
                if not nome_usuario:
                    st.error("Nome obrigatório!")
                else:
                    # Salvar no CSV
                    data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                    novo_reg = [[data_hoje, nome_usuario, st.session_state['area_atual'], st.session_state['sub_atual'], r["Item"], r["Status"], r["Tipo_Falha"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                    df_h = carregar_historico()
                    pd.concat([df_h, pd.DataFrame(novo_reg, columns=df_h.columns)]).to_csv(HISTORICO_FILE, index=False)
                    
                    st.success("Inspeção salva!")
                    
                    # Gerar ações de exportação se houver falhas
                    ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                    if ncs:
                        st.warning("Falhas detectadas! Baixe o relatório:")
                        pdf = gerar_pdf(ncs, st.session_state['area_atual'], st.session_state['sub_atual'], nome_usuario)
                        st.download_button("Baixar PDF", pdf, "Relatorio.pdf", "application/pdf")
                        
                        corpo_msg = f"Falhas em {st.session_state['area_atual']}:\n" + "\n".join([f"- {n['Item']}" for n in ncs])
                        link_z = f"https://api.whatsapp.com/send?text={urllib.parse.quote(corpo_msg)}"
                        st.link_button("Enviar via WhatsApp", link_z)
                    
                    # Resetar estado
                    st.session_state["em_inspecao"] = False
                    st.rerun()

        elif senha_area != "":
            st.error("Senha incorreta")

elif menu == "📂 Histórico Geral":
    st.header("📂 Histórico de Inspeções")
    df = carregar_historico()
    df_ncs = df[df["Status"] == "Não Conforme"]
    
    for idx, row in df_ncs.iloc[::-1].iterrows():
        with st.expander(f"{row['Data']} - {row['Item']} ({row['Subdivisao']}) - Por: {row['Usuario']}"):
            st.write(f"**Área:** {row['Area']} | **Falha:** {row['Tipo_Falha']}")
            st.write(f"**Obs:** {row['Detalhes']}")
            if str(row['Foto_Path']) != "nan":
                st.image(row['Foto_Path'], width=250)
