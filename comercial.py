import streamlit as st
import pandas as pd
from database import supabase
from datetime import datetime
import re 

def formata_brl(valor):
    """Função auxiliar para formatar valores no padrão brasileiro R$ 1.000,00"""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def render_tela_comercial():
    col_header1, col_header2 = st.columns([4, 1])
    with col_header1:
        st.title("💼 Fluxo de Vendas & Aplicação")
    with col_header2:
        st.write("") 
        st.write("")
        if st.button("🔄 Atualizar Dados", use_container_width=True, help="Clique para buscar as últimas aprovações do Financeiro"):
            st.rerun()

    st.markdown("Cadastre leads ou atualize fichas. Acompanhe o funil de vendas através da **Tabela** ou da **Vista Kanban** abaixo.")
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True) 

    usuario_logado = st.session_state.get('user_nome', 'Comercial')
    usuario_nivel = st.session_state.get('nivel', '')

    if "reset_comercial" not in st.session_state:
        st.session_state.reset_comercial = 0

    if "dados_importados" not in st.session_state:
        st.session_state.dados_importados = {}

    if "confirmar_limpeza" not in st.session_state:
        st.session_state.confirmar_limpeza = False

    if "aba_participantes" not in st.session_state:
        st.session_state.aba_participantes = "🔍 Buscar e Importar"

    try:
        res = supabase.table("vendas_contratos").select("*").order("criado_em", desc=True).execute()
        dados = res.data
        df_comercial = pd.DataFrame(dados) if dados else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de vendas: {e}")
        return

    hoje = pd.Timestamp.utcnow().tz_localize(None)
    if not df_comercial.empty:
        df_comercial['criado_em_dt'] = pd.to_datetime(df_comercial['criado_em'], errors='coerce').dt.tz_localize(None)
        df_comercial['dias_no_funil'] = (hoje - df_comercial['criado_em_dt']).dt.days

    try:
        res_part = supabase.table("base_participantes").select("*").execute()
        df_participantes = pd.DataFrame(res_part.data) if res_part.data else pd.DataFrame()
    except Exception as e:
        df_participantes = pd.DataFrame()

    if dados:
        aprovados = [d for d in dados if d.get('status_geral') == 'Aguardando Financeiro' and d.get('analise_credito') == 'Liberado' and d.get('status_serasa') == 'Nada Consta']
        recusados = [d for d in dados if d.get('status_geral') == 'Aguardando Financeiro' and (d.get('analise_credito') == 'Bloqueado' or d.get('status_serasa') in ['Com Restrição', 'Em Análise'])]
        
        if aprovados:
            st.success(f"🎉 **Boas notícias!** Tem **{len(aprovados)}** lead(s) com crédito aprovado.")
        if recusados:
            st.error(f"⚠️ **Atenção:** Tem **{len(recusados)}** lead(s) com crédito recusado.")

    # --- SECÇÃO: BASE DE PARTICIPANTES ---
    with st.expander("📂 Consultar / Gerenciar Base de Participantes", expanded=False):
        st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True) 
        
        idx_aba = 0 if st.session_state.aba_participantes == "🔍 Buscar e Importar" else 1
        aba_selecionada = st.radio("Selecione a ação:", ["🔍 Buscar e Importar", "⚙️ Gerenciar Upload / Limpar"], index=idx_aba, horizontal=True, label_visibility="collapsed")
        
        st.session_state.aba_participantes = aba_selecionada
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True) 
        
        if aba_selecionada == "🔍 Buscar e Importar":
            if not df_participantes.empty:
                eventos_cadastrados = df_participantes['nome_evento'].unique()
                st.markdown(f"**Eventos Carregados:** {', '.join(eventos_cadastrados)} &nbsp;|&nbsp; **Total na base:** {len(df_participantes)} contatos.")
                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True) 
                
                busca_ext = st.text_input("🔍 Pesquisar na Base (Nome, CPF ou E-mail):", key=f"busca_ext_{st.session_state.reset_comercial}")
                
                st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
                
                if busca_ext:
                    mask = df_participantes.astype(str).apply(lambda row: row.str.contains(busca_ext, case=False).any(), axis=1)
                    resultado = df_participantes[mask]
                    
                    if not resultado.empty:
                        st.write(f"Resultados encontrados ({len(resultado)}):")
                        for idx, row in resultado.head(5).iterrows():
                            with st.container(border=True):
                                c_res1, c_res2 = st.columns([3, 1])
                                nome_p = row.get('nome', 'N/A')
                                doc_p = row.get('documento', 'N/A')
                                emp_p = row.get('empresa', '')
                                ev_p = row.get('nome_evento', '')
                                
                                c_res1.markdown(f"**{nome_p}** (Evento: {ev_p})")
                                c_res1.markdown(f"<small>Doc: {doc_p} | Empresa: {emp_p}</small>", unsafe_allow_html=True)
                                
                                if c_res2.button("Importar Dados", key=f"btn_imp_{row.get('id', idx)}"):
                                    st.session_state.dados_importados = {
                                        "nome_evento": row.get('nome_evento', ''),
                                        "nome_cliente": row.get('nome', ''),
                                        "nome_empresa": row.get('empresa', ''),
                                        "telefone": row.get('telefone', ''),
                                        "email": row.get('email', ''),
                                        "cnpj": row.get('documento', '')
                                    }
                                    st.session_state.reset_comercial += 1
                                    st.success("Participante importado! O formulário foi limpo e preenchido.")
                                    st.rerun() 
                    else:
                        st.warning("Nenhum participante encontrado com esse termo.")
            else:
                st.info("A base está vazia. Vá à aba 'Gerenciar Upload / Limpar' para subir um ficheiro de evento.")

        elif aba_selecionada == "⚙️ Gerenciar Upload / Limpar":
            if usuario_nivel == "Admin":
                st.markdown("Suba um ficheiro para guardar permanentemente no banco. Ao final da ação, pode limpar tudo.")
                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
                
                nome_evento = st.text_input("Nome do Evento (ex: Imersão SP):")
                arquivo_base = st.file_uploader("Carregar Ficheiro (CSV ou Excel)", type=["csv", "xlsx"])
                
                st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                
                if st.button("📤 Salvar no Banco de Dados", type="primary", use_container_width=True):
                    if not nome_evento:
                        st.error("Por favor, preencha o Nome do Evento antes de salvar.")
                    elif not arquivo_base:
                        st.error("Por favor, selecione um ficheiro.")
                    else:
                        try:
                            df_up = pd.read_csv(arquivo_base) if arquivo_base.name.endswith('.csv') else pd.read_excel(arquivo_base)
                            registros = []
                            for _, row in df_up.iterrows():
                                empresa_final = ""
                                for col in ['Empresa', 'Nome da Empresa', 'Nome Fantasia']:
                                    if col in row and pd.notna(row[col]) and str(row[col]).strip() != "":
                                        empresa_final = str(row[col])
                                        break

                                doc_cru = str(row.get('CPF/CNPJ', row.get('CPF', ''))) if pd.notna(row.get('CPF/CNPJ', row.get('CPF'))) else ""
                                tel_cru = str(row.get('Telefone', '')) if pd.notna(row.get('Telefone')) else ""
                                
                                registros.append({
                                    "nome_evento": nome_evento,
                                    "nome": str(row.get('Participante', row.get('Nome', ''))) if pd.notna(row.get('Participante', row.get('Nome'))) else "",
                                    "empresa": empresa_final,
                                    "telefone": re.sub(r'\D', '', tel_cru),
                                    "email": str(row.get('E-mail', row.get('Email', ''))) if pd.notna(row.get('E-mail', row.get('Email'))) else "",
                                    "documento": re.sub(r'\D', '', doc_cru)
                                })
                                
                            supabase.table("base_participantes").insert(registros).execute()
                            st.session_state.reset_comercial += 1
                            st.session_state.aba_participantes = "🔍 Buscar e Importar"
                            st.success(f"✅ Sucesso! {len(registros)} contatos salvos no evento '{nome_evento}'.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar no banco: {e}")

                st.markdown("<div style='margin-top: 20px; margin-bottom: 20px;'><hr></div>", unsafe_allow_html=True)
                
                if not st.session_state.confirmar_limpeza:
                    if st.button("🗑️ Limpar Toda a Base de Participantes", type="secondary", use_container_width=True):
                        st.session_state.confirmar_limpeza = True
                        st.rerun()
                else:
                    st.warning("🚨 Tem certeza absoluta que deseja apagar todos os contatos da base? Esta ação não pode ser desfeita.")
                    col_conf_1, col_conf_2 = st.columns(2)
                    if col_conf_1.button("✅ Sim, apagar tudo", type="primary", use_container_width=True):
                        try:
                            supabase.table("base_participantes").delete().neq("id", 0).execute()
                            st.session_state.confirmar_limpeza = False
                            st.session_state.reset_comercial += 1
                            st.success("Base esvaziada com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao limpar banco: {e}")
                    if col_conf_2.button("❌ Cancelar", use_container_width=True):
                        st.session_state.confirmar_limpeza = False
                        st.rerun()
            else:
                st.warning("🔒 **Acesso Restrito:** Apenas utilizadores com o perfil de 'Admin' podem fazer upload ou limpar a base de participantes.")

    # --- FILTROS RÁPIDOS PARA O SELETOR ---
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    st.subheader("🎯 Triagem de Leads")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    f_ref = col_f1.selectbox("Refeição:", ["Todas", "Almoço", "Janta"], key="f_ref")
    f_status = col_f2.selectbox("Fase do Funil:", ["Todas", "Novo Lead", "Em Negociação", "Aguardando Financeiro", "Contrato Assinado", "Perdido"], key="f_status")
    f_cred = col_f3.selectbox("Situação Crédito:", ["Todos", "Liberado", "Bloqueado", "Pendente"], key="f_cred")

    # --- CONSTRUÇÃO DAS OPÇÕES COM FILTROS E TAGS ---
    opcoes = ["+ Novo Cadastro"]
    
    # Filtragem dos dados para o seletor
    dados_filtrados = dados if dados else []
    
    if f_ref == "Almoço":
        dados_filtrados = [d for d in dados_filtrados if d.get('status_entrevista_almoco') == 'Aguardando']
    elif f_ref == "Janta":
        dados_filtrados = [d for d in dados_filtrados if d.get('status_entrevista_jantar') == 'Aguardando']
        
    if f_status != "Todas":
        dados_filtrados = [d for d in dados_filtrados if d.get('status_geral') == f_status]
        
    if f_cred != "Todos":
        dados_filtrados = [d for d in dados_filtrados if d.get('analise_credito') == f_cred]

    for d in dados_filtrados:
        tags_list = []
        
        # Tag de Refeição com ícones
        if d.get('status_entrevista_almoco') == 'Aguardando':
            tags_list.append("🍽️ ALMOÇO")
        if d.get('status_entrevista_jantar') == 'Aguardando':
            tags_list.append("🍷 JANTA")
            
        # Tag de Análise / Status Geral com ícones
        status_geral = d.get('status_geral')
        if status_geral == 'Contrato Assinado':
            tags_list.append("📝 CONTRATO ASSINADO")
        elif status_geral == 'Aguardando Financeiro':
            credito = d.get('analise_credito')
            serasa = d.get('status_serasa')
            if credito == 'Liberado' and serasa == 'Nada Consta':
                tags_list.append("✅ CRÉDITO APROVADO")
            elif credito == 'Bloqueado' or serasa in ['Com Restrição', 'Em Análise']:
                tags_list.append("❌ RECUSADO")
            else:
                tags_list.append("⏳ EM ANÁLISE")
        elif status_geral == 'Perdido':
            tags_list.append("🛑 PERDIDO")
        elif status_geral == 'Novo Lead':
            tags_list.append("🆕 NOVO LEAD")
        elif status_geral == 'Em Negociação':
            tags_list.append("🤝 EM NEGOCIAÇÃO")
        
        # Tag de Análise Específica
        if d.get('analise_credito') == 'Pendente' and "EM ANÁLISE" not in "".join(tags_list):
            tags_list.append("⏳ EM ANÁLISE")

        tag_final = f" [{' | '.join(tags_list)}]" if tags_list else ""
        opcoes.append(f"{d['nome_cliente']} ({d['nome_empresa']}){tag_final}")

    selecao = st.selectbox("🔍 Buscar Cliente Existente (Para Editar Ficha):", opcoes, key=f"c_busca_box_{st.session_state.reset_comercial}")

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    cliente_sel = next((i for i in dados if i["nome_cliente"] == selecao.split(" (")[0]), None) if selecao != "+ Novo Cadastro" else None
    if cliente_sel: st.session_state.dados_importados = {}

    r_key = st.session_state.reset_comercial
    c_id = cliente_sel['id'] if cliente_sel else "novo"
    imp_id = "imp" if st.session_state.dados_importados else "no_imp"
    
    def get_val(field, default=""):
        if cliente_sel:
            val = cliente_sel.get(field)
            if field == 'nome_evento' and (val is None or str(val).strip() == ""): pass 
            elif val is not None and str(val).strip() != "": return val
        
        val_importado = st.session_state.dados_importados.get(field)
        if val_importado is not None and str(val_importado).strip() != "": return val_importado
            
        if field == 'nome_evento' and not df_participantes.empty:
            eventos_ativos = [e for e in df_participantes['nome_evento'].dropna().unique() if str(e).strip() != ""]
            if eventos_ativos: return str(eventos_ativos[0])
                
        return default

    with st.expander("📝 Ficha de Cadastro / Edição", expanded=True if not cliente_sel else False):
        st.markdown("<div style='padding-top: 15px;'></div>", unsafe_allow_html=True)
        st.subheader("👤 1. Dados Cadastrais & Captação")
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        c_cli0, c_cli1, c_cli2, c_cli3 = st.columns(4)
        nome_evento_form = c_cli0.text_input("Evento (Origem)", value=get_val('nome_evento'), key=f"ev_{r_key}_{c_id}_{imp_id}")
        resp_aplicacao = c_cli1.text_input("SDR (Captação)", value=get_val('resp_aplicacao'), key=f"resp_{r_key}_{c_id}_{imp_id}")
        nome_cliente = c_cli2.text_input("Nome do Cliente", value=get_val('nome_cliente'), key=f"nome_{r_key}_{c_id}_{imp_id}")
        empresa = c_cli3.text_input("Empresa", value=get_val('nome_empresa'), key=f"emp_{r_key}_{c_id}_{imp_id}")

        c_cli4, c_cli5, c_cli6 = st.columns(3)
        telefone = c_cli4.text_input("Telefone", value=get_val('telefone'), key=f"tel_{r_key}_{c_id}_{imp_id}")
        email = c_cli5.text_input("E-mail", value=get_val('email'), key=f"mail_{r_key}_{c_id}_{imp_id}")
        cnpj = c_cli6.text_input("CNPJ / CPF", value=get_val('cnpj'), key=f"cnpj_{r_key}_{c_id}_{imp_id}")

        c_cli7, c_cli8, _ = st.columns([1, 1, 2])
        qtd_vagas = c_cli7.number_input("Qtd. Vagas", min_value=1, value=int(get_val('qtd_vagas', 1)), key=f"vagas_{r_key}_{c_id}_{imp_id}")
        qtd_socios = c_cli8.number_input("Qtd. Sócios", min_value=0, value=int(get_val('qtd_socios', 0)), key=f"socios_{r_key}_{c_id}_{imp_id}")

        st.markdown("<div style='margin-top: 15px; margin-bottom: 15px;'><hr></div>", unsafe_allow_html=True)
        
        is_venda_direta_val = (cliente_sel.get('status_entrevista_almoco') == "Não se aplica") if cliente_sel else False
        venda_direta = st.toggle("🚀 Fechamento Direto (Pular etapa de Almoço/Jantar)", value=is_venda_direta_val, key=f"vd_{r_key}_{c_id}_{imp_id}")

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        st.subheader("🍽️ 2. Almoço e Entrevistas")
        a1, a2, a3 = st.columns(3)
        valor_almoco = a1.number_input("R$ Almoço", min_value=0.0, format="%.2f", value=float(cliente_sel['valor_almoco'] or 0.0) if cliente_sel else 0.0, key=f"val_a_{r_key}_{c_id}_{imp_id}")
        
        status_a_opcoes = ["Aguardando", "Realizada", "No-show", "Reprovado", "Não se aplica"]
        status_a_atual = cliente_sel.get('status_entrevista_almoco', "Aguardando") if cliente_sel else "Aguardando"
        status_almoco = a2.selectbox("Status Almoço", status_a_opcoes, index=status_a_opcoes.index(status_a_atual) if status_a_atual in status_a_opcoes else 0, key=f"st_a_{r_key}_{c_id}_{imp_id}")
        entrevistador = a3.text_input("Especialista Almoço *", value=cliente_sel.get('entrevistadores_almoco', '') if cliente_sel else "", key=f"ent_a_{r_key}_{c_id}_{imp_id}", help="Nome do Especialista (Obrigatório)")

        status_jantar = None
        entrevistador_jantar = ""
        if status_almoco == "No-show":
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            st.warning("🌙 Repescagem ativada: Preencha os dados do Jantar")
            j1, j2 = st.columns(2)
            entrevistador_jantar = j1.text_input("Especialista Jantar *", value=cliente_sel.get('entrevistadores_jantar', '') if cliente_sel else "", key=f"ent_j_{r_key}_{c_id}_{imp_id}", help="Nome do Especialista (Obrigatório)")
            status_j_opcoes = ["Aguardando", "Realizada", "No-show", "Reprovado"]
            status_j_atual = cliente_sel.get('status_entrevista_jantar', "Aguardando") if cliente_sel else "Aguardando"
            status_jantar = j2.selectbox("Status Jantar", status_j_opcoes, index=status_j_opcoes.index(status_j_atual) if status_j_atual in status_j_opcoes else 0, key=f"st_j_{r_key}_{c_id}_{imp_id}")

        st.markdown("<div style='margin-top: 20px; margin-bottom: 20px;'><hr></div>", unsafe_allow_html=True)
        
        etapa_comercial_liberada = venda_direta or (status_almoco == "Realizada") or (status_jantar == "Realizada")
        
        sdr_especialista_caixa_final = cliente_sel.get('sdr_especialista_caixa', '') if cliente_sel else ""
        
        # --- AUTO-PREENCHIMENTO DO CLOSER SE ENTREVISTA REALIZADA ---
        if not sdr_especialista_caixa_final:
            if status_almoco == "Realizada" and entrevistador.strip():
                sdr_especialista_caixa_final = entrevistador.strip()
            elif status_jantar == "Realizada" and entrevistador_jantar.strip():
                sdr_especialista_caixa_final = entrevistador_jantar.strip()

        opcoes_produto = ["Selecione...", "AE", "Giants"]
        produto_atual_db = cliente_sel.get('produto') if cliente_sel else "Selecione..."
        if not produto_atual_db or str(produto_atual_db).strip() == "":
             produto_atual_db = "Selecione..."
        produto_final = produto_atual_db
        
        valor_contrato_final = float(cliente_sel.get('valor_contrato', 0.0)) if cliente_sel else 0.0
        valor_vagas_adicionais_final = float(cliente_sel.get('valor_vagas_adicionais', 0.0)) if cliente_sel else 0.0
        valor_entrada_final = float(cliente_sel.get('valor_entrada', 0.0)) if cliente_sel else 0.0
        qtd_p = int(cliente_sel.get('qtd_parcelas_entrada') or 1) if cliente_sel else 1
        forma_pagamento_restante = cliente_sel.get('forma_pagamento_restante', 'Não se aplica') if cliente_sel else "Não se aplica"
        status_geral_final = cliente_sel.get('status_geral', "Novo Lead") if cliente_sel else "Novo Lead"
        faturamento_total_calc = valor_contrato_final + valor_vagas_adicionais_final

        if etapa_comercial_liberada:
            st.subheader("💰 3. Proposta Comercial")
            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
            
            c_prop1, c_prop2 = st.columns(2)
            sdr_especialista_caixa_final = c_prop1.text_input("Closer (Vendedor)", value=sdr_especialista_caixa_final, key=f"closer_{r_key}_{c_id}_{imp_id}")
            produto_final = c_prop2.selectbox("Produto *", opcoes_produto, index=opcoes_produto.index(produto_final) if produto_final in opcoes_produto else 0, key=f"prod_{r_key}_{c_id}_{imp_id}")

            st.markdown("<div style='margin-top: 15px;'><strong>1. Valores do Contrato</strong></div>", unsafe_allow_html=True)
            
            if qtd_vagas > 1:
                v_col1, v_col2 = st.columns(2)
                valor_contrato_final = v_col1.number_input("Valor Proposta (Principal) R$", min_value=0.0, format="%.2f", value=valor_contrato_final, key=f"v_pro_{r_key}_{c_id}_{imp_id}")
                valor_vagas_adicionais_final = v_col2.number_input("Valor Vaga(s) Adicional(is) R$", min_value=0.0, format="%.2f", value=valor_vagas_adicionais_final, key=f"v_vaga_{r_key}_{c_id}_{imp_id}")
            else:
                valor_contrato_final = st.number_input("Valor Proposta (Principal) R$", min_value=0.0, format="%.2f", value=valor_contrato_final, key=f"v_pro_{r_key}_{c_id}_{imp_id}")
                valor_vagas_adicionais_final = 0.0

            st.markdown("<div style='margin-top: 15px;'><strong>2. Condições de Pagamento</strong></div>", unsafe_allow_html=True)
            f1, f2, f3 = st.columns(3)
            valor_entrada_final = f1.number_input("Valor Entrada R$", min_value=0.0, format="%.2f", value=valor_entrada_final, key=f"v_ent_{r_key}_{c_id}_{imp_id}")
            
            faturamento_total_calc = valor_contrato_final + valor_vagas_adicionais_final
            falta_pagar = faturamento_total_calc - valor_entrada_final
            
            with f2:
                st.markdown(f"""
                    <div style="display: flex; flex-direction: column; margin-bottom: 1rem; margin-top: -2px;">
                        <label style="font-size: 14px; color: var(--text-color); margin-bottom: 6px;">Falta Pagar R$</label>
                        <div style="background-color: var(--secondary-background-color); border: 1px solid var(--border-color); padding: 0.5rem 0.75rem; border-radius: 0.5rem; color: var(--text-color); opacity: 0.6; cursor: not-allowed; display: flex; align-items: center; min-height: 40px; font-family: monospace;">
                            {formata_brl(falta_pagar)}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            qtd_p = f3.number_input("Qtd. Parcelas da Entrada", min_value=1, value=qtd_p, key=f"qtd_p_{r_key}_{c_id}_{imp_id}")
            
            f4, f5 = st.columns(2)
            opcoes_pagamento = ["Boleto", "Cartão de Crédito", "Cartão de Débito", "Pix", "Cheque", "Transferência", "Não se aplica"]
            forma_pagamento_restante = f4.selectbox("Forma de Pagto. (Restante)", opcoes_pagamento, index=opcoes_pagamento.index(forma_pagamento_restante) if forma_pagamento_restante in opcoes_pagamento else 0, key=f"forma_pag_{r_key}_{c_id}_{imp_id}")
            
            is_financeiro_aprovado = False
            if cliente_sel:
                cred_val = cliente_sel.get('analise_credito')
                serasa_val = cliente_sel.get('status_serasa')
                if cred_val == 'Liberado' and serasa_val == 'Nada Consta':
                    is_financeiro_aprovado = True

            if is_financeiro_aprovado or status_geral_final == "Contrato Assinado":
                geral_opcoes = ["Novo Lead", "Em Negociação", "Aguardando Financeiro", "Contrato Assinado", "Perdido"]
            else:
                geral_opcoes = ["Novo Lead", "Em Negociação", "Aguardando Financeiro", "Perdido"]

            status_geral_final = f5.selectbox("Status Venda", geral_opcoes, index=geral_opcoes.index(status_geral_final) if status_geral_final in geral_opcoes else 0, key=f"st_g_{r_key}_{c_id}_{imp_id}")
            
            with f5:
                if is_financeiro_aprovado and status_geral_final != "Contrato Assinado":
                    st.caption("✅ Crédito aprovado! Pode avançar para 'Contrato Assinado'.")
                elif not is_financeiro_aprovado and status_geral_final != "Contrato Assinado":
                    st.caption("🔒 'Contrato Assinado' requer aprovação prévia do Financeiro.")

            if qtd_p > 1 and valor_entrada_final > 0:
                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                st.info(f"💳 Informação: Entrada de **{formata_brl(valor_entrada_final)}** em {qtd_p}x de **{formata_brl(valor_entrada_final/qtd_p)}**")
        else:
            st.subheader("💰 3. Proposta Comercial")
            st.info("🔒 A etapa de **Proposta Comercial** só será exibida se o cliente comparecer ao evento (Almoço/Jantar Realizados) ou em caso de Fechamento Direto.")

        # --- SECÇÃO: COMENTÁRIOS ---
        st.markdown("<div style='margin-top: 20px; margin-bottom: 20px;'><hr></div>", unsafe_allow_html=True)
        st.subheader("💬 4. Comentários e Interações")
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        
        todos_logs = []
        if cliente_sel:
            try:
                res_logs = supabase.table("logs_auditoria").select("*").eq("cliente_id", str(cliente_sel['id'])).order("data_alteracao", desc=True).execute()
                todos_logs = res_logs.data if res_logs.data else []
            except Exception:
                todos_logs = []

        comentarios_manuais = [log for log in todos_logs if log.get('estado_antigo') == 'Adição de Comentário']

        if comentarios_manuais:
            with st.container(height=300):
                for log in comentarios_manuais:
                    data_formatada = pd.to_datetime(log.get('data_alteracao')).strftime("%d/%m/%Y %H:%M")
                    st.markdown(f"""
                        <div style="background-color: var(--secondary-background-color); border-left: 4px solid var(--primary-color); padding: 10px 15px; margin-bottom: 10px; border-radius: 0 4px 4px 0;">
                            <div style="font-size: 11px; color: gray; margin-bottom: 4px;">
                                <strong>👤 {log.get('quem_alterou', 'Desconhecido')}</strong> • 🕒 {data_formatada}
                            </div>
                            <div style="font-size: 14px; color: var(--text-color);">
                                {log.get('novo_estado', '')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.caption("Ainda não existem comentários manuais para este cliente.")

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        nova_nota = st.text_area("Escrever Novo Comentário (Visível para a equipa):", height=68, placeholder="Ex: O cliente atendeu e pediu envio de proposta...", key=f"nova_nota_{r_key}_{c_id}_{imp_id}")
        
        if cliente_sel:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Gravar Apenas Comentário", type="secondary"):
                if nova_nota.strip():
                    log_payload = {
                        "data_alteracao": datetime.now().isoformat(),
                        "quem_alterou": usuario_logado,
                        "quem_foi_afetado": cliente_sel['nome_cliente'],
                        "cliente_id": str(cliente_sel['id']),
                        "estado_antigo": "Adição de Comentário",
                        "novo_estado": nova_nota.strip()
                    }
                    try:
                        supabase.table("logs_auditoria").insert(log_payload).execute()
                        st.success("Comentário adicionado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar comentário: {e}")
                else:
                    st.warning("Escreva algo no comentário antes de gravar.")

        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        
        if st.button("🚀 Salvar / Atualizar Ficha", type="primary", use_container_width=True):
            nome_ja_existe = False
            if not cliente_sel and nome_cliente:
                nome_buscado = str(nome_cliente).strip().lower()
                for d in dados:
                    if str(d.get('nome_cliente', '')).strip().lower() == nome_buscado:
                        nome_ja_existe = True
                        break

            # Validações de obrigatoriedade
            if not venda_direta and status_almoco != "Não se aplica" and not entrevistador.strip():
                st.error("❌ Erro: É obrigatório preencher o nome do Especialista (Entrevistador Almoço)!")
            elif not venda_direta and status_almoco == "No-show" and status_jantar != "Não se aplica" and not entrevistador_jantar.strip():
                st.error("❌ Erro: É obrigatório preencher o nome do Especialista (Entrevistador Jantar)!")
            elif etapa_comercial_liberada and valor_entrada_final > faturamento_total_calc:
                st.error("❌ Erro: O valor da entrada não pode ser maior que o valor total do contrato (Principal + Vagas Extras)!")
            elif etapa_comercial_liberada and produto_final == "Selecione...":
                st.error("❌ Erro: A etapa de Proposta Comercial está desbloqueada. É obrigatório selecionar o 'Produto' (AE ou Giants).")
            elif not nome_cliente or not empresa:
                st.error("Preencha ao menos o Nome do Cliente e a Empresa!")
            elif nome_ja_existe:
                st.error(f"⚠️ Atenção: O cliente **{nome_cliente}** já está cadastrado no sistema! Por favor, procure-o na barra de seleção acima para editar a sua ficha.")
            else:
                produto_db = "" if (not etapa_comercial_liberada and produto_final == "Selecione...") else (produto_final if produto_final != "Selecione..." else "")

                # Garante o preenchimento do closer caso esteja vazio mas a etapa foi realizada e ele tentou submeter vazio
                closer_para_salvar = sdr_especialista_caixa_final.strip()
                if not closer_para_salvar:
                    if status_almoco == "Realizada":
                        closer_para_salvar = entrevistador.strip()
                    elif status_jantar == "Realizada":
                        closer_para_salvar = entrevistador_jantar.strip()

                payload = {
                    "atualizado_por": usuario_logado, 
                    "nome_evento": nome_evento_form, 
                    "resp_aplicacao": resp_aplicacao,
                    "sdr_especialista_caixa": closer_para_salvar,
                    "produto": produto_db, 
                    "nome_cliente": nome_cliente, 
                    "nome_empresa": empresa, 
                    "cnpj": re.sub(r'\D', '', str(cnpj)) if cnpj else "",           
                    "telefone": re.sub(r'\D', '', str(telefone)) if telefone else "",   
                    "email": email, 
                    "qtd_vagas": int(qtd_vagas),
                    "qtd_socios": int(qtd_socios),
                    "valor_almoco": float(valor_almoco),
                    "status_entrevista_almoco": "Não se aplica" if venda_direta else status_almoco, 
                    "entrevistadores_almoco": entrevistador,
                    "entrevistadores_jantar": entrevistador_jantar, 
                    "status_entrevista_jantar": status_jantar,
                    "valor_contrato": float(valor_contrato_final), 
                    "valor_vagas_adicionais": float(valor_vagas_adicionais_final),
                    "valor_entrada": float(valor_entrada_final),
                    "qtd_parcelas_entrada": int(qtd_p),
                    "forma_pagamento_restante": forma_pagamento_restante,
                    "status_geral": status_geral_final
                }

                mudancas_old = []
                mudancas_new = []

                if cliente_sel:
                    for chave, novo_valor in payload.items():
                        if chave in ['atualizado_por']: continue
                        valor_antigo = cliente_sel.get(chave)
                        
                        if chave in ['valor_contrato', 'valor_vagas_adicionais', 'valor_entrada', 'valor_almoco']:
                            old_str = formata_brl(valor_antigo or 0)
                            new_str = formata_brl(novo_valor or 0)
                        else:
                            old_str = str(valor_antigo).strip()
                            new_str = str(novo_valor).strip()
                        
                        if old_str != new_str:
                            nome_campo_visivel = chave.replace('_', ' ').title()
                            mudancas_old.append(f"{nome_campo_visivel}: {old_str}")
                            mudancas_new.append(f"{nome_campo_visivel}: {new_str}")

                try:
                    if cliente_sel:
                        supabase.table("vendas_contratos").update(payload).eq("id", cliente_sel['id']).execute()
                        if mudancas_old and mudancas_new:
                            log_payload = {
                                "data_alteracao": datetime.now().isoformat(),
                                "quem_alterou": usuario_logado,
                                "quem_foi_afetado": cliente_sel['nome_cliente'],
                                "cliente_id": str(cliente_sel['id']),
                                "estado_antigo": " | ".join(mudancas_old),
                                "novo_estado": " | ".join(mudancas_new)
                            }
                            supabase.table("logs_auditoria").insert(log_payload).execute()
                            
                        if nova_nota and nova_nota.strip():
                            nota_payload = {
                                "data_alteracao": datetime.now().isoformat(),
                                "quem_alterou": usuario_logado,
                                "quem_foi_afetado": cliente_sel['nome_cliente'],
                                "cliente_id": str(cliente_sel['id']),
                                "estado_antigo": "Adição de Comentário",
                                "novo_estado": nova_nota.strip()
                            }
                            supabase.table("logs_auditoria").insert(nota_payload).execute()

                    else:
                        payload["criado_por"] = usuario_logado
                        res_insert = supabase.table("vendas_contratos").insert(payload).execute()
                        
                        if res_insert.data and len(res_insert.data) > 0:
                            novo_id = res_insert.data[0]['id']
                            log_criacao = {
                                "data_alteracao": datetime.now().isoformat(),
                                "quem_alterou": usuario_logado,
                                "quem_foi_afetado": nome_cliente,
                                "cliente_id": str(novo_id),
                                "estado_antigo": "N/A",
                                "novo_estado": "Criação de Ficha de Cliente"
                            }
                            supabase.table("logs_auditoria").insert(log_criacao).execute()
                            
                            if nova_nota and nova_nota.strip():
                                nota_payload = {
                                    "data_alteracao": datetime.now().isoformat(),
                                    "quem_alterou": usuario_logado,
                                    "quem_foi_afetado": nome_cliente,
                                    "cliente_id": str(novo_id),
                                    "estado_antigo": "Adição de Comentário",
                                    "novo_estado": nova_nota.strip()
                                }
                                supabase.table("logs_auditoria").insert(nota_payload).execute()
                    
                    st.session_state.dados_importados = {}
                    st.session_state.reset_comercial += 1
                    st.success("✅ Sucesso! Os dados foram guardados e o formulário limpo.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar no banco: {e}")

    # 4. VISÃO GERAL (TABS)
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    st.divider()
    st.subheader("📊 Visão Geral do Funil")
    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    
    if not df_comercial.empty:
        df_comercial['valor_contrato'] = pd.to_numeric(df_comercial['valor_contrato'], errors='coerce').fillna(0)
        df_comercial['valor_vagas_adicionais'] = pd.to_numeric(df_comercial.get('valor_vagas_adicionais', 0), errors='coerce').fillna(0)
        df_comercial['valor_entrada'] = pd.to_numeric(df_comercial['valor_entrada'], errors='coerce').fillna(0)
        df_comercial['falta_pagar'] = (df_comercial['valor_contrato'] + df_comercial['valor_vagas_adicionais']) - df_comercial['valor_entrada']
        
        tab_kanban, tab_tabela = st.tabs(["🗂️ Quadro Kanban", "📋 Planilha Mestra (Todos os Campos)"])
        
        with tab_kanban:
            st.markdown("<div style='padding-top: 15px;'></div>", unsafe_allow_html=True)
            fases = ["Novo Lead", "Em Negociação", "Aguardando Financeiro", "Contrato Assinado", "Perdido"]
            cols = st.columns(len(fases))
            for i, fase in enumerate(fases):
                with cols[i]:
                    df_fase = df_comercial[df_comercial['status_geral'] == fase]
                    st.markdown(f"<h4 style='text-align: center; color: #005088; font-size: 16px;'>{fase}</h4>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align: center; color: #64748b; font-size: 12px; margin-bottom: 15px;'>{len(df_fase)} lead(s)</div>", unsafe_allow_html=True)
                    with st.container(height=550, border=False):
                        for _, row in df_fase.iterrows():
                            with st.container(border=True):
                                st.markdown(f"**{row['nome_cliente']}**")
                                st.markdown(f"<span style='font-size: 12px; color: gray;'>🏢 {row['nome_empresa']}</span>", unsafe_allow_html=True)
                                
                                dias_parado = row.get('dias_no_funil', 0)
                                if fase in ["Novo Lead", "Em Negociação"] and dias_parado > 7:
                                    st.markdown(f"<div style='background-color:#fee2e2; color:#991b1b; padding:4px 8px; border-radius:4px; font-size:11px; margin-top:8px; margin-bottom:8px; font-weight:bold;'>🚨 S/Ação há {int(dias_parado)} dias</div>", unsafe_allow_html=True)

                                st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
                                if row.get('produto') and str(row.get('produto')).strip() != "":
                                    st.markdown(f"<span style='font-size: 11px; background-color: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px;'>{row['produto']}</span>", unsafe_allow_html=True)
                                if row.get('sdr_especialista_caixa'):
                                    st.markdown(f"<span style='font-size: 11px; color: #005088; display:block; margin-top:4px;'>Vendedor: {row['sdr_especialista_caixa']}</span>", unsafe_allow_html=True)
                                faturamento_card = row['valor_contrato'] + row.get('valor_vagas_adicionais', 0.0)
                                if faturamento_card > 0:
                                    st.markdown(f"<span style='font-size: 13px; color: #11caa0; font-weight: bold; display:block; margin-top:4px;'>💰 {formata_brl(faturamento_card)}</span>", unsafe_allow_html=True)
                                if fase == "Aguardando Financeiro":
                                    icon_credito = "✅" if row.get('analise_credito') == "Liberado" else "⏳"
                                    if row.get('analise_credito') == 'Bloqueado': icon_credito = "❌"
                                    st.markdown(f"<span style='font-size: 12px; display:block; margin-top:4px;'>Crédito: {icon_credito}</span>", unsafe_allow_html=True)

        with tab_tabela:
            st.markdown("<div style='padding-top: 15px;'></div>", unsafe_allow_html=True)
            colunas_full = [
                "nome_evento", "nome_cliente", "nome_empresa", "cnpj", "telefone", "email", "qtd_vagas", "qtd_socios",
                "produto", "status_geral", "analise_credito", "status_serasa", "valor_contrato", "valor_vagas_adicionais",
                "valor_entrada", "falta_pagar", "qtd_parcelas_entrada", "forma_pagamento_restante", "investimento_cashback", 
                "resp_aplicacao", "sdr_especialista_caixa", "valor_almoco", 
                "status_entrevista_almoco", "entrevistadores_almoco", 
                "status_entrevista_jantar", "entrevistadores_jantar", 
                "status_pagamento_giants", "status_nf", "criado_em", "atualizado_por"
            ]
            c_busca_t, c_export = st.columns([3, 1])
            with c_busca_t:
                busca_t = st.text_input("🔍 Filtrar por qualquer campo (Tabela Full):", key="search_full_table")
            
            colunas_existentes = [c for c in colunas_full if c in df_comercial.columns]
            df_display = df_comercial[colunas_existentes]
            
            if busca_t:
                df_display = df_display[df_display.stack().astype(str).str.contains(busca_t, case=False, na=False).groupby(level=0).any()]
            with c_export:
                st.write("") 
                st.write("")
                csv = df_display.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Exportar Dados (CSV)", data=csv, file_name='relatorio_comercial_full.csv', mime='text/csv', use_container_width=True)
            st.dataframe(
                df_display, 
                column_config={
                    "nome_evento": "Evento",
                    "produto": "Produto",
                    "valor_contrato": st.column_config.NumberColumn("Valor Principal", format="R$ %.2f"), 
                    "valor_vagas_adicionais": st.column_config.NumberColumn("Valor Vaga Extra", format="R$ %.2f"), 
                    "valor_entrada": st.column_config.NumberColumn("Entrada", format="R$ %.2f"),
                    "falta_pagar": st.column_config.NumberColumn("Falta Pagar", format="R$ %.2f"),
                    "valor_almoco": st.column_config.NumberColumn("Valor Almoço", format="R$ %.2f"),
                    "forma_pagamento_restante": "Pgto. Restante",
                    "status_nf": "Status NF"
                }, 
                hide_index=True, 
                use_container_width=True
            )
    else:
        st.info("Nenhum dado cadastrado.")