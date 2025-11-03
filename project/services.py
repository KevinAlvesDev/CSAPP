# project/services.py

from flask import current_app, g
from .db import query_db, execute_db
from .constants import (
    CHECKLIST_OBRIGATORIO_ITEMS, MODULO_OBRIGATORIO,
    TAREFAS_TREINAMENTO_PADRAO, MODULO_PENDENCIAS,
    PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR,
    NIVEIS_RECEITA # <-- INÍCIO DA CORREÇÃO: Importar a lista
)
# Importa as duas funções de formatação
from .utils import format_date_iso_for_json, format_date_br

# Importa logar_timeline do DB (para uso interno)
from .db import logar_timeline
# Importa timedelta, datetime e date para cálculo de data
from datetime import datetime, timedelta, date # Adicionado datetime
import calendar # Adicionado para cálculo de gamificação

# --- Camada de Serviço (Business Logic) ---

def _create_default_tasks(impl_id):
    """Cria as tarefas padrão (Obrigatórias e Treinamento) para uma nova implantação."""
    tasks_added = 0
    # Tarefas Obrigatórias
    for i, tarefa_nome in enumerate(CHECKLIST_OBRIGATORIO_ITEMS, 1):
        execute_db(
            "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
            (impl_id, MODULO_OBRIGATORIO, tarefa_nome, i, 'Ação interna')
        )
        tasks_added += 1

    # Tarefas de Treinamento
    for modulo, tarefas_info in TAREFAS_TREINAMENTO_PADRAO.items():
        for i, tarefa_info in enumerate(tarefas_info, 1):
            execute_db(
                "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, ordem, tag) VALUES (%s, %s, %s, %s, %s)",
                (impl_id, modulo, tarefa_info['nome'], i, tarefa_info.get('tag', ''))
            )
            tasks_added += 1
    return tasks_added

def _get_progress(impl_id):
    """Calcula o progresso de uma implantação (incluindo todas as tarefas)."""
    counts = query_db(
        "SELECT COUNT(*) as total, SUM(CASE WHEN concluida THEN 1 ELSE 0 END) as done "
        "FROM tarefas WHERE implantacao_id = %s",
        (impl_id,),
        one=True
    )
    # Garante que counts não seja None antes de acessar 'total' ou 'done'
    total = counts.get('total', 0) if counts else 0
    done = counts.get('done', 0) if counts else 0
    # Converte done para int se vier como Decimal ou outro tipo numérico (comum em alguns DBs)
    done = int(done) if done is not None else 0

    return int(round((done / total) * 100)) if total > 0 else 0, total, done


def auto_finalizar_implantacao(impl_id, usuario_cs_email):
    """
    Verifica se todas as tarefas (exceto pendências) estão concluídas
    e, em caso afirmativo, finaliza a implantação.
    """
    pending_tasks = query_db(
        "SELECT COUNT(*) as total FROM tarefas "
        "WHERE implantacao_id = %s AND concluida = %s AND tarefa_pai != %s",
        (impl_id, 0, MODULO_PENDENCIAS),
        one=True
    )

    # Garante que pending_tasks não seja None
    total_pendentes = pending_tasks.get('total', 0) if pending_tasks else 0

    if total_pendentes == 0:
        impl_status = query_db(
            "SELECT status, nome_empresa FROM implantacoes WHERE id = %s",
            (impl_id,),
            one=True
        )
        if impl_status and impl_status.get('status') == 'andamento':
            agora = datetime.now() # Captura timestamp para consistência
            execute_db(
                "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = %s WHERE id = %s",
                (agora, impl_id)
            )
            detalhe = f'Implantação "{impl_status.get("nome_empresa", "N/A")}" auto-finalizada.'
            logar_timeline(impl_id, usuario_cs_email, 'auto_finalizada', detalhe)

            # Busca o log recém-criado para retornar formatado
            perfil = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (usuario_cs_email,), one=True)
            nome = perfil.get('nome') if perfil else usuario_cs_email

            log_final = query_db(
                "SELECT *, %s as usuario_nome FROM timeline_log "
                "WHERE implantacao_id = %s AND tipo_evento = 'auto_finalizada' "
                "ORDER BY id DESC LIMIT 1",
                (nome, impl_id),
                one=True
            )
            if log_final:
                # Garante que log_final seja um dict antes de modificar
                if not isinstance(log_final, dict):
                    log_final = dict(log_final)
                log_final['data_criacao'] = format_date_iso_for_json(log_final.get('data_criacao'))
                return True, log_final
            else:
                # Mesmo que o log não seja encontrado (improvável), a finalização ocorreu
                return True, None
    return False, None

# --- FUNÇÃO CORRIGIDA (get_dashboard_data) ---
def get_dashboard_data(user_email):
    """
    Busca e processa todos os dados para o dashboard.
    Filtra por usuário logado (user_email) A MENOS QUE seja um perfil de gerente.
    """

    # ==== AJUSTE 2: Lógica de Perfil Gerencial ====
    perfil_acesso = g.perfil.get('perfil_acesso') if g.get('perfil') else None
    manager_profiles = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]
    
    is_manager_view = perfil_acesso in manager_profiles

    # 1. Busca implantações
    # A consulta base agora inclui JOIN para pegar o nome do CS
    query_sql = """
        SELECT i.*, p.nome as cs_nome
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
    """
    args = []

    # Se NÃO for gerente, filtra pelo usuário logado
    if not is_manager_view:
        query_sql += " WHERE i.usuario_cs = %s "
        args.append(user_email)

    # Adiciona ordenação
    query_sql += """
        ORDER BY CASE status
                     WHEN 'nova' THEN 1      -- 'nova' vem primeiro
                     WHEN 'andamento' THEN 2
                     WHEN 'parada' THEN 3
                     WHEN 'futura' THEN 4
                     WHEN 'finalizada' THEN 5
                     ELSE 6
                 END, data_criacao DESC
    """
    
    impl_list = query_db(query_sql, tuple(args))
    # ==== FIM DO AJUSTE 2 ====

    # Garante que impl_list seja sempre uma lista
    impl_list = impl_list if impl_list is not None else []


    dashboard_data = {
        'andamento': [], 'atrasadas': [], 'futuras': [],
        'finalizadas': [], 'paradas': [], 'novas': [] # Adicionado 'novas'
    }
    metrics = {
        'impl_andamento_total': 0, 'implantacoes_atrasadas': 0,
        'implantacoes_futuras': 0, 'impl_finalizadas': 0, 'impl_paradas': 0,
        'impl_novas': 0, # Adicionado 'impl_novas'
        # REQ 3: Adiciona totais de valor para o dashboard
        'total_valor_andamento': 0.0,
        'total_valor_atrasadas': 0.0,
        'total_valor_futuras': 0.0,
        'total_valor_finalizadas': 0.0,
        'total_valor_paradas': 0.0,
        'total_valor_novas': 0.0, # Adicionado 'total_valor_novas'
    }

    # Otimização: Buscar todas as tarefas de uma vez
    impl_ids = [impl['id'] for impl in impl_list if impl and 'id' in impl] # Garante que impl e id existam
    tasks_by_impl = {}
    if impl_ids:
        placeholders = ','.join(['%s'] * len(impl_ids)) 
        sql = f"SELECT implantacao_id, concluida FROM tarefas WHERE implantacao_id IN ({placeholders})"
        all_tasks = query_db(sql, tuple(impl_ids))

        if all_tasks: # Verifica se a consulta retornou algo
            for task in all_tasks:
                # Garante que a chave exista antes de anexar
                impl_id_key = task.get('implantacao_id')
                if impl_id_key is not None: # Verifica se a chave existe e não é None
                    if impl_id_key not in tasks_by_impl:
                        tasks_by_impl[impl_id_key] = []
                    tasks_by_impl[impl_id_key].append(task)

    agora = datetime.now() # Obter a hora atual uma vez

    for impl in impl_list:
        # Pula se 'impl' for None ou não for um dicionário (segurança extra)
        if not impl or not isinstance(impl, dict):
            continue

        impl_id = impl.get('id')
        # Pula se não houver ID (improvável, mas seguro)
        if impl_id is None:
            continue

        status = impl.get('status')

        # Formata datas para os modais
        impl['data_criacao_iso'] = format_date_iso_for_json(impl.get('data_criacao'), only_date=True)
        impl['data_inicio_efetivo_iso'] = format_date_iso_for_json(impl.get('data_inicio_efetivo'), only_date=True)
        impl['data_inicio_producao_iso'] = format_date_iso_for_json(impl.get('data_inicio_producao'), only_date=True)
        impl['data_final_implantacao_iso'] = format_date_iso_for_json(impl.get('data_final_implantacao'), only_date=True)

        # Calcula progresso usando os dados pré-buscados
        impl_tasks = tasks_by_impl.get(impl_id, []) # Usa .get com default lista vazia
        total_tasks = len(impl_tasks)
        done_tasks = sum(1 for t in impl_tasks if t.get('concluida')) # Usa .get para segurança
        impl['progresso'] = int(round((done_tasks / total_tasks) * 100)) if total_tasks > 0 else 0

        # Converte valor_atribuido para float
        try:
            impl_valor = float(impl.get('valor_atribuido', 0.0))
        except (ValueError, TypeError):
            impl_valor = 0.0
        # Armazena o valor float para garantir consistência (embora o template formate)
        impl['valor_atribuido'] = impl_valor


        # Cálculo de dias_passados em Python (usado para Atrasadas)
        dias_passados = 0
        data_inicio_obj = impl.get('data_inicio_efetivo') 
        
        if data_inicio_obj:
            data_inicio_datetime = None
            if isinstance(data_inicio_obj, str):
                try:
                    data_inicio_datetime = datetime.fromisoformat(data_inicio_obj)
                except ValueError:
                    try:
                        data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d')
                    except ValueError:
                        print(f"AVISO: Formato de data_inicio_efetivo (str) inválido para impl {impl_id}: {data_inicio_obj}")
            
            elif isinstance(data_inicio_obj, date) and not isinstance(data_inicio_obj, datetime):
                data_inicio_datetime = datetime.combine(data_inicio_obj, datetime.min.time())
            
            elif isinstance(data_inicio_obj, datetime):
                data_inicio_datetime = data_inicio_obj

            if data_inicio_datetime:
                try:
                    agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
                    inicio_naive = data_inicio_datetime.replace(tzinfo=None) if data_inicio_datetime.tzinfo else data_inicio_datetime
                    dias_passados_delta = agora_naive - inicio_naive
                    dias_passados = dias_passados_delta.days if dias_passados_delta.days >= 0 else 0
                except TypeError as te:
                    print(f"AVISO: Erro de tipo ao calcular dias passados para impl {impl_id}. Verifique timezones. Erro: {te}")
                    dias_passados = -1 
                    
        impl['dias_passados'] = dias_passados # Adiciona o campo para o template

        # Classifica a implantação
        if status == 'finalizada':
            dashboard_data['finalizadas'].append(impl)
            metrics['impl_finalizadas'] += 1
            metrics['total_valor_finalizadas'] += impl_valor
        elif status == 'parada':
            dashboard_data['paradas'].append(impl)
            metrics['impl_paradas'] += 1
            metrics['total_valor_paradas'] += impl_valor
        elif status == 'futura': 
            dashboard_data['futuras'].append(impl)
            metrics['implantacoes_futuras'] += 1
            metrics['total_valor_futuras'] += impl_valor
            
            # Lógica de 'atrasada_para_iniciar' para 'futura'
            data_prevista_str = impl.get('data_inicio_previsto')
            data_prevista_obj = None

            if data_prevista_str and isinstance(data_prevista_str, str):
                try:
                    data_prevista_obj = datetime.strptime(data_prevista_str, '%Y-%m-%d').date()
                except ValueError:
                    print(f"AVISO: Formato de data_inicio_previsto (str) inválido para impl {impl_id}: {data_prevista_str}")
            elif isinstance(data_prevista_str, date):
                data_prevista_obj = data_prevista_str

            impl['data_inicio_previsto_fmt_d'] = format_date_br(data_prevista_obj or data_prevista_str, include_time=False)
            
            if data_prevista_obj and data_prevista_obj < agora.date():
                impl['atrasada_para_iniciar'] = True
            else:
                impl['atrasada_para_iniciar'] = False

        elif status == 'nova':
            dashboard_data['novas'].append(impl)
            metrics['impl_novas'] += 1
            metrics['total_valor_novas'] += impl_valor

        elif status == 'andamento':
            metrics['impl_andamento_total'] += 1 # Conta 'andamento' e 'atrasadas' no total
            
            if dias_passados > 25:
                dashboard_data['atrasadas'].append(impl)
                metrics['implantacoes_atrasadas'] += 1
                metrics['total_valor_atrasadas'] += impl_valor
            else:
                dashboard_data['andamento'].append(impl)
                metrics['total_valor_andamento'] += impl_valor 

        else:
            print(f"AVISO: Implantação ID {impl_id} com status desconhecido ou nulo: '{status}'. Ignorando na categorização.")


    # Atualiza o perfil com as métricas calculadas
    # SÓ atualiza as métricas do *perfil* se NÃO for manager (pois manager vê métricas globais)
    if not is_manager_view and impl_list:
        try:
            rows_affected = execute_db(
                """
                UPDATE perfil_usuario
                SET impl_andamento_total = %s, implantacoes_atrasadas = %s,
                    impl_finalizadas = %s, impl_paradas = %s
                WHERE usuario = %s
                """,
                (metrics['impl_andamento_total'], metrics['implantacoes_atrasadas'],
                 metrics['impl_finalizadas'], metrics['impl_paradas'], user_email)
            )
        except Exception as update_err:
            print(f"AVISO: Falha ao atualizar métricas no perfil {user_email}: {update_err}")

    return dashboard_data, metrics
# --- FIM DA FUNÇÃO CORRIGIDA ---


def calculate_time_in_status(impl_id, status_target='parada'):
    """
    Calcula o tempo (em dias) que uma implantação permaneceu em um status específico.
    Usado para calcular a duração da parada atual.
    """
    impl = query_db(
        "SELECT data_criacao, data_finalizacao, status FROM implantacoes WHERE id = %s",
        (impl_id,), one=True
    )

    if not impl or not impl.get('status'):
        return None # Implantação não encontrada ou sem status definido

    if impl['status'] == status_target and status_target == 'parada' and impl.get('data_finalizacao'):
        data_inicio_parada_obj = impl['data_finalizacao']
        
        data_inicio_parada_datetime = None
        if isinstance(data_inicio_parada_obj, str):
            try:
                data_inicio_parada_datetime = datetime.fromisoformat(data_inicio_parada_obj)
            except ValueError:
                print(f"AVISO: Formato de data_finalizacao (str) inválido para impl {impl_id}: {data_inicio_parada_obj}")
                return None
        elif isinstance(data_inicio_parada_obj, date) and not isinstance(data_inicio_parada_obj, datetime):
            data_inicio_parada_datetime = datetime.combine(data_inicio_parada_obj, datetime.min.time())
        elif isinstance(data_inicio_parada_obj, datetime):
            data_inicio_parada_datetime = data_inicio_parada_obj
        
        if data_inicio_parada_datetime:
            agora = datetime.now()
            agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
            parada_naive = data_inicio_parada_datetime.replace(tzinfo=None) if data_inicio_parada_datetime.tzinfo else data_inicio_parada_datetime
            try:
                delta = agora_naive - parada_naive
                return max(0, int(delta.days)) # Retorna o número de dias
            except TypeError as te:
                print(f"AVISO: Erro de tipo ao calcular tempo parado para impl {impl_id}. Verifique timezones. Erro: {te}")
                return None

    return None # Não está no status alvo ou dados insuficientes


# --- FUNÇÃO get_analytics_data (TOTALMENTE ATUALIZADA) ---
def get_analytics_data(target_cs_email=None, target_status=None, start_date=None, end_date=None, target_tag=None):
    """Busca e processa dados de TODA a carteira (ou filtrada) para o módulo Gerencial."""

    query_impl = """
        SELECT i.*,
               p.nome as cs_nome, p.cargo as cs_cargo, p.perfil_acesso as cs_perfil
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        WHERE 1=1
    """
    args_impl = []

    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    date_func = "date" if is_sqlite else "" 

    if target_cs_email:
        query_impl += " AND i.usuario_cs = %s "
        args_impl.append(target_cs_email)

    if target_status and target_status != 'todas':
        if target_status == 'atrasadas_status':
            if is_sqlite:
                query_impl += " AND i.status = 'andamento' AND i.data_inicio_efetivo IS NOT NULL AND date(i.data_inicio_efetivo) <= date('now', '-26 days') " 
            else: # PostgreSQL
                query_impl += " AND i.status = 'andamento' AND i.data_inicio_efetivo IS NOT NULL AND i.data_inicio_efetivo <= NOW() - INTERVAL '26 days' " 
        elif target_status == 'nova':
            query_impl += " AND i.status = 'nova' "
        elif target_status == 'futura': # REQ: Adicionado filtro 'futura'
            query_impl += " AND i.status = 'futura' "
        else:
            query_impl += " AND i.status = %s "
            args_impl.append(target_status)

    date_field_to_filter = "i.data_finalizacao" if target_status == 'finalizada' else "i.data_criacao"

    if start_date:
        query_impl += f" AND {date_func}({date_field_to_filter}) >= {date_func}(%s) "
        args_impl.append(start_date)
    if end_date:
        if not is_sqlite:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                next_day = end_date_obj + timedelta(days=1)
                query_impl += f" AND {date_field_to_filter} < %s "
                args_impl.append(next_day.strftime('%Y-%m-%d'))
            except ValueError:
                print(f"AVISO: Formato de end_date inválido ({end_date}). Usando <=.")
                query_impl += f" AND {date_func}({date_field_to_filter}) <= {date_func}(%s) "
                args_impl.append(end_date)
        else: # SQLite usa <=
            query_impl += f" AND {date_func}({date_field_to_filter}) <= {date_func}(%s) "
            args_impl.append(end_date)


    query_impl += " ORDER BY i.nome_empresa "

    # 1. BUSCA PRINCIPAL DE IMPLANTAÇÕES (FILTRADAS)
    impl_list = query_db(query_impl, tuple(args_impl))
    impl_list = impl_list if impl_list is not None else [] # Garante lista

    # 2. BUSCA DE TAREFAS (PARA PRODUTIVIDADE, SE NECESSÁRIO NO FUTURO)
    # (Mantido, embora não usado diretamente nos gráficos atuais)
    query_tasks = """
        SELECT i.usuario_cs, t.tag
        FROM tarefas t
        JOIN implantacoes i ON t.implantacao_id = i.id
        WHERE t.concluida = TRUE AND t.tag IN ('Ação interna', 'Reunião')
        AND t.data_conclusao IS NOT NULL
    """
    args_tasks = []
    # (O restante da query de tasks foi omitido para brevidade, mas está no original)
    # ...
    tasks_data = query_db(query_tasks, tuple(args_tasks))
    tasks_data = tasks_data if tasks_data is not None else [] # Garante lista


    # 3. BUSCA DE TODOS OS PERFIS DE CS (PARA RANKING)
    all_cs_profiles = query_db("SELECT usuario, nome, cargo, perfil_acesso FROM perfil_usuario")
    all_cs_profiles = all_cs_profiles if all_cs_profiles is not None else [] # Garante lista

    cs_metrics = {p['usuario']: {
        'email': p['usuario'], 'nome': p['nome'] or p['usuario'], 'cargo': p['cargo'] or 'N/A',
        'perfil': p['perfil_acesso'] or 'Nenhum',
        'impl_total': 0, 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0,
        'impl_novas': 0, 'impl_futuras': 0, # Adicionado 'impl_futuras'
        'tma_sum': 0, 'progresso_medio': 0, 'tma_medio': 'N/A', 'motivos_parada': {},
        'prod_tags': {'Ação interna': 0, 'Reunião': 0}, 
        'parada_dias_total': 0, 'impl_atrasadas_count': 0 
    } for p in all_cs_profiles if p and p.get('usuario')} 

    for row in tasks_data:
        cs_email_task = row.get('usuario_cs')
        if cs_email_task in cs_metrics:
            tag = row.get('tag')
            if tag in cs_metrics[cs_email_task]['prod_tags']:
                cs_metrics[cs_email_task]['prod_tags'][tag] += 1

    # 4. PROCESSAMENTO E CÁLCULO DE MÉTRICAS GLOBAIS
    total_impl_global = 0
    total_finalizadas = 0
    total_andamento_global = 0
    total_paradas = 0
    total_novas_global = 0
    total_futuras_global = 0 # Adicionado
    total_sem_previsao = 0 # Adicionado
    total_atrasadas_status = 0 
    tma_dias_sum = 0
    motivos_parada_global = {}
    implantacoes_paradas_detalhadas = []
    
    # --- INÍCIO DA CORREÇÃO (Gráfico MRR) ---
    # Inicializa o dicionário do gráfico usando as nomenclaturas exatas de constants.py
    chart_data_nivel_receita = {label: 0 for label in NIVEIS_RECEITA}
    # Adiciona uma categoria para implantações sem nível definido
    chart_data_nivel_receita["Não Definido"] = 0 
    # --- FIM DA CORREÇÃO ---
    
    chart_data_ranking_periodo = {i: 0 for i in range(1, 13)} # (Mês: Contagem)
    
    agora = datetime.now() 
    ano_corrente = agora.year

    for impl in impl_list:
        if not impl or not isinstance(impl, dict): continue

        impl_id = impl.get('id')
        cs_email_impl = impl.get('usuario_cs')
        status = impl.get('status')
        
        # --- INÍCIO DA CORREÇÃO (Gráfico MRR) ---
        # Pega a string da categoria (ex: "Prata (...)") direto do banco
        nivel_selecionado = impl.get('nivel_receita') 
        
        if nivel_selecionado and nivel_selecionado in chart_data_nivel_receita:
            # Incrementa a contagem para a nomenclatura exata
            chart_data_nivel_receita[nivel_selecionado] += 1
        else:
            # Agrupa todos os nulos ou vazios em "Não Definido"
            chart_data_nivel_receita["Não Definido"] += 1
        # --- FIM DA CORREÇÃO ---

        # Lógica para implantações sem previsão (baseado no status 'futura' e data)
        if status == 'futura' and not impl.get('data_inicio_previsto'):
            total_sem_previsao += 1

        if not impl_id or not cs_email_impl or cs_email_impl not in cs_metrics:
            continue

        total_impl_global += 1 
        metrics = cs_metrics[cs_email_impl]
        metrics['impl_total'] += 1

        tma_dias = None
        if status == 'finalizada':
            dt_criacao = impl.get('data_criacao')
            dt_finalizacao = impl.get('data_finalizacao')
            
            dt_criacao_datetime = None
            dt_finalizacao_datetime = None
            
            # (Lógica de parse de data_criacao)
            if isinstance(dt_criacao, str):
                try: dt_criacao_datetime = datetime.fromisoformat(dt_criacao)
                except ValueError: pass
            elif isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime): 
                dt_criacao_datetime = datetime.combine(dt_criacao, datetime.min.time())
            elif isinstance(dt_criacao, datetime):
                dt_criacao_datetime = dt_criacao

            # (Lógica de parse de data_finalizacao)
            if isinstance(dt_finalizacao, str):
                try: dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao)
                except ValueError: pass
            elif isinstance(dt_finalizacao, date) and not isinstance(dt_finalizacao, datetime): 
                dt_finalizacao_datetime = datetime.combine(dt_finalizacao, datetime.min.time())
            elif isinstance(dt_finalizacao, datetime):
                dt_finalizacao_datetime = dt_finalizacao

            if dt_criacao_datetime and dt_finalizacao_datetime:
                criacao_naive = dt_criacao_datetime.replace(tzinfo=None) if dt_criacao_datetime.tzinfo else dt_criacao_datetime
                final_naive = dt_finalizacao_datetime.replace(tzinfo=None) if dt_finalizacao_datetime.tzinfo else dt_finalizacao_datetime
                try:
                    delta = final_naive - criacao_naive
                    tma_dias = max(0, delta.days)
                except TypeError: pass 

            total_finalizadas += 1
            metrics['impl_finalizadas'] += 1
            if tma_dias is not None:
                tma_dias_sum += tma_dias
                metrics['tma_sum'] += tma_dias

            # NOVO: Adiciona ao gráfico de Ranking por Período
            if dt_finalizacao_datetime and dt_finalizacao_datetime.year == ano_corrente:
                chart_data_ranking_periodo[dt_finalizacao_datetime.month] += 1

        elif status == 'parada':
            total_paradas += 1
            metrics['impl_paradas'] += 1
            parada_dias = calculate_time_in_status(impl_id, 'parada')
            if parada_dias is not None:
                metrics['parada_dias_total'] += parada_dias

            motivo = impl.get('motivo_parada') or 'Motivo Não Especificado'
            motivos_parada_global[motivo] = motivos_parada_global.get(motivo, 0) + 1
            metrics['motivos_parada'][motivo] = metrics['motivos_parada'].get(motivo, 0) + 1

            implantacoes_paradas_detalhadas.append({
                'id': impl_id,
                'nome_empresa': impl.get('nome_empresa'),
                'motivo_parada': motivo,
                'dias_parada': parada_dias if parada_dias is not None else 0,
                'cs_nome': metrics.get('nome', cs_email_impl)
            })
        
        elif status == 'nova':
            total_novas_global += 1
            metrics['impl_novas'] += 1
            
        elif status == 'futura': # Adicionado
            total_futuras_global += 1
            metrics['impl_futuras'] += 1

        elif status == 'andamento':
            total_andamento_global += 1
            metrics['impl_andamento'] += 1

            data_inicio_obj = impl.get('data_inicio_efetivo') 
            dias_passados = 0
            
            # (Lógica de parse de data_inicio_efetivo)
            data_inicio_datetime = None
            if isinstance(data_inicio_obj, str):
                try: data_inicio_datetime = datetime.fromisoformat(data_inicio_obj)
                except ValueError: 
                    try: data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d')
                    except ValueError: pass
            elif isinstance(data_inicio_obj, date) and not isinstance(data_inicio_obj, datetime): 
                data_inicio_datetime = datetime.combine(data_inicio_obj, datetime.min.time())
            elif isinstance(data_inicio_obj, datetime):
                data_inicio_datetime = data_inicio_obj
            
            if data_inicio_datetime:
                agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
                inicio_naive = data_inicio_datetime.replace(tzinfo=None) if data_inicio_datetime.tzinfo else data_inicio_datetime
                try:
                    dias_passados_delta = agora_naive - inicio_naive
                    dias_passados = dias_passados_delta.days if dias_passados_delta.days >= 0 else 0
                except TypeError: dias_passados = -1 

            if dias_passados > 25:
                total_atrasadas_status += 1
                metrics['impl_atrasadas_count'] += 1 

    # 5. FINALIZAÇÃO DAS MÉTRICAS DE CS (para Ranking)
    final_cs_metrics_list = []
    for email, metrics_data in cs_metrics.items():
        # Inclui CS mesmo se não tiver implantações (para filtros)
        # if metrics_data['impl_total'] > 0 or not target_cs_email: 
            if metrics_data['impl_finalizadas'] > 0 and metrics_data['tma_sum'] is not None:
                metrics_data['tma_medio'] = round(metrics_data['tma_sum'] / metrics_data['impl_finalizadas'], 1)
            else:
                metrics_data['tma_medio'] = 'N/A'
            metrics_data['progresso_medio'] = 0 # (Placeholder, não calculado)
            final_cs_metrics_list.append(metrics_data)

    # 6. MONTAGEM DOS DADOS DE KPI (kpi_cards)
    global_metrics = {
        'total_clientes': total_impl_global, 
        'total_finalizadas': total_finalizadas,
        'total_andamento': total_andamento_global,
        'total_paradas': total_paradas,
        'total_novas': total_novas_global,
        'total_futuras': total_futuras_global,
        'total_sem_previsao': total_sem_previsao,
        'total_atrasadas': total_atrasadas_status, 
        'media_tma': round(tma_dias_sum / total_finalizadas, 1) if total_finalizadas > 0 and tma_dias_sum is not None else 0, 
        'motivos_parada': motivos_parada_global
    }

    # 7. MONTAGEM DOS DADOS DE GRÁFICO (chart_data)
    
    # Gráfico 1: Status Clientes
    status_data = {
        'Novas': total_novas_global,
        'Em Andamento': total_andamento_global,
        'Finalizadas': total_finalizadas,
        'Paradas': total_paradas,
        'Futuras': total_futuras_global,
        'Atrasadas': total_atrasadas_status
    }
    
    # Gráfico 2: Nível Receita (MRR)
    # (Agora é populado pela lógica corrigida acima)
    
    # Gráfico 3: Ranking Colaborador
    ranking_colab_data = sorted(
        [m for m in final_cs_metrics_list if m.get('impl_total', 0) > 0], 
        key=lambda x: x['impl_total'], 
        reverse=True
    )
    
    # Gráfico 4: Ranking Período
    meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    
    
    chart_data = {
        'status_clientes': {
            'labels': list(status_data.keys()),
            'data': list(status_data.values())
        },
        'nivel_receita': {
            'labels': list(chart_data_nivel_receita.keys()), 
            'data': list(chart_data_nivel_receita.values())
        },
        'ranking_colaborador': {
            'labels': [cs['nome'] for cs in ranking_colab_data], 
            'data': [cs['impl_total'] for cs in ranking_colab_data]
        },
        'ranking_periodo': {
            'labels': meses_nomes, 
            'data': [chart_data_ranking_periodo.get(i, 0) for i in range(1, 13)]
        }
    }

    # 8. RETORNO (NOVO FORMATO DE DICIONÁRIO ÚNICO)
    return {
        'kpi_cards': global_metrics,
        'implantacoes_lista_detalhada': impl_list,
        'chart_data': chart_data,
        
        'implantacoes_paradas_lista': implantacoes_paradas_detalhadas,
        
        # (Outros dados que podem ser úteis, mas não são usados pelo template)
        'cs_metrics_list': final_cs_metrics_list 
    }


# --- FUNÇÃO PARA GAMIFICAÇÃO ---
def calcular_pontuacao_gamificacao(usuario_cs, mes, ano):
    """Calcula a pontuação da gamificação para um usuário em um mês/ano específico."""

    # 1. Buscar Perfil e Métricas Manuais
    perfil = query_db("SELECT cargo FROM perfil_usuario WHERE usuario = %s", (usuario_cs,), one=True)
    if not perfil:
        raise ValueError(f"Perfil de usuário não encontrado para {usuario_cs}")
    cargo = perfil.get('cargo', 'N/A') 

    metricas_manuais = query_db(
        "SELECT * FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
        (usuario_cs, mes, ano), one=True
    )
    metricas_manuais = dict(metricas_manuais) if metricas_manuais else {}

    # (O restante da função de gamificação permanece inalterado)
    # ... 
    
    metricas_manuais.setdefault('nota_qualidade', None)
    metricas_manuais.setdefault('assiduidade', None)
    metricas_manuais.setdefault('planos_sucesso_perc', None)
    metricas_manuais.setdefault('satisfacao_processo', None)
    metricas_manuais.setdefault('reclamacoes', 0)
    metricas_manuais.setdefault('perda_prazo', 0)
    metricas_manuais.setdefault('nao_preenchimento', 0)
    metricas_manuais.setdefault('elogios', 0)
    metricas_manuais.setdefault('recomendacoes', 0)
    metricas_manuais.setdefault('certificacoes', 0)
    metricas_manuais.setdefault('treinamentos_pacto_part', 0)
    metricas_manuais.setdefault('treinamentos_pacto_aplic', 0)
    metricas_manuais.setdefault('reunioes_presenciais', 0)
    metricas_manuais.setdefault('cancelamentos_resp', 0)
    metricas_manuais.setdefault('nao_envolvimento', 0)
    metricas_manuais.setdefault('desc_incompreensivel', 0)
    metricas_manuais.setdefault('hora_extra', 0)
    metricas_manuais.setdefault('perda_sla_grupo', 0)
    metricas_manuais.setdefault('finalizacao_incompleta', 0)


    # 2. Definir Período
    try:
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        ultimo_dia = date(ano, mes, ultimo_dia_mes)
        fim_ultimo_dia = datetime.combine(ultimo_dia, datetime.max.time())
        dias_no_mes = ultimo_dia_mes
    except ValueError:
        raise ValueError(f"Mês ({mes}) ou Ano ({ano}) inválido.")

    primeiro_dia_str = primeiro_dia.isoformat()
    fim_ultimo_dia_str = fim_ultimo_dia.isoformat()


    # 3. Buscar Dados Automáticos do Período
    # a) Implantações Finalizadas e TMA
    impl_finalizadas = query_db(
        """
        SELECT data_criacao, data_finalizacao FROM implantacoes
        WHERE usuario_cs = %s AND status = 'finalizada'
        AND data_finalizacao >= %s AND data_finalizacao <= %s
        """,
        (usuario_cs, primeiro_dia_str, fim_ultimo_dia_str) # Passando strings
    )
    impl_finalizadas = impl_finalizadas if impl_finalizadas is not None else [] # Garante lista
    count_finalizadas = len(impl_finalizadas)
    tma_total_dias = 0
    if count_finalizadas > 0:
        for impl in impl_finalizadas:
            if not isinstance(impl, dict): continue
            dt_criacao = impl.get('data_criacao')
            dt_finalizacao = impl.get('data_finalizacao')
            
            dt_criacao_datetime = None
            dt_finalizacao_datetime = None

            if isinstance(dt_criacao, str):
                try: dt_criacao_datetime = datetime.fromisoformat(dt_criacao)
                except ValueError: pass
            elif isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime): 
                dt_criacao_datetime = datetime.combine(dt_criacao, datetime.min.time())
            elif isinstance(dt_criacao, datetime):
                dt_criacao_datetime = dt_criacao

            if isinstance(dt_finalizacao, str):
                try: dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao)
                except ValueError: pass
            elif isinstance(dt_finalizacao, date) and not isinstance(dt_finalizacao, datetime): 
                dt_finalizacao_datetime = datetime.combine(dt_finalizacao, datetime.min.time())
            elif isinstance(dt_finalizacao, datetime):
                dt_finalizacao_datetime = dt_finalizacao

            if dt_criacao_datetime and dt_finalizacao_datetime:
                if isinstance(dt_criacao, datetime) and isinstance(dt_finalizacao, datetime):
                    criacao_naive = dt_criacao_datetime.replace(tzinfo=None) if dt_criacao_datetime.tzinfo else dt_criacao_datetime
                    final_naive = dt_finalizacao_datetime.replace(tzinfo=None) if dt_finalizacao_datetime.tzinfo else dt_finalizacao_datetime
                    try:
                        delta = final_naive - criacao_naive
                        tma_total_dias += max(0, delta.days)
                    except TypeError: pass 
        tma_medio = round(tma_total_dias / count_finalizadas, 1) if tma_total_dias is not None else None
    else:
        tma_medio = None 

    # b) Implantações Iniciadas
    impl_iniciadas = query_db(
        "SELECT COUNT(*) as total FROM implantacoes WHERE usuario_cs = %s AND data_inicio_efetivo >= %s AND data_inicio_efetivo <= %s",
        (usuario_cs, primeiro_dia_str, fim_ultimo_dia_str), one=True # Passando strings
    )
    count_iniciadas = impl_iniciadas.get('total', 0) if impl_iniciadas else 0

    # c) Tarefas Concluídas (para média diária)
    tarefas_concluidas = query_db(
        """
        SELECT tag, COUNT(*) as total FROM tarefas
        WHERE implantacao_id IN (SELECT id FROM implantacoes WHERE usuario_cs = %s)
        AND concluida = TRUE AND tag IN ('Ação interna', 'Reunião')
        AND data_conclusao >= %s AND data_conclusao <= %s
        GROUP BY tag
        """,
        (usuario_cs, primeiro_dia_str, fim_ultimo_dia_str) # Passando strings
    )
    tarefas_concluidas = tarefas_concluidas if tarefas_concluidas is not None else [] # Garante lista
    count_acao_interna = 0
    count_reuniao = 0
    for row in tarefas_concluidas:
        if isinstance(row, dict): # Garante que row é dict
            if row.get('tag') == 'Ação interna': count_acao_interna = row.get('total', 0)
            elif row.get('tag') == 'Reunião': count_reuniao = row.get('total', 0)

    media_reunioes_dia = round(count_reuniao / dias_no_mes, 2) if dias_no_mes > 0 else 0
    media_acoes_dia = round(count_acao_interna / dias_no_mes, 2) if dias_no_mes > 0 else 0


    # 4. Verificar Elegibilidade (usando métricas manuais e automáticas)
    elegivel = True
    motivo_inelegibilidade = []

    min_nota_qualidade = 80
    min_assiduidade = 85
    min_reunioes_dia_criterio = 3 
    min_planos_sucesso = 75
    max_reclamacoes = 1
    max_perda_prazo = 2
    max_nao_preenchimento = 2

    min_processos_concluidos = 0
    if cargo == 'Júnior': min_processos_concluidos = 4
    elif cargo == 'Pleno': min_processos_concluidos = 5
    elif cargo == 'Sênior': min_processos_concluidos = 5

    nq = metricas_manuais.get('nota_qualidade')
    if nq is None: elegivel = False; motivo_inelegibilidade.append("Nota Qualidade não informada")
    elif nq < min_nota_qualidade: elegivel = False; motivo_inelegibilidade.append(f"Nota Qualidade < {min_nota_qualidade}%")

    assid = metricas_manuais.get('assiduidade')
    if assid is None: elegivel = False; motivo_inelegibilidade.append("Assiduidade não informada")
    elif assid < min_assiduidade: elegivel = False; motivo_inelegibilidade.append(f"Assiduidade < {min_assiduidade}%")

    psp = metricas_manuais.get('planos_sucesso_perc')
    if psp is None: elegivel = False; motivo_inelegibilidade.append("Planos Sucesso % não informado")
    elif psp < min_planos_sucesso: elegivel = False; motivo_inelegibilidade.append(f"Planos Sucesso < {min_planos_sucesso}%")

    if count_finalizadas < min_processos_concluidos:
        elegivel = False
        motivo_inelegibilidade.append(f"Impl. Finalizadas ({count_finalizadas}) < {min_processos_concluidos} ({cargo})")

    if metricas_manuais.get('reclamacoes', 0) >= max_reclamacoes + 1:
        elegivel = False; motivo_inelegibilidade.append(f"Reclamações >= {max_reclamacoes + 1}")
    if metricas_manuais.get('perda_prazo', 0) >= max_perda_prazo + 1:
        elegivel = False; motivo_inelegibilidade.append(f"Perda Prazo >= {max_perda_prazo + 1}")
    if metricas_manuais.get('nao_preenchimento', 0) >= max_nao_preenchimento + 1:
        elegivel = False; motivo_inelegibilidade.append(f"Não Preenchimento >= {max_nao_preenchimento + 1}")

    if nq is not None and nq < 80:
        elegivel = False; motivo_inelegibilidade.append("Nota Qualidade < 80% (Eliminado)")

    # 5. Calcular Pontuação (APENAS SE ELEGÍVEL)
    pontos = 0
    detalhamento_pontos = {} # Para mostrar o breakdown

    if elegivel:
        satisfacao = metricas_manuais.get('satisfacao_processo')
        pts_satisfacao = 0
        if satisfacao is not None:
            if satisfacao >= 100: pts_satisfacao = 25
            elif satisfacao >= 95: pts_satisfacao = 17
            elif satisfacao >= 90: pts_satisfacao = 15
            elif satisfacao >= 85: pts_satisfacao = 14
            elif satisfacao >= 80: pts_satisfacao = 12
        pontos += pts_satisfacao
        detalhamento_pontos['Satisfação Processo'] = f"{pts_satisfacao} pts ({satisfacao if satisfacao is not None else 'N/A'}%)"

        pts_assiduidade = 0
        if assid is not None:
            if assid >= 100: pts_assiduidade = 30
            elif assid >= 98: pts_assiduidade = 20
            elif assid >= 95: pts_assiduidade = 15
        pontos += pts_assiduidade
        detalhamento_pontos['Assiduidade'] = f"{pts_assiduidade} pts ({assid if assid is not None else 'N/A'}%)"

        pts_tma = 0
        tma_display = 'N/A'
        if tma_medio is not None:
            tma_display = f"{tma_medio:.1f} dias"
            if tma_medio <= 30: pts_tma = 45
            elif tma_medio <= 35: pts_tma = 32
            elif tma_medio <= 40: pts_tma = 24
            elif tma_medio <= 45: pts_tma = 16
            else: pts_tma = 8 
        pontos += pts_tma
        detalhamento_pontos['TMA Médio'] = f"{pts_tma} pts ({tma_display})"

        pts_reunioes_dia = 0
        if media_reunioes_dia >= 5: pts_reunioes_dia = 40
        elif media_reunioes_dia >= 4: pts_reunioes_dia = 35
        elif media_reunioes_dia >= 3: pts_reunioes_dia = 25
        elif media_reunioes_dia >= 2: pts_reunioes_dia = 10
        pontos += pts_reunioes_dia
        detalhamento_pontos['Média Reuniões/Dia'] = f"{pts_reunioes_dia} pts ({media_reunioes_dia:.2f})"

        pts_acoes_dia = 0
        if media_acoes_dia >= 7: pts_acoes_dia = 20
        elif media_acoes_dia >= 6: pts_acoes_dia = 15
        elif media_acoes_dia >= 5: pts_acoes_dia = 10
        elif media_acoes_dia >= 4: pts_acoes_dia = 5
        elif media_acoes_dia >= 3: pts_acoes_dia = 3
        pontos += pts_acoes_dia
        detalhamento_pontos['Média Ações/Dia'] = f"{pts_acoes_dia} pts ({media_acoes_dia:.2f})"

        pts_planos = 0
        if psp is not None:
            if psp >= 100: pts_planos = 45
            elif psp >= 95: pts_planos = 35
            elif psp >= 90: pts_planos = 30
            elif psp >= 85: pts_planos = 20
            elif psp >= 80: pts_planos = 10
        pontos += pts_planos
        detalhamento_pontos['Planos Sucesso'] = f"{pts_planos} pts ({psp if psp is not None else 'N/A'}%)"

        pts_iniciadas = 0
        if count_iniciadas >= 10: pts_iniciadas = 45
        elif count_iniciadas >= 9: pts_iniciadas = 32
        elif count_iniciadas >= 8: pts_iniciadas = 24
        elif count_iniciadas >= 7: pts_iniciadas = 16
        elif count_iniciadas >= 6: pts_iniciadas = 8
        pontos += pts_iniciadas
        detalhamento_pontos['Impl. Iniciadas'] = f"{pts_iniciadas} pts ({count_iniciadas})"

        pts_qualidade = 0
        if nq is not None:
            if nq >= 100: pts_qualidade = 55
            elif nq >= 95: pts_qualidade = 40
            elif nq >= 90: pts_qualidade = 30
            elif nq >= 85: pts_qualidade = 15
            elif nq >= 80: pts_qualidade = 0
        pontos += pts_qualidade
        detalhamento_pontos['Nota Qualidade'] = f"{pts_qualidade} pts ({nq if nq is not None else 'N/A'}%)"

        pts_bonus = 0
        elogios = metricas_manuais.get('elogios', 0)
        pts_bonus_elogios = min(elogios, 1) * 15 
        pts_bonus += pts_bonus_elogios
        detalhamento_pontos['Bônus Elogios'] = f"+{pts_bonus_elogios} pts ({elogios} ocorr.)"

        recomendacoes = metricas_manuais.get('recomendacoes', 0)
        pts_bonus_recom = recomendacoes * 1
        pts_bonus += pts_bonus_recom
        detalhamento_pontos['Bônus Recomendações'] = f"+{pts_bonus_recom} pts ({recomendacoes} ocorr.)"

        certificacoes = metricas_manuais.get('certificacoes', 0)
        pts_bonus_cert = min(certificacoes, 1) * 15 
        pts_bonus += pts_bonus_cert
        detalhamento_pontos['Bônus Certificações'] = f"+{pts_bonus_cert} pts ({certificacoes} ocorr.)"

        trein_part = metricas_manuais.get('treinamentos_pacto_part', 0)
        pts_bonus_tpart = trein_part * 15
        pts_bonus += pts_bonus_tpart
        detalhamento_pontos['Bônus Trein. Pacto (Part.)'] = f"+{pts_bonus_tpart} pts ({trein_part} ocorr.)"

        trein_aplic = metricas_manuais.get('treinamentos_pacto_aplic', 0)
        pts_bonus_taplic = trein_aplic * 30
        pts_bonus += pts_bonus_taplic
        detalhamento_pontos['Bônus Trein. Pacto (Aplic.)'] = f"+{pts_bonus_taplic} pts ({trein_aplic} ocorr.)"

        reun_pres = metricas_manuais.get('reunioes_presenciais', 0)
        pts_bonus_reun_pres = 0
        if reun_pres > 10: pts_bonus_reun_pres = 35
        elif reun_pres >= 7: pts_bonus_reun_pres = 30
        elif reun_pres >= 5: pts_bonus_reun_pres = 25
        elif reun_pres >= 3: pts_bonus_reun_pres = 20
        elif reun_pres >= 1: pts_bonus_reun_pres = 15
        pts_bonus += pts_bonus_reun_pres
        detalhamento_pontos['Bônus Reuniões Presenciais'] = f"+{pts_bonus_reun_pres} pts ({reun_pres} ocorr.)"

        pontos += pts_bonus 

        pts_penalidade = 0
        reclamacoes = metricas_manuais.get('reclamacoes', 0)
        pts_pen_reclam = reclamacoes * 50
        pts_penalidade += pts_pen_reclam
        detalhamento_pontos['Penalidade Reclamação'] = f"-{pts_pen_reclam} pts ({reclamacoes} ocorr.)"

        perda_prazo = metricas_manuais.get('perda_prazo', 0)
        pts_pen_prazo = perda_prazo * 10
        pts_penalidade += pts_pen_prazo
        detalhamento_pontos['Penalidade Perda Prazo'] = f"-{pts_pen_prazo} pts ({perda_prazo} ocorr.)"

        desc_incomp = metricas_manuais.get('desc_incompreensivel', 0)
        pts_pen_desc = desc_incomp * 10
        pts_penalidade += pts_pen_desc
        detalhamento_pontos['Penalidade Desc. Incomp.'] = f"-{pts_pen_desc} pts ({desc_incomp} ocorr.)"

        cancel_resp = metricas_manuais.get('cancelamentos_resp', 0)
        pts_pen_cancel = cancel_resp * 100
        pts_penalidade += pts_pen_cancel
        detalhamento_pontos['Penalidade Cancelamento Resp.'] = f"-{pts_pen_cancel} pts ({cancel_resp} ocorr.)"

        nao_envolv = metricas_manuais.get('nao_envolvimento', 0)
        pts_pen_envolv = nao_envolv * 10
        pts_penalidade += pts_pen_envolv
        detalhamento_pontos['Penalidade Não Envolv.'] = f"-{pts_pen_envolv} pts ({nao_envolv} ocorr.)"

        nao_preench = metricas_manuais.get('nao_preenchimento', 0)
        pts_pen_preench = nao_preench * 10
        pts_penalidade += pts_pen_preench
        detalhamento_pontos['Penalidade Não Preench.'] = f"-{pts_pen_preench} pts ({nao_preench} ocorr.)"

        perda_sla = metricas_manuais.get('perda_sla_grupo', 0)
        pts_pen_sla = perda_sla * 5
        pts_penalidade += pts_pen_sla
        detalhamento_pontos['Penalidade SLA Grupo'] = f"-{pts_pen_sla} pts ({perda_sla} ocorr.)"

        final_incomp = metricas_manuais.get('finalizacao_incompleta', 0)
        pts_pen_final = final_incomp * 10
        pts_penalidade += pts_pen_final
        detalhamento_pontos['Penalidade Finaliz. Incomp.'] = f"-{pts_pen_final} pts ({final_incomp} ocorr.)"

        hora_extra = metricas_manuais.get('hora_extra', 0)
        pts_pen_he = hora_extra * 10
        pts_penalidade += pts_pen_he
        detalhamento_pontos['Penalidade Hora Extra'] = f"-{pts_pen_he} pts ({hora_extra} ocorr.)"

        pontos -= pts_penalidade 

    # 6. Preparar Resultado Final
    resultado = {
        'elegivel': elegivel,
        'motivo_inelegibilidade': ", ".join(motivo_inelegibilidade) if motivo_inelegibilidade else None,
        'pontuacao_final': max(0, pontos) if elegivel else 0, 
        'detalhamento_pontos': detalhamento_pontos if elegivel else {},
        'impl_finalizadas_mes': count_finalizadas,
        'tma_medio_mes': f"{tma_medio:.1f}" if tma_medio is not None else 'N/A',
        'impl_iniciadas_mes': count_iniciadas,
        'media_reunioes_dia': media_reunioes_dia,
        'media_acoes_dia': media_acoes_dia,
        'metricas_manuais_usadas': metricas_manuais 
    }

    # 7. Opcional, mas recomendado: Atualizar o DB com os resultados calculados
    try:
        existing_record_id = query_db(
            "SELECT id FROM gamificacao_metricas_mensais WHERE usuario_cs = %s AND mes = %s AND ano = %s",
            (usuario_cs, mes, ano), one=True
        )
        calculated_data = {
            'pontuacao_calculada': resultado['pontuacao_final'],
            'elegivel': resultado['elegivel'],
            'impl_finalizadas_mes': count_finalizadas,
            'tma_medio_mes': tma_medio, # Salva o número ou None
            'impl_iniciadas_mes': count_iniciadas,
            'reunioes_concluidas_dia_media': media_reunioes_dia,
            'acoes_concluidas_dia_media': media_acoes_dia,
            'data_registro': datetime.now()
        }
        if existing_record_id:
            set_clauses_calc = [f"{key} = %s" for key in calculated_data.keys()]
            sql_update_calc = f"""
                UPDATE gamificacao_metricas_mensais
                SET {', '.join(set_clauses_calc)}
                WHERE id = %s
            """
            args_update_calc = list(calculated_data.values()) + [existing_record_id['id']]
            execute_db(sql_update_calc, tuple(args_update_calc))
        else:
            columns_calc = ['usuario_cs', 'mes', 'ano'] + list(calculated_data.keys())
            values_placeholders_calc = ['%s'] * len(columns_calc)
            sql_insert_calc = f"INSERT INTO gamificacao_metricas_mensais ({', '.join(columns_calc)}) VALUES ({', '.join(values_placeholders_calc)})"
            args_insert_calc = [usuario_cs, mes, ano] + list(calculated_data.values())
            execute_db(sql_insert_calc, tuple(args_insert_calc))

    except Exception as db_update_err:
        print(f"AVISO: Falha ao salvar resultados calculados da gamificação para {usuario_cs} ({mes}/{ano}): {db_update_err}")


    return resultado