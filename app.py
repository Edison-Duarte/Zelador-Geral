import streamlit as st
from fpdf import FPDF
import io

# Configuração inicial da página
st.set_page_config(page_title="Zelador Virtual", page_icon="🏢")

# --- DADOS DE CONFIGURAÇÃO ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "subdivisoes": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OICS",
        "subdivisoes": [
            "Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", 
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", 
            "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- ESTADO DO APLICATIVO ---
if 'relatorio' not in st.session_state:
    st.session_state.relatorio = []
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- INTERFACE ---
st.title("🏢 Zelador Virtual")
st.info("Sistema de Inspeção e Checklist")

# 1. Identificação e Área
col1, col2 = st.columns(2)
with col1:
    usuario = st.text_input("Identificação do Usuário:")
with col2:
    area_selecionada = st.selectbox("Selecione a Área:", ["Selecione..."] + list(AREAS.keys()))

# 2. Autenticação
if area_selecionada != "Selecione...":
    senha_input = st.text_input("Digite a senha da área:", type="password")
    
    if senha_input == AREAS[area_selecionada]["senha"]:
        st.success(f"Acesso liberado para {area_selecionada}")
        
        # 3. Escolha da Subdivisão
        subdivisao = st.selectbox("Selecione o local específico:", AREAS[area_selecionada]["subdivisoes"])
        
        st.divider()
        st.subheader(f"Checklist: {subdivisao}")
        
        # 4. Formulário de Inspeção
        inspecoes = {}
        for item in AREAS[area_selecionada]["itens"]:
            st.write(f"**Item: {item}**")
            status = st.radio(f"Status de {item}", ["Conforme", "Não Conforme"], key=f"status_{item}", horizontal=True)
            
            detalhes = ""
            acao = ""
            if status == "Não Conforme":
                acao = st.selectbox(f"Ação necessária para {item}:", 
                                    ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], 
                                    key=f"acao_{item}")
                detalhes = st.text_input(f"Observação adicional para {item} (Opcional):", key=f"obs_{item}")
            
            inspecoes[item] = {"status": status, "acao": acao, "detalhes": detalhes}
            st.divider()

        # 5. Finalização
        if st.button("Finalizar Checklist"):
            nao_conformidades = []
            for item, dados in inspecoes.items():
                if dados["status"] == "Não Conforme":
                    nao_conformidades.append({
                        "Item": item,
                        "Ação": dados["acao"],
                        "Obs": dados["detalhes"]
                    })
            
            if not nao_conformidades:
                st.balloons()
                st.success("Inspeção concluída! Tudo em conformidade.")
            else:
                st.warning("Relatório de Não Conformidades Gerado!")
                
                # Montar texto do relatório
                texto_relatorio = f"RELATÓRIO DE INSPEÇÃO - {area_selecionada} ({subdivisao})\n"
                texto_relatorio += f"Inspetor: {usuario}\n"
                texto_relatorio += "-"*30 + "\n"
                for nc in nao_conformidades:
                    texto_relatorio += f"🔴 {nc['Item']}: {nc['Ação']} | Obs: {nc['Obs']}\n"
                
                st.text_area("Resumo das ocorrências:", texto_relatorio, height=200)

                # --- EXPORTAÇÃO ---
                
                # Gerar PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt=f"Relatório de Zeladoria - {subdivisao}", ln=True, align='C')
                pdf.ln(10)
                pdf.multi_cell(0, 10, txt=texto_relatorio)
                pdf_output = pdf.output(dest='S').encode('latin-1')
                
                st.download_button(label="📄 Baixar Relatório em PDF", 
                                   data=pdf_output, 
                                   file_name=f"inspecao_{subdivisao}.pdf", 
                                   mime="application/pdf")

                # Links Externos
                msg_whatsapp = f"https://wa.me/?text={texto_relatorio.replace(' ', '%20')}"
                st.link_button("📲 Enviar por WhatsApp", msg_whatsapp)
                
                email_link = f"mailto:?subject=Relatorio%20Zeladoria&body={texto_relatorio.replace(' ', '%20')}"
                st.link_button("📧 Enviar por E-mail", email_link)

    elif senha_input != "":
        st.error("Senha incorreta!")
