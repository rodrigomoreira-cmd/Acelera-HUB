import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import supabase
from datetime import datetime, timedelta

def formata_brl(valor):
    """Função auxiliar para formatar valores no padrão brasileiro R$ 1.000,00"""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def render_dashboard():
    st.title("📊 Indicadores de Performance - Acelera Hub")
    
    try:
        res = supabase.table("vendas_contratos").select("*").execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    if df.empty:
        st.info("Aguardando dados para gerar os indicadores.")
        return

    # Garante que a coluna produto existe antes da verificação
    if 'produto' not in df.columns:
        df['produto'] = 'AE'
        
    for col in ['sdr_especialista_caixa', 'resp_aplicacao', 'nome_evento']:
        if col not in df.columns:
            df[col] = 'Não informado'

    df['criado_em'] = pd.to_datetime(df['criado_em'], errors='coerce').dt.tz_localize(None)
    hoje = pd.Timestamp.utcnow().tz_localize(None)

    st.sidebar.header("🔍 Filtros")
    eventos = sorted([str(e) for e in df['nome_evento'].unique() if pd.notna(e) and str(e).strip() != ''])
    evento_selecionado = st.sidebar.selectbox("🎟️ Evento:", ["Geral"] + eventos)
    opcoes_periodo = ["Todo o Período", "Últimos 7 Dias", "Últimos 30 Dias", "Este Mês", "Este Ano"]
    periodo_selecionado = st.sidebar.selectbox("📅 Período de Registo:", opcoes_periodo)

    df_filtrado = df.copy()
    
    if evento_selecionado != "Geral":
        df_filtrado = df_filtrado[df_filtrado['nome_evento'] == evento_selecionado]

    if periodo_selecionado == "Últimos 7 Dias":
        df_filtrado = df_filtrado[df_filtrado['criado_em'] >= (hoje - timedelta(days=7))]
    elif periodo_selecionado == "Últimos 30 Dias":
        df_filtrado = df_filtrado[df_filtrado['criado_em'] >= (hoje - timedelta(days=30))]
    elif periodo_selecionado == "Este Mês":
        df_filtrado = df_filtrado[(df_filtrado['criado_em'].dt.month == hoje.month) & (df_filtrado['criado_em'].dt.year == hoje.year)]
    elif periodo_selecionado == "Este Ano":
        df_filtrado = df_filtrado[df_filtrado['criado_em'].dt.year == hoje.year]

    if df_filtrado.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    total_aplicacoes = len(df_filtrado)
    qtd_empresas = df_filtrado['nome_empresa'].nunique()
    qtd_membros = len(df_filtrado) + int(pd.to_numeric(df_filtrado.get('qtd_socios', 0), errors='coerce').fillna(0).sum())
    
    empresas_com_socio = len(df_filtrado[pd.to_numeric(df_filtrado.get('qtd_socios', 0), errors='coerce') > 0])
    if empresas_com_socio == 0:
        contagem_empresas = df_filtrado['nome_empresa'].value_counts()
        empresas_com_socio = len(contagem_empresas[contagem_empresas > 1])

    df_filtrado['valor_entrada'] = pd.to_numeric(df_filtrado['valor_entrada'], errors='coerce').fillna(0)
    df_filtrado['valor_contrato'] = pd.to_numeric(df_filtrado['valor_contrato'], errors='coerce').fillna(0)
    df_filtrado['valor_vagas_adicionais'] = pd.to_numeric(df_filtrado.get('valor_vagas_adicionais', 0), errors='coerce').fillna(0)
    
    df_filtrado['faturamento_linha'] = df_filtrado['valor_contrato'] + df_filtrado['valor_vagas_adicionais']

    total_primeira_parcela = df_filtrado['valor_entrada'].sum()
    df_assinados = df_filtrado[df_filtrado['status_geral'] == 'Contrato Assinado']
    faturamento_total = df_assinados['faturamento_linha'].sum()

    fechados = len(df_assinados)
    percentual_conversao = (fechados / total_aplicacoes * 100) if total_aplicacoes > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏢 Qtd. Empresas", qtd_empresas)
    c2.metric("👥 Qtd. Membros", qtd_membros)
    c3.metric("🤝 Empresas c/ Sócio", empresas_com_socio)
    c4.metric("📅 Filtrado por", periodo_selecionado)

    st.divider()
    f1, f2, f3 = st.columns(3)
    f1.metric("💰 Faturamento Global", formata_brl(faturamento_total), help="Soma do valor total (Principal + Vagas Extras) dos Contratos Assinados")
    f2.metric("💳 Valor total entrada", formata_brl(total_primeira_parcela), help="Soma de todos os valores de entrada recebidos")
    f3.metric("📈 Conversão (Vendas)", f"{percentual_conversao:.1f}%", f"{fechados} Fechados")

    st.markdown("### 📦 Desempenho por Produto (Apenas Assinados)")
    p1, p2 = st.columns(2)
    
    df_ae = df_assinados[df_assinados['produto'] == 'AE']
    fat_ae = df_ae['faturamento_linha'].sum()
    
    df_giants = df_assinados[df_assinados['produto'] == 'Giants']
    fat_giants = df_giants['faturamento_linha'].sum()

    with p1:
        with st.container(border=True):
            st.markdown("<h4 style='color: #005088; margin-bottom: 0px;'>Acelerador Empresarial (AE)</h4>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='color: #11caa0; margin-top: 0px;'>{formata_brl(fat_ae)}</h2>", unsafe_allow_html=True)
            st.markdown(f"**Total:** {len(df_ae)} venda(s)")

    with p2:
        with st.container(border=True):
            st.markdown("<h4 style='color: #6b21a8; margin-bottom: 0px;'>Giants</h4>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='color: #11caa0; margin-top: 0px;'>{formata_brl(fat_giants)}</h2>", unsafe_allow_html=True)
            st.markdown(f"**Total:** {len(df_giants)} venda(s)")

    st.divider()
    col_grafico1, col_grafico2, col_grafico3 = st.columns([2, 1, 1])
    
    with col_grafico1:
        st.subheader("📊 Etapas do Funil")
        
        fases_exibicao = ["Novo Lead", "Em Negociação", "Aguardando Financeiro", "Contrato Assinado", "Perdido"]
        contagens = [df_filtrado[df_filtrado['status_geral'] == fase].shape[0] for fase in fases_exibicao]
        
        if sum(contagens) > 0:
            max_contagem = max(contagens)
            folga_topo = max_contagem + max(1, max_contagem * 0.15)

            fig = go.Figure(data=[go.Bar(
                x=fases_exibicao,
                y=contagens,
                text=contagens,
                textposition='auto',
                marker_color=["#3b82f6", "#f59e0b", "#8b5cf6", "#10b981", "#ef4444"] 
            )])
            
            fig.update_layout(
                margin=dict(l=10, r=10, t=40, b=20), 
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                yaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(200, 200, 200, 0.2)',
                    range=[0, folga_topo] 
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado para gerar o gráfico neste período.")
        
    with col_grafico2:
        st.subheader("🎯 Top 3 Captação")
        if not df_assinados.empty:
            ranking_cap = df_assinados['resp_aplicacao'].value_counts().head(3).reset_index()
            ranking_cap.columns = ['Responsável', 'Vendas']
            medalhas = ["🥇", "🥈", "🥉"]
            for i, row in ranking_cap.iterrows():
                with st.container(border=True):
                    medalha = medalhas[i] if i < len(medalhas) else ""
                    st.markdown(f"<h5 style='margin-bottom: 5px; color: #005088;'>{medalha} {row['Responsável']}</h5>", unsafe_allow_html=True)
                    st.markdown(f"<span style='font-size: 16px; color: #11caa0; font-weight: bold;'>{row['Vendas']} captação(ões)</span>", unsafe_allow_html=True)
        else:
            st.info("Nenhuma venda.")

    with col_grafico3:
        st.subheader("🤝 Top 3 Closers")
        if not df_assinados.empty:
            ranking_closer = df_assinados.groupby('sdr_especialista_caixa')['faturamento_linha'].sum().reset_index()
            ranking_closer = ranking_closer.sort_values(by='faturamento_linha', ascending=False).head(3).reset_index(drop=True)
            ranking_closer.columns = ['Responsável', 'Faturamento']
            
            medalhas = ["🥇", "🥈", "🥉"]
            for i, row in ranking_closer.iterrows():
                with st.container(border=True):
                    medalha = medalhas[i] if i < len(medalhas) else ""
                    st.markdown(f"<h5 style='margin-bottom: 5px; color: #005088;'>{medalha} {row['Responsável']}</h5>", unsafe_allow_html=True)
                    st.markdown(f"<span style='font-size: 16px; color: #11caa0; font-weight: bold;'>{formata_brl(row['Faturamento'])}</span>", unsafe_allow_html=True)
        else:
            st.info("Nenhuma venda.")

    st.divider()
    c_titulo, c_botao = st.columns([3, 1])
    with c_titulo:
        st.subheader("🎓 Alunos que Fecharam (Contratos Assinados)")
    
    colunas_fechados = ["nome_cliente", "nome_empresa", "produto", "faturamento_linha", "valor_entrada", "status_pagamento_giants", "resp_aplicacao", "sdr_especialista_caixa"]
    colunas_existentes = [c for c in colunas_fechados if c in df_assinados.columns]
    
    df_fechados = df_assinados[colunas_existentes]
    
    if not df_fechados.empty:
        with c_botao:
            csv = df_fechados.to_csv(index=False).encode('utf-8')
            nome_arq = f"alunos_fechados_{periodo_selecionado.replace(' ', '_')}.csv"
            st.download_button(label="📥 Exportar Fechados", data=csv, file_name=nome_arq, mime='text/csv', use_container_width=True)

        st.dataframe(
            df_fechados,
            column_config={
                "nome_cliente": "Nome do Aluno",
                "nome_empresa": "Empresa",
                "produto": "Produto",
                "faturamento_linha": st.column_config.NumberColumn("Faturamento Total", format="R$ %.2f"),
                "valor_entrada": st.column_config.NumberColumn("Valor Entrada", format="R$ %.2f"),
                "status_pagamento_giants": "Status Giants",
                "resp_aplicacao": "Captador (SDR)",
                "sdr_especialista_caixa": "Closer (Vendedor)"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.warning("Nenhum contrato assinado neste período/evento.")