import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide")

HISTORICO_FILE = "historico_inspecoes.csv"
if not os.path.exists(HISTORICO_FILE):
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Tipo_Falha", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

# --- GERADOR DE PDF (Para baixar e anexar manualmente) ---
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
        pdf.ln(2)
    return bytes(pdf.output())

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
            sub_area = st.selectbox(f"Subdivisão:", AREAS[area_selecionada]["subs"])
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
                ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                
                # Salvar no CSV
                data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                novo_registro = [[data_atual, nome_usuario, area_selecionada, sub_area, r["Item"], r["Status"], r["Tipo_Falha"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                df_hist = pd.read_csv(HISTORICO_FILE)
                pd.concat([df_hist, pd.DataFrame(novo_registro, columns=df_hist.columns)]).to_csv(HISTORICO_FILE, index=False)

                if ncs:
                    st.warning(f"⚠️ {len(ncs)} Não Conformidades encontradas!")
                    
                    # 1. Preparar PDF para Download
                    pdf_bytes = gerar_pdf(ncs, area_selecionada, sub_area, nome_usuario)
                    st.download_button("📥 1º Baixe o PDF do Relatório", pdf_bytes, f"Relatorio_{sub_area}.pdf", "application/pdf")

                    # 2. Montar texto do E-mail detalhado
                    corpo_email = f"Relatório de Inspeção - Zeladoria\n"
                    corpo_email += f"Local: {area_selecionada} ({sub_area})\n"
                    corpo_email += f"Realizado por: {nome_usuario}\n"
                    corpo_email += "-"*30 + "\n\n"
                    corpo_email += "ITENS PONTUADOS:\n"
                    
                    for nc in ncs:
                        corpo_email += f"• {nc['Item']}: {nc['Tipo_Falha']}\n  Obs: {nc['Detalhes']}\n\n"
                    
                    corpo_email += "\n(Favor anexar o PDF e as fotos baixadas a este e-mail.)"
                    
                    # 3. Botão de E-mail (Abre o app padrão)
                    assunto = f"ALERTA: Manutenção {sub_area}"
                    link_mailto = f"mailto:?subject={urllib.parse.quote(assunto)}&body={urllib.parse.quote(corpo_email)}"
                    
                    st.link_button("📧 2º Abrir meu E-mail agora", link_mailto)
                    
                    # 4. WhatsApp
                    link_zap = f"https://api.whatsapp.com/send?text={urllib.parse.quote(corpo_email)}"
                    st.link_button("💬 Enviar Resumo via WhatsApp", link_zap)
                else:
                    st.success("Tudo em conformidade!")

elif menu == "Histórico":
    st.header("📂 Histórico de Falhas")
    df_hist = pd.read_csv(HISTORICO_FILE)
    df_ncs = df_hist[df_hist["Status"] == "Não Conforme"]
    for idx, row in df_ncs.iterrows():
        with st.expander(f"{row['Data']} - {row['Item']} ({row['Subdivisao']})"):
            st.write(f"**Falha:** {row['Tipo_Falha']} | **Obs:** {row['Detalhes']}")
            if str(row['Foto_Path']) != "nan": st.image(row['Foto_Path'], width=250)
