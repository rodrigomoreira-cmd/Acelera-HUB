import streamlit as st
import pandas as pd
import base64

# 1. Configuração da página - DEVE ser a primeira linha
st.set_page_config(page_title="Acelera Hub", page_icon="🔗", layout="wide", initial_sidebar_state="expanded")

# 2. Importação das Telas e Banco (Como você já tinha)
from database import supabase
from comercial import render_tela_comercial
from financeiro import render_tela_financeira
from dashboard import render_dashboard
from auditoria import render_tela_auditoria 
from mapa_mesas import render_mapa_mesas 

def render_login():
    """Função para renderizar a tela de login validando no banco de dados"""
    _, col_login, _ = st.columns([1, 1.5, 1])
    
    with col_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>🔗 Acelera Hub</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: #64748b; margin-bottom: 30px;'>Acesso Restrito</h4>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.subheader("🔐 Login")
            
            with st.form(key="form_login"):
                email = st.text_input("E-mail de Acesso:", placeholder="exemplo@grupoacelerador.com.br")
                senha = st.text_input("Senha:", type="password", placeholder="Digite a sua senha")
                
                st.write("") 
                submit_button = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
                
                if submit_button:
                    if not email.strip() or not senha.strip():
                        st.error("⚠️ Preencha o E-mail e a Senha.")
                    else:
                        try:
                            email_limpo = email.strip().lower()
                            senha_limpa = senha.strip()
                            
                            res = supabase.table("usuarios").select("*").eq("email", email_limpo).eq("senha", senha_limpa).execute()
                            
                            if res.data and len(res.data) > 0:
                                user = res.data[0]
                                st.session_state.usuario_logado = True
                                st.session_state.user_id = user['id']
                                st.session_state.user_nome = user['nome']
                                st.session_state.nivel = user['nivel']
                                st.session_state.foto_perfil = user.get('foto_perfil', None)
                                st.rerun()
                            else:
                                st.error("❌ E-mail ou Senha incorretos!")
                        except Exception as e:
                            st.error(f"Erro ao conectar ao banco: {e}")

def render_meu_perfil():
    """Tela para o utilizador alterar os seus dados e foto de perfil"""
    st.title("👤 Meu Perfil")
    st.markdown("Atualize as suas informações e a sua foto de apresentação.")
    st.divider()
    
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Foto de Perfil")
        if st.session_state.get('foto_perfil'):
            st.markdown(f'<img src="{st.session_state.foto_perfil}" style="width: 150px; height: 150px; border-radius: 50%; object-fit: cover; border: 3px solid #ff4b4b; display: block; margin: 0 auto;">', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size: 80px; text-align: center;">👤</div>', unsafe_allow_html=True)
            
        st.write("")
        nova_foto = st.file_uploader("Carregar Nova Foto (JPG/PNG)", type=["png", "jpg", "jpeg"])
        if nova_foto is not None:
            if st.button("💾 Guardar Foto", type="primary", use_container_width=True):
                bytes_data = nova_foto.getvalue()
                b64_str = base64.b64encode(bytes_data).decode()
                mime_type = nova_foto.type
                foto_formatada = f"data:{mime_type};base64,{b64_str}"
                
                try:
                    supabase.table("usuarios").update({"foto_perfil": foto_formatada}).eq("id", st.session_state.user_id).execute()
                    st.session_state.foto_perfil = foto_formatada
                    st.success("Foto atualizada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar a foto: {e}")

    with c2:
        st.subheader("Dados de Acesso")
        with st.container(border=True):
            novo_nome = st.text_input("Seu Nome:", value=st.session_state.user_nome)
            nova_senha = st.text_input("Nova Senha (deixe em branco para não alterar):", type="password")
            
            st.write("")
            if st.button("Atualizar Dados de Acesso", use_container_width=True):
                payload = {"nome": novo_nome}
                if nova_senha.strip():
                    payload["senha"] = nova_senha.strip()
                    
                try:
                    supabase.table("usuarios").update(payload).eq("id", st.session_state.user_id).execute()
                    st.session_state.user_nome = novo_nome
                    st.success("Dados atualizados com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar dados: {e}")

def render_gestao_usuarios():
    """Tela exclusiva para o Admin criar novos acessos"""
    st.title("👥 Gestão de Equipa")
    st.markdown("Crie ou remova acessos ao sistema para os seus colaboradores.")
    st.divider()

    with st.expander("➕ Adicionar Novo Utilizador", expanded=False):
        with st.form("form_novo_user"):
            c1, c2 = st.columns(2)
            nome_u = c1.text_input("Nome Completo:")
            email_u = c2.text_input("E-mail de Acesso:", placeholder="ex: joao@grupoacelerador.com.br")
            
            c3, c4 = st.columns(2)
            senha_u = c3.text_input("Senha Inicial:", type="password")
            nivel_u = c4.selectbox("Perfil de Acesso:", ["Comercial (SDR/Closer)", "Financeiro (Backoffice)", "Admin"])
            
            st.write("")
            submit_user = st.form_submit_button("Criar Utilizador", type="primary")
            
            if submit_user:
                if not nome_u or not email_u or not senha_u:
                    st.error("Preencha todos os campos obrigatórios.")
                else:
                    try:
                        supabase.table("usuarios").insert({
                            "nome": nome_u.strip(),
                            "email": email_u.strip().lower(),
                            "senha": senha_u.strip(),
                            "nivel": nivel_u
                        }).execute()
                        st.success(f"Utilizador {nome_u} criado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao criar utilizador. Detalhe: {e}")

    st.subheader("Equipa Cadastrada")
    try:
        res = supabase.table("usuarios").select("id, nome, email, nivel").order("nome").execute()
        if res.data:
            df_users = pd.DataFrame(res.data)
            st.dataframe(df_users, hide_index=True, use_container_width=True)
    except Exception as e:
        st.error("Erro ao listar utilizadores.")

def main():
    if 'usuario_logado' not in st.session_state:
        st.session_state.usuario_logado = False

    if 'tela_atual' not in st.session_state:
        st.session_state.tela_atual = "📊 Dashboard"

    if not st.session_state.usuario_logado:
        render_login()
        st.stop()

    nivel = st.session_state.nivel
    nome = st.session_state.user_nome
    foto = st.session_state.get('foto_perfil', None)

    with st.sidebar:
        st.markdown("<h2 style='color:#ff4b4b; text-align:center;'>🔗 Acelera Hub</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if foto:
            st.markdown(f'<img src="{foto}" style="width: 90px; height: 90px; border-radius: 50%; object-fit: cover; display: block; margin: 0 auto; border: 2px solid #e2e8f0;">', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size: 55px; text-align: center; margin-bottom: 0px;">👤</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div style='text-align:center; padding-bottom: 10px; border-bottom: 1px solid #e6e6e6; margin-bottom: 15px; margin-top: 10px;'>
            <b>{nome}</b><br>
            <span style='color: #64748b; font-size: 12px;'>{nivel}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📌 Menu Principal")
        
        if st.button("📊 Dashboard", use_container_width=True, type="primary" if st.session_state.tela_atual == "📊 Dashboard" else "secondary"):
            st.session_state.tela_atual = "📊 Dashboard"
            st.rerun()

        if nivel in ["Comercial (SDR/Closer)", "Admin"]:
            if st.button("💼 Fluxo Comercial", use_container_width=True, type="primary" if st.session_state.tela_atual == "💼 Fluxo Comercial" else "secondary"):
                st.session_state.tela_atual = "💼 Fluxo Comercial"
                st.rerun()

        # NOVO BOTÃO: Mapa de Mesas (Visível para Comercial e Admin)
        if nivel in ["Comercial (SDR/Closer)", "Admin"]:
            if st.button("🍽️ Mapa de Mesas", use_container_width=True, type="primary" if st.session_state.tela_atual == "🍽️ Mapa de Mesas" else "secondary"):
                st.session_state.tela_atual = "🍽️ Mapa de Mesas"
                st.rerun()
                
        if nivel in ["Financeiro (Backoffice)", "Admin"]:
            if st.button("💰 Financeiro", use_container_width=True, type="primary" if st.session_state.tela_atual == "💰 Financeiro" else "secondary"):
                st.session_state.tela_atual = "💰 Financeiro"
                st.rerun()

        if nivel == "Admin":
            if st.button("🛡️ Auditoria (Logs)", use_container_width=True, type="primary" if st.session_state.tela_atual == "🛡️ Auditoria (Logs)" else "secondary"):
                st.session_state.tela_atual = "🛡️ Auditoria (Logs)"
                st.rerun()
            
            if st.button("👥 Gestão de Equipa", use_container_width=True, type="primary" if st.session_state.tela_atual == "👥 Gestão de Equipa" else "secondary"):
                st.session_state.tela_atual = "👥 Gestão de Equipa"
                st.rerun()

        st.divider()
        
        if st.button("⚙️ Meu Perfil", use_container_width=True, type="primary" if st.session_state.tela_atual == "⚙️ Meu Perfil" else "secondary"):
            st.session_state.tela_atual = "⚙️ Meu Perfil"
            st.rerun()
            
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    escolha = st.session_state.tela_atual
    
    if escolha == "📊 Dashboard":
        render_dashboard()
    elif escolha == "💼 Fluxo Comercial":
        render_tela_comercial()
    elif escolha == "🍽️ Mapa de Mesas":
        render_mapa_mesas()
    elif escolha == "💰 Financeiro":
        render_tela_financeira()
    elif escolha == "🛡️ Auditoria (Logs)":
        render_tela_auditoria()
    elif escolha == "👥 Gestão de Equipa":
        render_gestao_usuarios()
    elif escolha == "⚙️ Meu Perfil":
        render_meu_perfil()

if __name__ == "__main__":
    main()