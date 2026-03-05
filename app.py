import streamlit as st
from fpdf import FPDF
import urllib.parse

# Configurações de Estilo Personalizadas
st.markdown("""
    <style>
    .titulo-inspecao {
        color: #0000FF;
        font-weight: bold;
        font-size: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("🏛️ Zelador Virtual")

    # 1. Seleção de Área
    area = st.selectbox("Selecione a Área", ["Escolha...", "Sede Social", "Operacional"])
    
    if area == "Escolha...":
        st.info("Por favor, selecione uma área para começar.")
        return

    # 2. Identificação e Senha
    nome_usuario = st.text_input("Identifique-se (Seu Nome):")
    senha_digitada = st.text_input("Digite a senha da área:", type="password")

    # Validação de Senha
    senhas = {"Sede Social": "SSICS", "Operacional": "OICS"}
    
    if senha_digitada == senhas[area]:
        st.success(f"Acesso liberado: {area}")
        
        # 3. Definição de Subdivisões e Itens
        if area == "Sede Social":
            subdivisoes = ["Terraço", "1º Andar", "2º Andar"]
            itens_inspecao = ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
        else:
            subdivisoes = ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", 
                           "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"]
            itens_inspecao = ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]

        sub_escolhida = st.selectbox(f"Selecione o local em {area}", subdivisoes)
        
        # 4. Checklist de Inspeção
        st.markdown(f'<p class="titulo-inspecao">{sub_escolhida}</p>', unsafe_allow_html=True)
        
        relatorio_nc = []

        for item in itens_inspecao:
            col1, col2 = st.columns([1, 2])
            with col1:
                status = st.radio(f"Status: {item}", ["Conforme", "Não Conforme"], key=f"radio_{item}")
            
            if status == "Não Conforme":
                with col2:
                    acao = st.selectbox("Ação Necessária", ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], key=f"acao_{item}")
                    obs = st.text_input("Observação (Opcional)", key=f"obs_{item}")
                    relatorio_nc.append({"Item": item, "Problema": acao, "Obs": obs})
            st.divider()

        # 5. Finalização e Relatórios
        if st.button("Finalizar e Gerar Relatório"):
            if not relatorio_nc:
                st.balloons()
                st.success("Tudo em conformidade! Nenhum relatório gerado.")
            else:
                st.subheader("Relatório de Não Conformidades")
                resumo_texto = f"Relatório de Inspeção - {area} ({sub_escolhida})\nInspetor: {nome_usuario}\n\n"
                for nc in relatorio_nc:
                    resumo_texto += f"- {nc['Item']}: {nc['Problema']} ({nc['Obs']})\n"
                
                st.text_area("Conteúdo do Relatório", resumo_texto, height=200)

                # Botão WhatsApp
                msg_whatsapp = urllib.parse.quote(resumo_texto)
                st.markdown(f"[📲 Enviar por WhatsApp](https://wa.me/?text={msg_whatsapp})")

                # Botão E-mail
                assunto = f"Inspecao_{area}_{sub_escolhida}"
                st.markdown(f"[📧 Enviar por E-mail](mailto:?subject={assunto}&body={msg_whatsapp})")

                # Geração de PDF (Simples)
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt=f"Relatório de Zeladoria - {area}", ln=True, align='C')
                for line in resumo_texto.split('\n'):
                    pdf.cell(200, 10, txt=line, ln=True)
                
                pdf_output = pdf.output(dest='S').encode('latin-1')
                st.download_button(label="📄 Baixar Relatório em PDF", data=pdf_output, file_name="relatorio_zeladoria.pdf", mime="application/pdf")

    elif senha_digitada != "":
        st.error("Senha incorreta!")

if __name__ == "__main__":
    main()
