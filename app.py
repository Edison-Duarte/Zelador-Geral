import streamlit as st
from fpdf import FPDF
import datetime

# Configuração da página
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")

# Simulação de banco de dados em memória (Histórico)
if 'historico' not in st.session_state:
    st.session_state['historico'] = []

# --- DADOS DE CONFIGURAÇÃO ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "subdivisoes": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "subdivisoes": [
            "Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV",
            "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4",
            "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"
        ],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual - Inspeção")

menu = st.sidebar.selectbox("Menu", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.header("Checklist de Manutenção")
    
    # 1. Identificação
    nome_usuario = st.text_input("Nome do Inspetor:")
    area_sel = st.selectbox("Selecione a Área:", ["Selecione..."] + list(AREAS.keys()))

    if area_sel != "Selecione...":
        # 2. Senha
        senha_input = st.text_input("Digite a senha da área:", type="password")
        
        if senha_input == AREAS[area_sel]["senha"]:
            st.success("Acesso Liberado!")
            
            sub_sel = st.selectbox("Subdivisão:", AREAS[area_sel]["subdivisoes"])
            
            st.divider()
            st.subheader(f"Inspecionando: {sub_sel}")
            
            # 3. Checklist
            respostas = {}
            for item in AREAS[area_sel]["itens"]:
                col1, col2 = st.columns([1, 2])
                with col1:
                    status = st.radio(f"**{item}**", ["Conforme", "Não Conforme"], key=item)
                
                if status == "Não Conforme":
                    with col2:
                        tipo_falha = st.selectbox(f"Ação necessária ({item}):", 
                                                ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], key=f"tipo_{item}")
                        obs = st.text_input(f"Observação ({item}):", key=f"obs_{item}")
                        foto = st.file_uploader(f"Foto da evidência ({item})", type=['png', 'jpg', 'jpeg'], key=f"foto_{item}")
                        respostas[item] = {"status": status, "acao": tipo_falha, "obs": obs, "foto": foto}
                else:
                    respostas[item] = {"status": status}

            # 4. Finalização
            if st.button("Finalizar Inspeção"):
                nao_conformes = {k: v for k, v in respostas.items() if v["status"] == "Não Conforme"}
                
                data_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                relatorio_id = f"REL-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                dados_inspecao = {
                    "id": relatorio_id,
                    "data": data_atual,
                    "inspetor": nome_usuario,
                    "local": f"{area_sel} - {sub_sel}",
                    "falhas": nao_conformes
                }
                
                st.session_state['historico'].append(dados_inspecao)
                st.success("Relatório gerado com sucesso!")

                # --- EXIBIÇÃO DO RELATÓRIO ---
                st.divider()
                st.subheader("Relatório de Não Conformidades")
                if not nao_conformes:
                    st.info("Tudo em conformidade! Nada a relatar.")
                else:
                    texto_relatorio = f"Inspeção: {area_sel} ({sub_sel})\nInspetor: {nome_usuario}\nData: {data_atual}\n\nProblemas encontrados:\n"
                    for item, info in nao_conformes.items():
                        item_texto = f"- {item}: {info['acao']} | Obs: {info['obs']}\n"
                        st.warning(item_texto)
                        texto_relatorio += item_texto

                    # Botões de Ação
                    col_a, col_b = st.columns(2)
                    
                    # WhatsApp (Link dinâmico)
                    msg_whatsapp = texto_relatorio.replace("\n", "%0A")
                    with col_a:
                        st.markdown(f"[📲 Enviar via WhatsApp](https://wa.me/?text={msg_whatsapp})")
                    
                    # PDF (Simples)
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(200, 10, txt="Relatório de Zeladoria", ln=True, align='C')
                    pdf.multi_cell(0, 10, txt=texto_relatorio)
                    pdf_output = pdf.output(dest='S').encode('latin-1')
                    
                    with col_b:
                        st.download_button(label="📥 Baixar PDF", data=pdf_output, file_name=f"relatorio_{relatorio_id}.pdf", mime="application/pdf")

        elif senha_input != "":
            st.error("Senha incorreta.")

elif menu == "Histórico":
    st.header("Histórico de Inspeções")
    if not st.session_state['historico']:
        st.write("Nenhuma inspeção realizada ainda.")
    else:
        for insp in reversed(st.session_state['historico']):
            with st.expander(f"{insp['data']} - {insp['local']}"):
                st.write(f"**Inspetor:** {insp['inspetor']}")
                if insp['falhas']:
                    for item, info in insp['falhas'].items():
                        st.write(f"❌ **{item}**: {info['acao']} ({info['obs']})")
                else:
                    st.write("✅ Sem não conformidades.")
