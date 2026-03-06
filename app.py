import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide")

# Inicialização do arquivo de histórico
HISTORICO_FILE = "historico_inspecoes.csv"
if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Tipo_Falha", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

# --- FUNÇÕES DE EXPORTAÇÃO ---
def gerar_pdf(ncs, area, subarea, usuario):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    
    # Cabeçalho
    pdf.cell(0, 10, txt="Relatório de Não Conformidades", ln=True, align='C')
    
    # Informações Gerais
    pdf.set_font("Helvetica", size=12)
    pdf.ln(10)
    pdf.cell(0, 10, txt=f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, txt=f"Área: {area} - {subarea}", ln=True)
    pdf.cell(0, 10, txt=f"Inspecionado por: {usuario}", ln=True)
    pdf.ln(10)
    
    # Título dos Itens
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, txt="ITENS COM FALHA:", ln=True)
    
    # Loop das Não Conformidades
    for item in ncs:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, txt=f"Item: {item['Item']}", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, txt=f"Tipo: {item['Tipo_Falha']}", ln=True)
        pdf.cell(0, 8, txt=f"Observação: {item['Detalhes']}", ln=True)
        pdf.cell(0, 5, txt="-"*50, ln=True)
    
    # Tratamento para fpdf2 no Streamlit
    try:
        return bytes(pdf.output())
    except TypeError:
        # Fallback caso ainda esteja usando o fpdf antigo
        return pdf.output(dest='S').encode('latin-1', errors='replace')

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
                
                # Salvar no histórico
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
                    col_pdf, col_zap, col_mail = st.columns(3)

                    # Ação PDF
                    pdf_data = gerar_pdf(ncs, area_selecionada, sub_area, nome_usuario)
                    col_pdf.download_button(
                        label="📄 Baixar PDF", 
                        data=pdf_data, 
                        file_name=f"Relatorio_{sub_area}_{datetime.now().strftime('%Y%m%d')}.pdf", 
                        mime="application/pdf"
                    )

                    # Ação WhatsApp
                    msg_whatsapp = f"🚨 *Relatório de Zeladoria*\n\nLocal: {area_selecionada} ({sub_area})\nInspecionado por: {nome_usuario}\n\nForam encontradas {len(ncs)} não conformidades."
                    link_whatsapp = f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_whatsapp)}"
                    col_zap.link_button("💬 Enviar WhatsApp", link_whatsapp)

                    # Ação E-mail
                    assunto = f"Inspeção Zeladoria - {sub_area}"
                    link_email = f"mailto:?subject={urllib.parse.quote(assunto)}&body={urllib.parse.quote(msg_whatsapp)}"
                    col_mail.link_button("📧 Enviar por E-mail", link_email)
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
