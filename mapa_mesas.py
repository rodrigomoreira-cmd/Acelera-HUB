import streamlit as st
import pandas as pd
from database import supabase

def render_mapa_mesas():
    # Estilos CSS Dark Mode Refinados para o Acelera Hub
    st.markdown("""
<style>
/* Reset de margens superiores */
.main .block-container { 
    padding-top: 1.5rem !important; 
}

/* Estilo dos Cards Dark */
.mesa-card-dark {
    background-color: #0f172a; /* Slate 900 */
    border: 1px solid #334155;
    border-radius: 16px;
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
    height: 320px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
    transition: transform 0.2s ease;
}

.mesa-card-dark:hover {
    border-color: #475569;
}

.mesa-header-dark {
    padding: 15px;
    text-align: center;
    background-color: #1e293b; /* Slate 800 */
    border-bottom: 1px solid #334155;
    border-radius: 16px 16px 0 0;
    flex-shrink: 0;
}

.mesa-number {
    font-size: 32px;
    font-weight: 900;
    color: #ffffff;
    line-height: 1;
}

.mesa-status-label {
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    color: #94a3b8;
    letter-spacing: 2px;
    margin-bottom: 4px;
}

.mesa-body-dark {
    padding: 12px;
    flex-grow: 1;
    overflow-y: auto;
    background-color: #0f172a;
    scrollbar-width: thin;
    scrollbar-color: #475569 #0f172a;
}

/* Scrollbar Customizado Premium */
.mesa-body-dark::-webkit-scrollbar { width: 5px; }
.mesa-body-dark::-webkit-scrollbar-track { background: #0f172a; }
.mesa-body-dark::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
.mesa-body-dark::-webkit-scrollbar-thumb:hover { background: #475569; }

.participante-tag-dark {
    background: #1e293b;
    padding: 8px 12px;
    border-radius: 8px;
    margin-bottom: 8px;
    border-left: 5px solid #ff4b4b;
    color: #f8fafc;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.p-nome { 
    font-size: 11px; 
    font-weight: 800; 
    text-transform: uppercase; 
    color: #ffffff;
    white-space: normal; 
    word-wrap: break-word;
    line-height: 1.2;
    margin-bottom: 2px;
}
.p-empresa { 
    font-size: 10px; 
    color: #94a3b8; 
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Novo Estilo para o Entrevistador */
.p-entrevistador {
    font-size: 9px;
    color: #38bdf8; /* Azul claro para destacar */
    font-weight: 600;
    margin-top: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Indicadores de assento mais visíveis */
.dots-container {
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 10px;
    max-width: 140px;
    margin-left: auto;
    margin-right: auto;
}
.dot-seat { width: 7px; height: 7px; border-radius: 50%; background: #334155; }
.dot-occupied { background: #ff4b4b; box-shadow: 0 0 5px #ff4b4b; }

/* Estilo do Painel de Controle */
.stSelectbox label, .stNumberInput label {
    color: #1e293b !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

    st.title("🍽️ Gestão de Mesas")
    
    # 1. Buscar Dados (agora incluindo os entrevistadores)
    try:
        res = supabase.table("vendas_contratos").select(
            "id, nome_cliente, nome_empresa, status_geral, numero_mesa, status_entrevista_almoco, status_entrevista_jantar, entrevistadores_almoco, entrevistadores_jantar"
        ).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return

    if df.empty:
        st.info("Nenhum dado disponível no sistema.")
        return

    # Função para limpar e normalizar o número da mesa
    def clean_mesa_val(val):
        if pd.isna(val) or str(val).strip().lower() in ['none', 'nan', '']:
            return None
        try:
            return str(int(float(str(val).strip())))
        except:
            return str(val).strip()

    df['numero_mesa'] = df['numero_mesa'].apply(clean_mesa_val)

    # REGRAS DE FILTRO PARA O MAPA VISUAL:
    # Mostramos os participantes que não foram descartados/perdidos E que não têm Contrato Assinado.
    # Assim, quando assinam, libertam a mesa automaticamente.
    df_mapa = df[~df['status_geral'].isin(['Descartado', 'Perdido', 'Contrato Assinado'])].copy()

    # LÓGICA DE ALOCAÇÃO (LISTA DE SELEÇÃO):
    df_refeicao = df[
        (~df['status_geral'].isin(['Descartado', 'Perdido', 'Contrato Assinado'])) &
        (
            ((df['status_entrevista_almoco'].notna()) & (df['status_entrevista_almoco'] != 'Não se aplica')) |
            ((df['status_entrevista_jantar'].notna()) & (df['status_entrevista_jantar'] != 'Não se aplica')) |
            (df['numero_mesa'].notna()) # Se já tiver mesa e não estiver assinado, continua na lista
        )
    ].copy()

    # Criar label com as tags de refeição para o selectbox
    def get_meal_tag(row):
        tags = []
        is_lunch = pd.notna(row['status_entrevista_almoco']) and row['status_entrevista_almoco'] != 'Não se aplica'
        is_dinner = pd.notna(row['status_entrevista_jantar']) and row['status_entrevista_jantar'] != 'Não se aplica'
        
        if is_lunch: 
            status_icone = "✅" if row['status_entrevista_almoco'] == 'Realizada' else ("⏳" if row['status_entrevista_almoco'] == 'Aguardando' else "❌")
            tags.append(f"🍽️ ALM {status_icone}")
        if is_dinner: 
            status_icone = "✅" if row['status_entrevista_jantar'] == 'Realizada' else ("⏳" if row['status_entrevista_jantar'] == 'Aguardando' else "❌")
            tags.append(f"🍷 JAN {status_icone}")
        
        tag_str = " | ".join(tags)
        mesa_info = f" -> (Mesa {row['numero_mesa']})" if pd.notna(row['numero_mesa']) else ""
        
        return f"{row['nome_cliente']} [{tag_str}]{mesa_info}" if tags else f"{row['nome_cliente']}{mesa_info}"

    if not df_refeicao.empty:
        df_refeicao['label_display'] = df_refeicao.apply(get_meal_tag, axis=1)
    
    # --- PAINEL DE CONTROLE (ALOCAÇÃO DIRETA) ---
    with st.container(border=True):
        st.markdown("### 🎯 Painel de Alocação")
        
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c1:
            total_mesas = st.number_input("Total de Mesas:", min_value=1, value=14, help="Padrão do sistema: 14 mesas")
        with c2:
            cadeiras_por_mesa = st.number_input("Cadeiras por Mesa:", min_value=1, value=10)
        
        st.divider()
        
        ca1, ca2 = st.columns([2, 1])
        
        with ca1:
            if not df_refeicao.empty:
                opcoes_display = ["Selecione um participante..."] + sorted(df_refeicao['label_display'].tolist())
                selecao_display = st.selectbox("1. Escolha o Participante (Com Refeição):", opcoes_display)
            else:
                st.warning("⚠️ Nenhum participante elegível para refeição encontrado.")
                selecao_display = "Selecione um participante..."
        
        with ca2:
            if selecao_display != "Selecione um participante...":
                row_cliente = df_refeicao[df_refeicao['label_display'] == selecao_display].iloc[0]
                
                opcoes_mesas = ["Sem Mesa"] + [str(i) for i in range(1, total_mesas + 1)]
                mesa_atual = str(row_cliente['numero_mesa']) if row_cliente['numero_mesa'] else "Sem Mesa"
                
                try:
                    idx_default = opcoes_mesas.index(mesa_atual)
                except:
                    idx_default = 0
                
                nova_mesa = st.selectbox("2. Definir Mesa:", opcoes_mesas, index=idx_default)
                
                if nova_mesa != mesa_atual:
                    val_db = None if nova_mesa == "Sem Mesa" else str(nova_mesa)
                    try:
                        supabase.table("vendas_contratos").update({"numero_mesa": val_db}).eq("id", row_cliente['id']).execute()
                        st.toast(f"✅ {row_cliente['nome_cliente']} movido para a Mesa {nova_mesa}", icon="🎉")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
            else:
                st.selectbox("2. Definir Mesa:", ["Aguardando seleção..."], disabled=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🗺️ Mapa do Salão (4 mesas por linha)")
    
    # --- GRID DE MESAS DARK ---
    cols_per_row = 4
    map_cols = st.columns(cols_per_row)
    
    for m in range(1, total_mesas + 1):
        with map_cols[(m-1) % cols_per_row]:
            target_mesa = str(m)
            p_na_mesa = df_mapa[df_mapa['numero_mesa'] == target_mesa] if not df_mapa.empty else pd.DataFrame()
            qtd = len(p_na_mesa)
            
            if qtd == 0:
                cor_indicador, status_msg = "#64748b", "MESA LIVRE"
            elif qtd < cadeiras_por_mesa:
                cor_indicador, status_msg = "#10b981", f"{cadeiras_por_mesa - qtd} VAGAS"
            else:
                cor_indicador, status_msg = "#ff4b4b", "LOTADA"
            
            lista_html = ""
            if not p_na_mesa.empty:
                for _, p in p_na_mesa.iterrows():
                    refeicao_info = ""
                    
                    # Identificador visual das refeições
                    if pd.notna(p['status_entrevista_almoco']) and p['status_entrevista_almoco'] != 'Não se aplica': 
                        icone = "✅" if p['status_entrevista_almoco'] == 'Realizada' else "⏳"
                        refeicao_info += f" 🍽️{icone}"
                        
                    if pd.notna(p['status_entrevista_jantar']) and p['status_entrevista_jantar'] != 'Não se aplica': 
                        icone = "✅" if p['status_entrevista_jantar'] == 'Realizada' else "⏳"
                        refeicao_info += f" 🍷{icone}"
                    
                    # Identificação do Especialista/Entrevistador
                    entrevistadores = []
                    if pd.notna(p.get('entrevistadores_almoco')) and str(p.get('entrevistadores_almoco')).strip():
                        entrevistadores.append(str(p['entrevistadores_almoco']).strip())
                    if pd.notna(p.get('entrevistadores_jantar')) and str(p.get('entrevistadores_jantar')).strip():
                        if str(p['entrevistadores_jantar']).strip() not in entrevistadores:
                            entrevistadores.append(str(p['entrevistadores_jantar']).strip())
                            
                    ent_str = " / ".join(entrevistadores)
                    div_entrevistador = f'<div class="p-entrevistador">👤 {ent_str}</div>' if ent_str else ''

                    lista_html += f'<div class="participante-tag-dark"><div class="p-nome">{str(p["nome_cliente"])}{refeicao_info}</div><div class="p-empresa">🏢 {str(p["nome_empresa"])}</div>{div_entrevistador}</div>'
            else:
                lista_html = '<div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; opacity: 0.3;"><div style="font-size: 30px;">🍽️</div><div style="font-size: 10px; margin-top: 5px; font-weight: 700;">DISPONÍVEL</div></div>'

            dots_html = "".join([f'<div class="dot-seat {"dot-occupied" if i < qtd else ""}"></div>' for i in range(cadeiras_por_mesa)])

            card_html = f"""<div class="mesa-card-dark"><div class="mesa-header-dark"><div class="mesa-status-label">Mesa</div><div class="mesa-number">{m}</div><div style="font-size: 10px; font-weight: 900; color: {cor_indicador}; margin-top: 6px; letter-spacing: 1px;">{status_msg}</div><div class="dots-container">{dots_html}</div></div><div class="mesa-body-dark">{lista_html}</div></div>"""
            
            st.markdown(card_html, unsafe_allow_html=True)

if __name__ == "__main__":
    render_mapa_mesas()