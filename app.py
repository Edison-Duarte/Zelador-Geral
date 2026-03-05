import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import urllib.parse

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")

# Simulação de Banco de Dados (Em produção, use st.connection ou um CSV fixo)
if 'historico' not in st.session_state:
    st.session_state.historico = []

# --- DADOS E REGRAS DE NEGÓCIO ---
AREAS = {
    "Sede Social": {
        "sub": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"],
        "senha": "SSICS"
    },
    "Operacional": {
        "sub": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", 
                "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"],
        "senha": "OPICS"
    }
}

OPCOES_NAO_CONFORME = ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"]

# --- FUNÇÕES AUXILIARES ---
def gerar_cronograma():
    dia_semana = datetime.now().weekday()
    cronograma = {
        0: "Hangar 1 e Cais I",
        1: "Sede Social - 1º Andar",
        2: "Hangar 3 e Bacia IV",
        3: "Boxes e Hangar Serv",
        4: "Sede Social - Terraço",
        5: "Cais III e Hangar 7",
        6: "Revisão Geral de Limpeza"
    }
    return cronograma.get(dia_semana, "Área Geral")

def gerar_pdf(usuario, area, sub, problemas):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Relatório de Não Conformidades - Zeladoria", ln=True, align='C')
    
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(200, 10, txt=f"Inspetor: {usuario}", ln=True)
    pdf.cell(200, 10, txt=f"Local: {area} - {sub}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, txt="Itens com Problemas:", ln=True)
    pdf.set_font("Arial", size=10)
    
    for p in problemas:
        texto = f"- {p['item']}: {p['tipo']} | Obs: {p['obs']}"
        pdf.multi_cell(0, 10, txt=texto)
    
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")
st.info(f"📅 **Cronograma de Hoje:** {gerar_cronograma()}")

menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.header("📋 Checklists de Inspeção")
    
    # Identificação
    nome_usuario = st.text_input("Nome do Inspetor")
    
    # Seleção de Área
    escolha_area = st.selectbox("Selecione a Área", ["Selecione..."] + list(AREAS.keys()))
    
    if escolha_area != "Selecione...":
        senha_input = st.text_input("Senha da Área", type="password")
        
        if senha_input == AREAS[escolha_area]["senha"]:
            st.success("Acesso Liberado")
            
            sub_area = st.selectbox(f"Subdivisão de {escolha_area}", AREAS[escolha_area]["sub"])
            
            st.divider()
            st.subheader(f"Itens para Inspecionar em: {sub_area}")
            
            respostas = []
            nao_conformidades = []
            
            for item in AREAS[escolha_area]["itens"]:
                col1, col2 = st.columns([1, 2])
                with col1:
                    status = st.radio(f"Status: {item}", ["Conforme", "Não Conforme"], key=item)
                
                if status == "Não Conforme":
                    with col2:
                        tipo_falha = st.selectbox(f"Ação para {item}", OPCOES_NAO_CONFORME, key=f"tipo_{item}")
                        obs = st.text_input(f"Detalhes (opcional)", key=f"obs_{item}")
                        nao_conformidades.append({"item": item, "tipo": tipo_falha, "obs": obs})
            
            if st.button("Finalizar Inspeção"):
                if not nome_usuario:
                    st.error("Por favor, identifique-se antes de finalizar.")
                else:
                    # Salvar no Histórico
                    registro = {
                        "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Inspetor": nome_usuario,
                        "Area": escolha_area,
                        "Sub": sub_area,
                        "Problemas": nao_conformidades
                    }
                    st.session_state.historico.append(registro)
                    
                    st.success("Inspeção finalizada com sucesso!")
                    
                    if nao_conformidades:
                        st.warning(f"Foram encontradas {len(nao_conformidades)} não conformidades.")
                        
                        # Preparar Texto para Relatórios
                        texto_relatorio = f"Relatorio de Inspecao - {sub_area}\nInspetor: {nome_usuario}\n\n"
                        for n in nao_conformidades:
                            texto_relatorio += f"- {n['item']}: {n['tipo']} ({n['obs']})\n"
                        
                        # Botões de Exportação
                        col_pdf, col_wa, col_email = st.columns(3)
                        
                        with col_pdf:
                            pdf_bytes = gerar_pdf(nome_usuario, escolha_area, sub_area, nao_conformidades)
                            st.download_button("Baixar PDF", data=pdf_bytes, file_name="relatorio.pdf", mime="application/pdf")
                        
                        with col_wa:
                            wa_url = f"https://wa.me/?text={urllib.parse.quote(texto_relatorio)}"
                            st.link_button("Enviar WhatsApp", wa_url)
                            
                        with col_email:
                            subject = urllib.parse.quote(f"Não Conformidade - {sub_area}")
                            body = urllib.parse.quote(texto_relatorio)
                            st.link_button("Enviar E-mail", f"mailto:?subject={subject}&body={body}")
                    else:
                        st.balloons()
                        st.info("Tudo em ordem! Nenhuma não conformidade registrada.")
        
        elif senha_input != "":
            st.error("Senha incorreta!")

elif menu == "Histórico":
    st.header("📜 Histórico de Inspeções")
    if not st.session_state.historico:
        st.write("Nenhuma inspeção realizada ainda.")
    else:
        for idx, entry in enumerate(reversed(st.session_state.historico)):
            with st.expander(f"{entry['Data']} - {entry['Area']} ({entry['Sub']})"):
                st.write(f"**Inspetor:** {entry['Inspetor']}")
                if entry['Problemas']:
                    st.table(pd.DataFrame(entry['Problemas']))
                else:
                    st.write("✅ Sem pendências.")
