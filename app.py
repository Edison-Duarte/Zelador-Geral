import streamlit as st
from fpdf import FPDF
import urllib.parse

# Configurações iniciais da página
st.set_page_config(page_title="Zelador Virtual", page_icon="🏢")

# --- DADOS DE CONFIGURAÇÃO ---
AREAS = {
    "Sede Social": {
        "sublocais": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "sublocais": [
            "Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", 
            "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- TÍTULO ---
st.title("🏢 Zelador Virtual")
st.markdown("Sistema de inspeção e checklist predial.")

# --- SELEÇÃO DE ÁREA ---
area_selecionada = st.selectbox("Selecione a Área:", list(AREAS.keys()))
sublocal_selecionado = st.selectbox("Selecione o Local Específico:", AREAS[area_selecionada]["sublocais"])

# Identificação do Usuário
usuario = st.text_input("Identificação do Inspetor (Nome):")

st.divider()

# --- FORMULÁRIO DE INSPEÇÃO ---
inspecoes = {}
nao_conformidades = []

if usuario:
    st.subheader(f"Inspecionando: {sublocal_selecionado}")
    
    for item in AREAS[area_selecionada]["itens"]:
        st.write(f"**{item}**")
        col1, col2 = st.columns([1, 2])
        
        status = col1.radio(f"Status {item}", ["Conforme", "Não Conforme"], key=f"rad_{item}", label_visibility="collapsed")
        
        if status == "Não Conforme":
            acao = col2.selectbox("Ação necessária:", ["Limpeza Imediata", "Reparo", "Troca de Componentes"], key=f"sel_{item}")
            obs = col2.text_input(f"Observação (opcional):", key=f"txt_{item}")
            
            nao_conformidades.append({
                "Item": item,
                "Ação": acao,
                "Observação": obs if obs else "Nenhuma"
            })
    
    st.divider()

    # --- FINALIZAÇÃO E RELATÓRIO ---
    if st.button("Finalizar Relatório"):
        if not nao_conformidades:
            st.success("Tudo em conformidade! Nenhum relatório de falhas gerado.")
        else:
            st.subheader("📋 Resumo de Não Conformidades")
            
            # Montar texto do relatório
            texto_relatorio = f"RELATÓRIO DE ZELADORIA\nLocal: {area_selecionada} - {sublocal_selecionado}\nInspetor: {usuario}\n\n"
            for nc in nao_conformidades:
                st.warning(f"**{nc['Item']}**: {nc['Ação']} ({nc['Observação']})")
                texto_relatorio += f"- {nc['Item']}: {nc['Ação']} | Obs: {nc['Observação']}\n"

            # --- BOTÕES DE EXPORTAÇÃO ---
            st.divider()
            
            # 1. Gerar PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Relatorio de Nao Conformidades", ln=True, align='C')
            pdf.ln(10)
            for linha in texto_relatorio.split('\n'):
                pdf.cell(200, 10, txt=linha, ln=True)
            
            pdf_output = pdf.output(dest='S').encode('latin-1')
            st.download_button("📥 Baixar Relatório em PDF", data=pdf_output, file_name="relatorio_zeladoria.pdf", mime="application/pdf")

            # 2. WhatsApp
            texto_zap = urllib.parse.quote(texto_relatorio)
            link_zap = f"https://wa.me/?text={texto_zap}"
            st.link_button("📲 Enviar via WhatsApp", link_zap)
            
            # 3. Email
            corpo_email = urllib.parse.quote(texto_relatorio)
            link_email = f"mailto:?subject=Relatorio%20Zeladoria%20{sublocal_selecionado}&body={corpo_email}"
            st.link_button("📧 Enviar via E-mail", link_email)

else:
    st.info("Por favor, insira sua identificação para começar.")
