import streamlit as st
import pandas as pd
from database import supabase

def render_tela_auditoria():
    col_header1, col_header2 = st.columns([4, 1])
    with col_header1:
        st.title("🛡️ Auditoria Global (Logs)")
    with col_header2:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar Logs", use_container_width=True):
            st.rerun()

    st.markdown("Acompanhe todas as alterações de dados e interações efetuadas no sistema por qualquer utilizador.")
    st.divider()

    try:
        # Busca todos os logs do sistema
        res = supabase.table("logs_auditoria").select("*").order("data_alteracao", desc=True).execute()
        logs = res.data
    except Exception as e:
        st.error(f"Erro ao carregar logs: {e}")
        return

    if not logs:
        st.info("Ainda não existem registos de auditoria no sistema.")
        return

    df_logs = pd.DataFrame(logs)
    df_logs['data_alteracao'] = pd.to_datetime(df_logs['data_alteracao']).dt.strftime('%d/%m/%Y %H:%M:%S')

    # Separar o que é Alteração de Campo do que é Comentário Manual
    df_comentarios = df_logs[df_logs['estado_antigo'] == 'Adição de Comentário']
    df_sistema = df_logs[df_logs['estado_antigo'] != 'Adição de Comentário']

    tab1, tab2 = st.tabs(["🔄 Alterações no Sistema", "💬 Comentários da Equipa"])

    with tab1:
        st.subheader("Rastreio de Edição de Campos")
        col1, col2 = st.columns(2)
        with col1:
            f_user_sys = st.selectbox("Filtrar por Utilizador (Ação):", ["Todos"] + list(df_sistema['quem_alterou'].dropna().unique()), key="f_usr_sys")
        with col2:
            f_cli_sys = st.text_input("Buscar por Cliente Afetado:", key="f_cli_sys", placeholder="Digite o nome...")

        df_show_sys = df_sistema.copy()
        if f_user_sys != "Todos":
            df_show_sys = df_show_sys[df_show_sys['quem_alterou'] == f_user_sys]
        if f_cli_sys:
            df_show_sys = df_show_sys[df_show_sys['quem_foi_afetado'].str.contains(f_cli_sys, case=False, na=False)]

        st.dataframe(
            df_show_sys,
            column_config={
                "data_alteracao": "Data/Hora",
                "quem_alterou": "Utilizador (Autor)",
                "quem_foi_afetado": "Cliente Afetado",
                "estado_antigo": "Valor Antigo",
                "novo_estado": "Valor Novo",
                "id": None,
                "cliente_id": None
            },
            hide_index=True,
            use_container_width=True
        )

    with tab2:
        st.subheader("Mural Global de Comentários")
        col3, col4 = st.columns(2)
        with col3:
            f_user_msg = st.selectbox("Filtrar por Utilizador (Autor):", ["Todos"] + list(df_comentarios['quem_alterou'].dropna().unique()), key="f_usr_msg")
        with col4:
            f_cli_msg = st.text_input("Buscar por Cliente:", key="f_cli_msg", placeholder="Digite o nome...")

        df_show_msg = df_comentarios.copy()
        if f_user_msg != "Todos":
            df_show_msg = df_show_msg[df_show_msg['quem_alterou'] == f_user_msg]
        if f_cli_msg:
            df_show_msg = df_show_msg[df_show_msg['quem_foi_afetado'].str.contains(f_cli_msg, case=False, na=False)]

        st.dataframe(
            df_show_msg,
            column_config={
                "data_alteracao": "Data/Hora",
                "quem_alterou": "Autor da Nota",
                "quem_foi_afetado": "Ficha do Cliente",
                "novo_estado": "Texto do Comentário",
                "estado_antigo": None,
                "id": None,
                "cliente_id": None
            },
            hide_index=True,
            use_container_width=True
        )