import streamlit as st
import pandas as pd
from fpdf import FPDF
import urllib.parse

# --- FUNÇÃO PARA GERAR PDF ---
def gerar_pdf(dados_ncs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Relatório de Não Conformidades", ln=True, align='C')
    
    pdf.set_font("Arial", size=12)
    for index, row in dados_ncs.iterrows():
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Item: {row['Item']} - Status: {row['Status']}", ln=True)
        pdf.cell(200, 10, txt=f"Falha: {row['Tipo_Falha']}", ln=True)
        pdf.cell(200, 10, txt=f"Detalhes: {row['Detalhes']}", ln=True)
        pdf.cell(200, 10, txt="-"*50, ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- DENTRO DA SUA CONDIÇÃO 'IF NCS:' NO FINALIZAR INSPEÇÃO ---
if ncs:
    df_relatorio = pd.DataFrame(ncs)
    st.table(df_relatorio[["Item", "Tipo_Falha", "Detalhes"]])
    
    st.write("---")
    
    # 1. BOTÃO PDF (Usando download_button para funcionar de verdade)
    pdf_bytes = gerar_pdf(df_relatorio)
    st.download_button(
        label="📄 Baixar Relatório PDF",
        data=pdf_bytes,
        file_name=f"inspeção_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

    # 2. WHATSAPP (Link direto)
    texto_whats = f"Olá, foram encontradas {len(ncs)} não conformidades na área {area_selecionada}."
    texto_url = urllib.parse.quote(texto_whats)
    # Substitua o número abaixo pelo número do gestor
    link_zap = f"https://api.whatsapp.com/send?phone=55XXXXXXXXXXX&text={texto_url}"
    st.link_button("💬 Enviar via WhatsApp", link_zap)

    # 3. E-MAIL (Simples link 'mailto')
    corpo_email = f"Relatorio de Inspecao - Area: {area_selecionada}"
    link_email = f"mailto:gestor@empresa.com?subject=Inspecao%20Zeladoria&body={urllib.parse.quote(corpo_email)}"
    st.link_button("📧 Enviar por E-mail", link_email)
