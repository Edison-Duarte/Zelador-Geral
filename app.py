import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import json
import os

# --- CONFIGURAÇÕES E BANCO DE DADOS SIMPLIFICADO ---
DB_FILE = "historico_inspecoes.json"

def carregar_historico():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return []

def salvar_inspecao(dados):
    historico = carregar_historico()
    historico.append(dados)
    with open(DB_FILE, "w") as f:
        json.dump(historico, f, indent=4)

# --- LÓGICA DE PERIODICIDADE ---
# Definindo periodicidade (em dias)
PERIODICIDADE = {
    "Sede Social": 7,  # Semanal
    "Operacional": 3   # A cada 3 dias (maior desgaste)
}

def verificar_pendencias():
    historico = carregar_historico()
    status = {}
    for area in PERIODICIDADE.keys():
        ultimas = [i for i in historico if i['area'] == area]
        if not ultimas:
            status[area] = "⚠️ Nunca inspecionado"
        else:
            ultima_data = datetime.strptime(ultimas[-1]['data'], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > ultima_data + timedelta(days=PERIODICIDADE[area]):
                status[area] = f"🔴 Atrasado (Última: {ultima_data.strftime('%d/%m')})"
            else:
                status[area] = "🟢 Em dia"
    return status

# --- INTERFACE ---
st.set_page_config(page_title="Zelador Virtual IC", layout="wide")
st.title("🏛️ Zelador Virtual")

menu = st.sidebar.selectbox("Menu", ["Nova Inspeção", "Histórico", "Pendências"])

if menu == "Pendências":
    st.subheader("Status de Periodicidade")
    for area, st_msg in verificar_pendencias().items():
        st.write(f"**{area}**: {st_msg}")

elif menu == "Nova Inspeção":
    # 1. Identificação
    col1, col2 = st.columns(2)
    usuario = col1.text_input("Nome do Inspetor")
    area_sel = col2.selectbox("Área", ["Sede Social", "Operacional"])
    
    # 2. Senha
    senha = st.text_input("Senha da Área", type="password")
    senhas_validas = {"Sede Social": "SSICS", "Operacional": "OPICS"}
    
    if senha == senhas_validas[area_sel]:
        st.success("Acesso Liberado")
        
        # 3. Subdivisões e Itens
        if area_sel == "Sede Social":
            subs = ["Terraço", "1º Andar", "2º Andar"]
            itens = ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"]
        else:
            subs = ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv"] # ... adicione os outros
            itens = ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"]
        
        sub_sel = st.selectbox("Subdivisão", subs)
        
        # 4. Checklist
        st.divider()
        respostas = []
        for item in itens:
            st.write(f"### {item}")
            col_a, col_b, col_c = st.columns([2, 3, 3])
            
            status = col_a.radio(f"Status {item}", ["Conforme", "Não Conforme"], key=f"rad_{item}")
            
            obs = ""
            acao = ""
            foto = None
            
            if status == "Não Conforme":
                acao = col_b.selectbox("Ação Necessária", ["Limpeza Imediata", "Pintura", "Reparo", "Troca de componentes"], key=f"sel_{item}")
                obs = col_c.text_area("Detalhes (Opcional)", key=f"txt_{item}")
                foto = st.file_uploader(f"Foto da irregularidade ({item})", type=['jpg', 'png'], key=f"foto_{item}")
            
            respostas.append({"item": item, "status": status, "acao": acao, "obs": obs})

        if st.button("Finalizar Inspeção"):
            dados_finais = {
                "inspetor": usuario,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "area": area_sel,
                "subdivisao": sub_sel,
                "check": [r for r in respostas if r['status'] == "Não Conforme"]
            }
            salvar_inspecao(dados_finais)
            st.balloons()
            st.success("Relatório de Não Conformidades gerado com sucesso!")
            
            # Exibir resumo das Não Conformidades
            if dados_finais["check"]:
                st.table(pd.DataFrame(dados_finais["check"]))
                # Aqui entraria a lógica de PDF e compartilhamento
            else:
                st.info("Tudo em conformidade! Nenhuma ação necessária.")

elif menu == "Histórico":
    st.subheader("📜 Histórico de Inspeções")
    hist = carregar_historico()
    if hist:
        df_hist = pd.DataFrame(hist)
        st.dataframe(df_hist[["data", "area", "subdivisao", "inspetor"]])
        
        idx = st.number_input("Ver detalhes do índice:", min_value=0, max_value=len(hist)-1, step=1)
        st.json(hist[idx])
    else:
        st.write("Nenhum registro encontrado.")
