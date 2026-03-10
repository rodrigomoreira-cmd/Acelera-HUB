import streamlit as st
import pandas as pd
from database import supabase
from streamlit_autorefresh import st_autorefresh
import re

def formata_brl(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def limpa_valor_para_float(valor):
    """
    Remove R$, pontos de milhar, parênteses e converte vírgula em ponto.
    Ex: 'R$ 19.600,00 (70.0%)' -> 19600.0
    """
    if valor is None or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    
    texto = str(valor)
    # 1. Remove tudo o que estiver dentro de parênteses (como a porcentagem)
    texto = re.sub(r'\(.*?\)', '', texto)
    # 2. Remove 'R$', espaços e pontos (separador de milhar no padrão BR)
    texto = texto.replace('R$', '').replace(' ', '').replace('.', '')
    # 3. Troca a vírgula por ponto (separador decimal padrão Python)
    texto = texto.replace(',', '.')
    
    try:
        return float(texto)
    except ValueError:
        return 0.0

def render_tela_financeira():
    # --- A MÁGICA ---
    # Só este ecrã do Financeiro vai recarregar automaticamente a cada 5 segundos (5000 ms).
    # O ecrã do Comercial não é afetado e o SDR pode digitar em paz!
    st_autorefresh(interval=5000, key="refresh_financeiro")

    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.title("💰 Aprovação Financeira")
        st.markdown("Analise o crédito, notas fiscais e liberação de cashbacks dos clientes pendentes.")
    with col_h2:
        st.write("")
        if st.button("🔄 Forçar Atualização", use_container_width=True):
            st.rerun()

    st.divider()

    # 1. Buscar leads que estão aguardando o Financeiro
    try:
        res = supabase.table("vendas_contratos").select("*").eq("status_geral", "Aguardando Financeiro").execute()
        dados = res.data if res.data else []
    except Exception as e:
        st.error(f"Erro ao ligar à base de dados: {e}")
        dados = []

    if not dados:
        st.success("🎉 Excelente! Não há nenhum contrato pendente de aprovação financeira no momento.")
        return

    st.subheader(f"Pendentes de Análise ({len(dados)})")
    
    for row in dados:
        with st.container(border=True):
            # Layout em 4 colunas para organizar todos os campos
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            
            # Limpeza de valores para cálculos
            v_contrato = limpa_valor_para_float(row.get('valor_contrato', 0))
            v_vagas = limpa_valor_para_float(row.get('valor_vagas_adicionais', 0))
            v_entrada = limpa_valor_para_float(row.get('valor_entrada', 0))
            faturamento_total = v_contrato + v_vagas

            with c1:
                st.markdown(f"**{row.get('nome_cliente', 'N/A')}**")
                st.markdown(f"<span style='font-size:12px; color:gray;'>🏢 {row.get('nome_empresa', 'N/A')}</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-size:12px; color:gray;'>📄 CNPJ/CPF: {row.get('cnpj', 'N/A')}</span>", unsafe_allow_html=True)

            with c2:
                st.markdown(f"<span style='font-size:13px;'>💼 **Valor Investido:** {formata_brl(faturamento_total)}</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-size:13px;'>💵 **Entrada:** {formata_brl(v_entrada)}</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-size:12px; color:#005088;'>Vendedor: {row.get('sdr_especialista_caixa', 'N/A')}</span>", unsafe_allow_html=True)

            with c3:
                # Proteção contra valores nulos para os índices dos selectboxes
                lista_credito = ["Pendente", "Liberado", "Bloqueado"]
                cred_val = row.get('analise_credito')
                if cred_val not in lista_credito: cred_val = "Pendente"

                lista_serasa = ["Em Análise", "Nada Consta", "Com Restrição"]
                ser_val = row.get('status_serasa')
                if ser_val not in lista_serasa: ser_val = "Em Análise"

                novo_credito = st.selectbox(
                    "Decisão de Crédito:", 
                    lista_credito, 
                    index=lista_credito.index(cred_val),
                    key=f"cred_{row['id']}"
                )
                novo_serasa = st.selectbox(
                    "Status Serasa:", 
                    lista_serasa, 
                    index=lista_serasa.index(ser_val),
                    key=f"serasa_{row['id']}"
                )

            with c4:
                # Lógica de Cálculo de Cashback
                cashback_atual_valor = limpa_valor_para_float(row.get('investimento_cashback', 0.0))
                
                # Tenta extrair o percentual da string original caso exista algo como "(70.0%)"
                percentual_sugerido = 0.0
                texto_raw = str(row.get('investimento_cashback', ""))
                match_perc = re.search(r'(\d+\.?\d*)%', texto_raw)
                if match_perc:
                    percentual_sugerido = float(match_perc.group(1))
                elif faturamento_total > 0:
                    percentual_sugerido = (cashback_atual_valor / faturamento_total) * 100

                col_p, col_v = st.columns(2)
                with col_p:
                    novo_percentual = st.number_input(
                        "% Cashback:", 
                        min_value=0.0, 
                        max_value=100.0, 
                        value=float(percentual_sugerido),
                        step=0.1,
                        key=f"perc_{row['id']}"
                    )
                
                # Cálculo automático baseado no percentual
                valor_calculado = faturamento_total * (novo_percentual / 100)
                
                with col_v:
                    novo_cashback = st.number_input(
                        "Valor Cashback:", 
                        min_value=0.0, 
                        format="%.2f", 
                        value=float(valor_calculado), 
                        key=f"cash_{row['id']}"
                    )
                
                lista_nf = ["Pendente", "Emitida", "Não se aplica"]
                nf_val = row.get('status_nf')
                if nf_val not in lista_nf: nf_val = "Pendente"

                novo_status_nf = st.selectbox(
                    "Status NF:", 
                    lista_nf, 
                    index=lista_nf.index(nf_val),
                    key=f"nf_{row['id']}"
                )

            # Rodapé do Card com Avisos e Botão de Salvar
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            col_aviso, col_btn = st.columns([3, 1])
            
            with col_aviso:
                if novo_credito == "Liberado" and novo_serasa == "Nada Consta":
                    st.info(f"✅ Crédito aprovado! Liberação de **{formata_brl(novo_cashback)}** ({novo_percentual:.1f}%) confirmada.")
                elif novo_credito == "Bloqueado" or novo_serasa == "Com Restrição":
                    st.warning("❌ Crédito recusado. O status será atualizado para o Comercial.")

            with col_btn:
                if st.button("💾 Guardar Análise", type="primary", use_container_width=True, key=f"btn_salvar_{row['id']}"):
                    # Guardamos o valor limpo mas podemos formatar a string se desejar manter o padrão visual no banco
                    # Aqui salvamos o valor numérico para o campo 'investimento_cashback'
                    # Se o seu banco espera string com o formato "R$ X (Y%)", descomente a linha abaixo:
                    # valor_para_banco = f"{formata_brl(novo_cashback)} ({novo_percentual:.1f}%)"
                    
                    try:
                        supabase.table("vendas_contratos").update({
                            "analise_credito": novo_credito,
                            "status_serasa": novo_serasa,
                            "investimento_cashback": novo_cashback, # Alterado para salvar apenas o float para evitar erros de conversão futuros
                            "status_nf": novo_status_nf
                        }).eq("id", row['id']).execute()
                        
                        st.success(f"Análise de {row['nome_cliente']} atualizada!")
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Erro ao guardar: {e}")