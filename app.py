import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide")

HISTORICO_FILE = "historico_inspecoes.csv"
if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Tipo_Falha", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

# --- FUNÇÕES DE EXPORTAÇÃO ---
def gerar_pdf(ncs, area, subarea, usuario):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, txt="Relatório de Não Conformidades", ln=True, align='C')
    
    pdf.set_font("Helvetica", size=12)
    pdf.ln(10)
    pdf.cell(0, 10, txt=f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, txt=f"Área: {area} - {subarea}", ln=True)
    pdf.cell(0, 10, txt=f"Inspecionado por: {usuario}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, txt="ITENS COM FALHA:", ln=True)
    
    for item in ncs:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, txt=f"Item: {item['Item']}", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, txt=f"Tipo: {item['Tipo_Falha']}", ln=True)
        pdf.cell(0, 8, txt=f"Observação: {item['Detalhes']}", ln=True)
        pdf.cell(0, 5, txt="-"*50, ln=True)
    
    try:
        return bytes(pdf.output())
    except TypeError:
        return pdf.output(dest='S').encode('latin-1', errors='replace')

# NOVA FUNÇÃO: Enviar e-mail com anexos
def enviar_email_automatico(ncs, area, subarea, usuario, email_destino, pdf_bytes):
    # ATENÇÃO: Substitua pelos dados reais da conta que vai disparar o e-mail
    REMETENTE = "seu_email_sistema@gmail.com"
    SENHA = "sua_senha_de_app_aqui" 
    
    msg = MIMEMultipart()
    msg['From'] = REMETENTE
    msg['To'] = email_destino
    msg['Subject'] = f"🚨 Inspeção Zeladoria - {area} ({subarea})"

    # Montando o texto do e-mail listando as falhas
    corpo_email = f"Olá,\n\nSegue o relatório de inspeção de zeladoria realizado por {usuario} em {datetime.now().strftime('%d/%m/%Y às %H:%M')}.\n\n"
    corpo_email += f"📍 **Local:** {area} - {subarea}\n\n"
    corpo_email += "📋 **NÃO CONFORMIDADES ENCONTRADAS:**\n"
    
    for nc in ncs:
        corpo_email += f"\n🔸 Item: {nc['Item']}\n"
        corpo_email += f"   - Tipo de Falha: {nc['Tipo_Falha']}\n"
        corpo_email += f"   - Observação: {nc['Detalhes']}\n"
    
    msg.attach(MIMEText(corpo_email, 'plain'))

    # Anexando o PDF
    anexo_pdf = MIMEApplication(pdf_bytes, _subtype="pdf")
    anexo_pdf.add_header('Content-Disposition', 'attachment', filename=f"Relatorio_{subarea}.pdf")
    msg.attach(anexo_pdf)

    # Anexando as fotos
    for nc in ncs:
        if nc['Foto_Path'] and os.path.exists(nc['Foto_Path']):
            with open(nc['Foto_Path'], 'rb') as f:
                img_data = f.read()
            # Nomeia a foto com o nome do item para facilitar a identificação
            nome_foto = f"Foto_{nc['Item']}.jpg"
            anexo_img = MIMEImage(img_data, name=nome_foto)
            msg.attach(anexo_img)

    # Conectando ao servidor SMTP do Gmail e enviando
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(REMETENTE, SENHA)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

# --- BANCO DE DADOS DE ÁREAS ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "subs": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")

menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.header("📋 Check-list de Inspeção")
    
    nome_usuario = st.text_input("Seu nome:")
    area_selecionada = st.selectbox("Selecione a Área:", ["Selecione..."] + list(AREAS.keys()))

    if area_selecionada != "Selecione...":
        senha_input = st.text_input("Senha da Área:", type="password")
        
        if senha_input == AREAS[area_selecionada]["senha"]:
            st.success("Acesso Liberado!")
            sub_area = st.selectbox(f"Subdivisão de {area_selecionada}:", AREAS[area_selecionada]["subs"])
            
            st.divider()
            st.subheader(f"Inspecionando: {sub_area}")
            
            respostas = []
            
            for item in AREAS[area_selecionada]["itens"]:
                col1, col2 = st.columns([1, 2])
                with col1:
                    status = st.radio(f"**{item}**", ["Conforme", "Não Conforme"], key=item)
                
                falha_tipo = ""
                detalhe = ""
                foto_nome = ""
                
                if status == "Não Conforme":
                    with col2:
                        falha_tipo = st.selectbox(f"Tipo de falha ({item})", ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], key=f"tipo_{item}")
                        detalhe = st.text_input(f"Observações ({item})", key=f"obs_{item}")
                        foto = st.file_uploader(f"Foto ({item})", type=["jpg", "png", "jpeg"], key=f"foto_{item}")
                        if foto:
                            foto_nome = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            os.makedirs("fotos", exist_ok=True)
                            with open(foto_nome, "wb") as f:
                                f.write(foto.getbuffer())
                
                respostas.append({
                    "Item": item, "Status": status, "Tipo_Falha": falha_tipo, 
                    "Detalhes": detalhe, "Foto_Path": foto_nome
                })

            if st.button("Finalizar Inspeção"):
                ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                
                novo_registro = []
                data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                for r in respostas:
                    novo_registro.append([data_atual, nome_usuario, area_selecionada, sub_area, r["Item"], r["Status"], r["Tipo_Falha"], r["Detalhes"], r["Foto_Path"]])
                
                df_hist = pd.read_csv(HISTORICO_FILE)
                df_novo = pd.DataFrame(novo_registro, columns=df_hist.columns)
                pd.concat([df_hist, df_novo]).to_csv(HISTORICO_FILE, index=False)

                if ncs:
                    st.warning("⚠️ Relatório de Não Conformidades Gerado!")
                    df_relatorio = pd.DataFrame(ncs)
                    st.table(df_relatorio[["Item", "Tipo_Falha", "Detalhes"]])
                    
                    st.write("### 📤 Ações de Envio")
                    
                    # Gera o PDF em background para podermos usá-lo tanto no botão quanto no anexo de e-mail
                    pdf_data = gerar_pdf(ncs, area_selecionada, sub_area, nome_usuario)
                    
                    col_pdf, col_zap = st.columns(2)
                    col_pdf.download_button(
                        label="📄 Baixar PDF", 
                        data=pdf_data, 
                        file_name=f"Relatorio_{sub_area}_{datetime.now().strftime('%Y%m%d')}.pdf", 
                        mime="application/pdf"
                    )

                    # Construindo a mensagem detalhada para o WhatsApp também
                    msg_whatsapp = f"🚨 *Relatório de Zeladoria*\n\nLocal: {area_selecionada} ({sub_area})\nInspecionado por: {nome_usuario}\n\n*Falhas Encontradas:*\n"
                    for nc in ncs:
                        msg_whatsapp += f"- {nc['Item']}: {nc['Tipo_Falha']} ({nc['Detalhes']})\n"
                    
                    link_whatsapp = f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_whatsapp)}"
                    col_zap.link_button("💬 Enviar Resumo no WhatsApp", link_whatsapp)

                    st.divider()
                    st.write("📧 **Enviar Relatório Completo por E-mail (com fotos e PDF)**")
                    email_destinatario = st.text_input("E-mail do Gestor/Manutenção:")
                    if st.button("Enviar E-mail"):
                        if email_destinatario:
                            with st.spinner('Enviando e-mail com anexos...'):
                                sucesso = enviar_email_automatico(ncs, area_selecionada, sub_area, nome_usuario, email_destinatario, pdf_data)
                                if sucesso:
                                    st.success(f"E-mail enviado com sucesso para {email_destinatario}!")
                        else:
                            st.error("Por favor, digite um endereço de e-mail válido.")

                else:
                    st.success("Tudo em conformidade! Nenhuma ação necessária.")

        elif senha_input != "":
            st.error("Senha incorreta!")

elif menu == "Histórico":
    st.header("📂 Histórico de Inspeções (Não Conformidades)")
    if os.path.exists(HISTORICO_FILE):
        df_hist = pd.read_csv(HISTORICO_FILE)
        df_ncs = df_hist[df_hist["Status"] == "Não Conforme"]
        
        if not df_ncs.empty:
            for idx, row in df_ncs.iterrows():
                with st.expander(f"{row['Data']} - {row['Area']} ({row['Subdivisao']})"):
                    st.write(f"**Item:** {row['Item']}")
                    st.write(f"**Tipo:** {row['Tipo_Falha']}")
                    st.write(f"**Detalhes:** {row['Detalhes']}")
                    if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                        st.image(row['Foto_Path'], width=300)
        else:
            st.info("Nenhuma não conformidade registrada.")
