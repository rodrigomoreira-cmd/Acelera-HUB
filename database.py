import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_connection() -> Client:
    """Inicializa e faz o cache da ligação com o Supabase."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro nas credenciais: {e}")
        st.stop()

supabase = init_connection()

def setup_realtime_listener(table_name):
    """
    Configura o listener de Realtime. 
    Sempre que a tabela mudar, marcamos um flag no session_state.
    """
    def on_change(payload):
        # Marcamos que houve uma mudança. 
        # Nota: Não podemos chamar st.rerun() aqui dentro pois é uma thread diferente.
        st.session_state.db_updated = True
        st.session_state.last_update_payload = payload

    try:
        channel = supabase.channel(f"realtime-{table_name}")
        channel.on(
            "postgres_changes",
            event="*",
            schema="public",
            table=table_name,
            callback=on_change
        ).subscribe()
        return channel
    except Exception as e:
        # Silencioso para não quebrar a UI se o Realtime falhar
        return None