import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from fpdf import FPDF

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Zelador Virtual", layout="wide", page_icon="🏛️")

HISTORICO_FILE = "historico_inspecoes.csv"

# --- LÓGICA DE CORREÇÃO E INICIALIZAÇÃO DO CSV ---
if os.path.exists(HISTORICO_FILE):
    try:
        df_fix = pd.read_csv(HISTORICO_FILE)
        if "Tipo_Falha" in df_fix.columns:
            df_fix = df_fix.rename(columns={"Tipo_Falha": "Acao"})
            df_fix.to_csv(HISTORICO_FILE, index=False)
    except: pass
else:
    df_init = pd.DataFrame(columns=["Data", "Usuario", "Area", "Subdivisao", "Item", "Status", "Acao", "Detalhes", "Foto_Path"])
    df_init.to_csv(HISTORICO_FILE, index=False)

# --- BANCO DE DADOS DE ÁREAS ---
AREAS = {
    "Sede Social": {
        "senha": "SSICS",
        "subs": ["Terraço", "1º Andar", "2º Andar"],
        "itens": ["Lâmpadas", "Piso", "Corrimões", "Janelas", "Limpeza", "Pintura"],
        "periodicidade_dias": 15
    },
    "Operacional": {
        "senha": "OPICS",
        "subs": ["Cais I", "Cais do Meio", "Cais II", "Cais III", "Bacia IV", "Hangar Serv", "Hangar 1", "Hangar 2", "Hangar 3", "Hangar 4", "Hangar 5", "Hangar 6", "Hangar 7", "Boxes"],
        "itens": ["Piso", "Caixas de energia", "Lâmpadas/Iluminação", "Estrutura", "Limpeza", "Pintura"],
        "periodicidade_dias": 7 
    }
}

# --- FUNÇÕES ---
def verificar_pendencias():
    if not os.path.exists(HISTORICO_FILE): return []
    try:
        df = pd.read_csv(HISTORICO_FILE)
        if df.empty: return []
        df['Data_dt'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        pendencias = []
        hoje = datetime.now()
        for area, info in AREAS.items():
            prazo = info['periodicidade_dias']
            for sub in info['subs']:
                ultima = df[(df['Area'] == area) & (df['Subdivisao'] == sub)]
                if not ultima.empty:
                    dias = (hoje - ultima['Data_dt'].max()).days
                    if dias >= prazo:
                        pendencias.append(f"🔴 **{area} - {sub}** (Última há {dias} dias)")
        return pendencias
    except: return []

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
        pdf.cell(0, 8, txt=f"Ação Necessária: {item['Acao']}", ln=True)
        obs_limpa = str(item['Detalhes']).encode('latin-1', 'ignore').decode('latin-1')
        pdf.cell(0, 8, txt=f"Obs: {obs_limpa}", ln=True)
        pdf.ln(5)
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str): return pdf_output.encode('latin-1')
    return pdf_output

# --- INTERFACE ---
st.title("🏛️ Zelador Virtual")
menu = st.sidebar.selectbox("Navegação", ["Nova Inspeção", "Histórico"])

if menu == "Nova Inspeção":
    st.header("📋 Check-list de Inspeção")
    pendentes = verificar_pendencias()
    if pendentes:
        st.warning("### ⚠️ Áreas Pendentes:")
        for p in pendentes: st.write(p)
    
    nome_usuario = st.text_input("Nome do Inspetor:")
    area_sel = st.selectbox("Área Principal:", ["Selecione..."] + list(AREAS.keys()))

    if area_sel != "Selecione...":
        senha_in = st.text_input("Senha da Área:", type="password")
        if senha_in == AREAS[area_sel]["senha"]:
            st.success("Acesso Liberado!")
            sub_area = st.selectbox(f"Subdivisão:", AREAS[area_sel]["subs"])
            st.divider()
            
            respostas = []
            for item in AREAS[area_sel]["itens"]:
                st.markdown(f"#### {item}")
                status = st.radio(f"Status para {item}", ["Conforme", "Não Conforme"], key=f"s_{item}", horizontal=True)
                acao_val, detalhe, foto_path = "", "", ""
                if status == "Não Conforme":
                    col_nc1, col_nc2 = st.columns([1, 1])
                    with col_nc1:
                        acao_val = st.selectbox(f"Ação necessária:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], key=f"a_{item}")
                        detalhe = st.text_input(f"Observações:", key=f"o_{item}")
                    with col_nc2:
                        foto = st.file_uploader(f"Foto ({item})", type=["jpg", "png", "jpeg"], key=f"f_{item}")
                        if foto:
                            foto_path = f"fotos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{item}.jpg"
                            os.makedirs("fotos", exist_ok=True)
                            with open(foto_path, "wb") as f: f.write(foto.getbuffer())
                respostas.append({"Item": item, "Status": status, "Acao": acao_val, "Detalhes": detalhe, "Foto_Path": foto_path})
                st.divider()

            if st.button("🚀 Finalizar e Enviar"):
                if not nome_usuario: st.error("Preencha o nome!")
                else:
                    ncs = [r for r in respostas if r["Status"] == "Não Conforme"]
                    df_hist = pd.read_csv(HISTORICO_FILE)
                    novo_reg = [[datetime.now().strftime("%d/%m/%Y %H:%M"), nome_usuario, area_sel, sub_area, r["Item"], r["Status"], r["Acao"], r["Detalhes"], r["Foto_Path"]] for r in respostas]
                    pd.concat([df_hist, pd.DataFrame(novo_reg, columns=df_hist.columns)]).to_csv(HISTORICO_FILE, index=False)
                    if ncs:
                        pdf_bytes = gerar_pdf(ncs, area_sel, sub_area, nome_usuario)
                        st.download_button("📥 Baixar PDF", pdf_bytes, f"Relatorio_{sub_area}.pdf")
                    st.success("Relatório registrado!")

elif menu == "Histórico":
    st.header("📂 Histórico de Ocorrências")
    if os.path.exists(HISTORICO_FILE):
        df = pd.read_csv(HISTORICO_FILE)
        filtro_area = st.selectbox("🔍 Filtrar por Área:", ["Mostrar Tudo", "Sede Social", "Operacional"])
        df_display = df[df["Status"] == "Não Conforme"].copy()
        if filtro_area != "Mostrar Tudo": df_display = df_display[df_display["Area"] == filtro_area]

        for idx, row in df_display.iloc[::-1].iterrows():
            with st.expander(f"🗓️ {row['Data']} | {row['Item']} ({row['Subdivisao']})"):
                col_info, col_img = st.columns([2, 1])
                with col_info:
                    st.write(f"**Ação:** {row.get('Acao', 'N/A')}")
                    st.write(f"**Detalhes:** {row['Detalhes']}")
                    st.divider()
                    
                    # --- SISTEMA DE EDIÇÃO ---
                    if st.checkbox("✏️ Editar este registro", key=f"edit_chk_{idx}"):
                        senha_edit = st.text_input("Senha para editar:", type="password", key=f"pwd_edit_{idx}")
                        if senha_edit == AREAS[row['Area']]["senha"]:
                            nova_acao = st.selectbox("Nova Ação:", ["Limpeza Imediata", "Pintura", "Reparo", "Troca"], index=0, key=f"new_acao_{idx}")
                            novo_detalhe = st.text_area("Novas Observações:", value=row['Detalhes'], key=f"new_det_{idx}")
                            nova_foto = st.file_uploader("Substituir/Adicionar Foto:", type=["jpg","png","jpeg"], key=f"new_foto_{idx}")
                            
                            if st.button("Salvar Alterações", key=f"save_{idx}"):
                                df_full = pd.read_csv(HISTORICO_FILE)
                                df_full.at[idx, 'Acao'] = nova_acao
                                df_full.at[idx, 'Detalhes'] = novo_detalhe
                                if nova_foto:
                                    path = f"fotos/edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                                    os.makedirs("fotos", exist_ok=True)
                                    with open(path, "wb") as f: f.write(nova_foto.getbuffer())
                                    df_full.at[idx, 'Foto_Path'] = path
                                df_full.to_csv(HISTORICO_FILE, index=False)
                                st.success("Atualizado!")
                                st.rerun()
                        elif senha_edit: st.error("Senha incorreta")
                    
                    # --- SISTEMA DE EXCLUSÃO ---
                    if st.checkbox("🗑️ Excluir este registro", key=f"del_chk_{idx}"):
                        senha_del = st.text_input("Senha para excluir:", type="password", key=f"pwd_del_{idx}")
                        if st.button("Confirmar Exclusão", key=f"btn_del_{idx}"):
                            if senha_del == AREAS[row['Area']]["senha"]:
                                df_full = pd.read_csv(HISTORICO_FILE)
                                df_full = df_full.drop(idx)
                                df_full.to_csv(HISTORICO_FILE, index=False)
                                st.rerun()
                            else: st.error("Senha incorreta")
                            
                with col_img:
                    if str(row['Foto_Path']) != "nan" and row['Foto_Path']:
                        st.image(row['Foto_Path'], use_container_width=True)
