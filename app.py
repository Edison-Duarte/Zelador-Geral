import streamlit as st
import pandas as pd
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import base64

# --- CONFIGURAÇÕES E DADOS ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "subs": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
    },
    "Operacional": {
        "senha": "OPICS",
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", 
                 "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
    }
}

HISTORICO_FILE = "historico_inspecoes.csv"

def salvar_dados(dados):
    df = pd.DataFrame(dados)
    if not os.path.isfile(HISTORICO_FILE):
        df.to_csv(HISTORICO_FILE, index=False)
    else:
        df.to_csv(HISTORICO_FILE, mode='a', header=False, index=False)

# --- INTERFACE ---
st.set_page_config(page_title="Zelador Virtual ICS", layout="centered")
st.title("📋 Zelador Virtual")

# --- CRONOGRAMA INTELIGENTE ---
hoje = datetime.now().strftime("%A")
cronograma = {
    "Monday": "Hangar 1 e Hangar 2",
    "Tuesday": "Sede Social (Todos os andares)",
    "Wednesday": "Cais I, II e III",
    "Thursday": "Hangar 3 e Hangar 4",
    "Friday": "Boxes e Bacia IV",
    "Saturday": "Hangar 5, 6 e 7",
    "Sunday": "Revisão Geral de Limpeza"
}
st.info(f"💡 **Cronograma do Dia:** Hoje deve ser feita a inspeção do **{cronograma.get(hoje, 'Área de Plantão')}**")

# --- LOGIN E SELEÇÃO ---
area_sel = st.selectbox("Selecione a Área", [""] + list(AREAS.keys()))

if area_sel:
    sub_sel = st.selectbox(f"Selecione a subdivisão de {area_sel}", AREAS[area_sel]["subs"])
    usuario = st.text_input("Identifique-se (Nome)")
    senha = st.text_input("Senha da Área", type="password")

    if senha == AREAS[area_sel]["senha"]:
        st.success("Acesso Liberado")
        
        st.subheader(f"Checklist: {sub_sel}")
        respostas = []
        
        for item in AREAS[area_sel]["itens"]:
            col1, col2 = st.columns([1, 2])
            with col1:
                status = st.radio(f"{item}", ["Conforme", "Não Conforme"], key=f"status_{item}")
            
            detalhes = {}
            if status == "Não Conforme":
                with col2:
                    tipo_falha = st.selectbox("Ação necessária", ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], key=f"tipo_{item}")
                    obs = st.text_area("Especificação (Opcional)", key=f"obs_{item}")
                    foto = st.file_uploader("Foto da NC", type=['png', 'jpg', 'jpeg'], key=f"foto_{item}")
                    detalhes = {"item": item, "status": status, "acao": tipo_falha, "obs": obs, "foto": foto.name if foto else "Sem foto"}
            else:
                detalhes = {"item": item, "status": status, "acao": "-", "obs": "-", "foto": "-"}
            
            respostas.append(detalhes)

        if st.button("Finalizar Inspeção"):
            ncs = [r for r in respostas if r["status"] == "Não Conforme"]
            
            # Preparar dados para histórico
            data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            novos_registros = []
            for r in ncs:
                novos_registros.append({
                    "Data": data_hora, "Usuario": usuario, "Area": area_sel, 
                    "Subdivisao": sub_sel, "Item": r["item"], "Ação": r["acao"], "Obs": r["obs"]
                })
            
            if novos_registros:
                salvar_dados(novos_registros)
                st.warning("⚠️ Relatório de Não Conformidades Gerado!")
                st.table(pd.DataFrame(ncs).drop(columns=['foto']))
                
                # Botões de exportação (Simulação)
                st.download_button("Baixar Relatório PDF", data="Conteúdo do PDF", file_name=f"NC_{sub_sel}.pdf")
                st.write(f"Link para WhatsApp: [Enviar via WhatsApp](https://wa.me/?text=Relatorio%20NC%20{sub_sel})")
            else:
                st.success("Tudo conforme! Nenhuma pendência registrada.")

    elif senha != "":
        st.error("Senha incorreta")

# --- HISTÓRICO ---
st.divider()
st.subheader("📜 Histórico de Inspeções (NCs)")
if os.path.isfile(HISTORICO_FILE):
    df_hist = pd.read_csv(HISTORICO_FILE)
    st.dataframe(df_hist)
else:
    st.write("Nenhum histórico registrado ainda.")
