# project/domain/analytics_service.py
# (Funções movidas de project/services.py)

from flask import current_app
from ..db import query_db
from ..constants import NIVEIS_RECEITA 
from datetime import datetime, timedelta, date 

# --- Funções de Analytics (Lógica de Negócio) ---

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
        return None 

    if impl['status'] == status_target and status_target == 'parada' and impl.get('data_finalizacao'):
        data_inicio_parada_obj = impl['data_finalizacao']
        
        data_inicio_parada_datetime = None
        if isinstance(data_inicio_parada_obj, str):
            try:
                data_inicio_parada_datetime = datetime.fromisoformat(data_inicio_parada_obj.replace('Z', '+00:00'))
            except ValueError:
                try:
                    if '.' in data_inicio_parada_obj:
                         data_inicio_parada_datetime = datetime.strptime(data_inicio_parada_obj, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                         data_inicio_parada_datetime = datetime.strptime(data_inicio_parada_obj, '%Y-%m-%d %H:%M:%S')
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
                return max(0, int(delta.days)) 
            except TypeError as te:
                print(f"AVISO: Erro de tipo ao calcular tempo parado para impl {impl_id}. Verifique timezones. Erro: {te}")
                return None

    return None 


def get_analytics_data(target_cs_email=None, target_status=None, start_date=None, end_date=None, target_tag=None,
                       task_cs_email=None, task_start_date=None, task_end_date=None
                       ):
    """Busca e processa dados de TODA a carteira (ou filtrada) para o módulo Gerencial."""

    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    date_func = "date" if is_sqlite else ""
    agora = datetime.now() 
    ano_corrente = agora.year

    # --- LÓGICA DE FILTRO PRINCIPAL (PARA GRÁFICOS E LISTA DETALHADA) ---
    query_impl = """
        SELECT i.*,
               p.nome as cs_nome, p.cargo as cs_cargo, p.perfil_acesso as cs_perfil
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        WHERE 1=1
    """
    args_impl = []

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
        elif target_status == 'futura': 
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
        else: 
            query_impl += f" AND {date_func}({date_field_to_filter}) <= {date_func}(%s) "
            args_impl.append(end_date)


    query_impl += " ORDER BY i.nome_empresa "

    # 1. BUSCA PRINCIPAL DE IMPLANTAÇÕES (FILTRADAS PELO FILTRO PRINCIPAL)
    impl_list = query_db(query_impl, tuple(args_impl))
    impl_list = impl_list if impl_list is not None else [] 
    
    # 2. BUSCA DE TODOS OS PERFIS DE CS (PARA RANKING E FILTROS)
    all_cs_profiles = query_db("SELECT usuario, nome, cargo, perfil_acesso FROM perfil_usuario")
    all_cs_profiles = all_cs_profiles if all_cs_profiles is not None else [] 

    # --- LÓGICA DO RELATÓRIO DE PRODUTIVIDADE ---

    primeiro_dia_mes = agora.replace(day=1)
    default_task_start_date_str = primeiro_dia_mes.strftime('%Y-%m-%d')
    default_task_end_date_str = agora.strftime('%Y-%m-%d')

    task_start_date_to_query = task_start_date or default_task_start_date_str
    task_end_date_to_query = task_end_date or default_task_end_date_str

    query_tasks = """
        SELECT
            i.usuario_cs,
            COALESCE(p.nome, i.usuario_cs) as cs_nome,
            t.tag,
            COUNT(t.id) as total_concluido
        FROM tarefas t
        JOIN implantacoes i ON t.implantacao_id = i.id
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        WHERE
            t.concluida = TRUE 
            AND t.tag IN ('Ação interna', 'Reunião')
            AND t.data_conclusao IS NOT NULL
    """
    args_tasks = []

    if task_cs_email:
        query_tasks += " AND i.usuario_cs = %s "
        args_tasks.append(task_cs_email)

    if task_start_date_to_query:
        query_tasks += f" AND {date_func}(t.data_conclusao) >= {date_func}(%s) "
        args_tasks.append(task_start_date_to_query)
        
    if task_end_date_to_query:
        if not is_sqlite:
            try:
                end_date_obj_task = datetime.strptime(task_end_date_to_query, '%Y-%m-%d').date()
                next_day_task = end_date_obj_task + timedelta(days=1)
                query_tasks += f" AND t.data_conclusao < %s "
                args_tasks.append(next_day_task.strftime('%Y-%m-%d'))
            except ValueError:
                 query_tasks += f" AND {date_func}(t.data_conclusao) <= {date_func}(%s) "
                 args_tasks.append(task_end_date_to_query)
        else:
             query_tasks += f" AND {date_func}(t.data_conclusao) <= {date_func}(%s) "
             args_tasks.append(task_end_date_to_query)

    query_tasks += " GROUP BY i.usuario_cs, p.nome, t.tag ORDER BY cs_nome, t.tag "

    # 3. BUSCA DE TAREFAS (FILTRADAS PELO NOVO FILTRO DE TAREFAS)
    tasks_summary_raw = query_db(query_tasks, tuple(args_tasks))
    tasks_summary_raw = tasks_summary_raw if tasks_summary_raw is not None else []

    task_summary_processed = {}
    for row in tasks_summary_raw:
        if not row or not isinstance(row, dict): continue
        email = row.get('usuario_cs')
        if not email: continue
        
        if email not in task_summary_processed:
            task_summary_processed[email] = {
                'usuario_cs': email,
                'cs_nome': row.get('cs_nome', email),
                'Ação interna': 0,
                'Reunião': 0
            }
        
        tag = row.get('tag')
        total = row.get('total_concluido', 0)
        if tag == 'Ação interna':
            task_summary_processed[email]['Ação interna'] = total
        elif tag == 'Reunião':
            task_summary_processed[email]['Reunião'] = total
            
    task_summary_list = list(task_summary_processed.values())
    
    # 4. PROCESSAMENTO E CÁLCULO DE MÉTRICAS GLOBAIS (Baseado na busca 1)
    
    cs_metrics_ranking = {p['usuario']: {
        'email': p['usuario'], 'nome': p['nome'] or p['usuario'], 'cargo': p['cargo'] or 'N/A',
        'perfil': p['perfil_acesso'] or 'Nenhum',
        'impl_total_ranking': 0, 'tma_sum_ranking': 0, 'impl_finalizadas_ranking': 0,
        'tma_medio_ranking': 'N/A'
    } for p in all_cs_profiles if p and p.get('usuario')} 
    
    query_impl_ano = """
        SELECT i.usuario_cs, i.data_finalizacao, i.data_criacao
        FROM implantacoes i
        WHERE i.status = 'finalizada'
    """
    args_impl_ano = []
    
    if is_sqlite:
         query_impl_ano += " AND strftime('%Y', i.data_finalizacao) = %s "
         args_impl_ano.append(str(ano_corrente))
    else: # Postgres
         query_impl_ano += " AND EXTRACT(YEAR FROM i.data_finalizacao) = %s "
         args_impl_ano.append(ano_corrente)
         
    if target_cs_email:
        query_impl_ano += " AND i.usuario_cs = %s "
        args_impl_ano.append(target_cs_email)
        
    impl_finalizadas_ano_corrente = query_db(query_impl_ano, tuple(args_impl_ano))
    impl_finalizadas_ano_corrente = impl_finalizadas_ano_corrente if impl_finalizadas_ano_corrente is not None else []
    
    chart_data_ranking_periodo = {i: 0 for i in range(1, 13)} 

    for impl in impl_finalizadas_ano_corrente:
        if not impl or not isinstance(impl, dict): continue
        cs_email_impl = impl.get('usuario_cs')
        dt_finalizacao = impl.get('data_finalizacao')
        dt_criacao = impl.get('data_criacao')
        
        dt_finalizacao_datetime = None
        if isinstance(dt_finalizacao, str):
            try: dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao.replace('Z', '+00:00'))
            except ValueError: 
                try: 
                    if '.' in dt_finalizacao: dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, '%Y-%m-%d %H:%M:%S.%f')
                    else: dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, '%Y-%m-%d %H:%M:%S')
                except ValueError: pass
        elif isinstance(dt_finalizacao, date) and not isinstance(dt_finalizacao, datetime): 
            dt_finalizacao_datetime = datetime.combine(dt_finalizacao, datetime.min.time())
        elif isinstance(dt_finalizacao, datetime):
            dt_finalizacao_datetime = dt_finalizacao
        
        if dt_finalizacao_datetime and dt_finalizacao_datetime.year == ano_corrente:
            chart_data_ranking_periodo[dt_finalizacao_datetime.month] += 1
            

    # 5. PROCESSAMENTO DA LISTA FILTRADA (impl_list)
    total_impl_global = 0
    total_finalizadas = 0
    total_andamento_global = 0
    total_paradas = 0
    total_novas_global = 0
    total_futuras_global = 0 
    total_atrasadas_status = 0 
    tma_dias_sum = 0
    implantacoes_paradas_detalhadas = []
    
    chart_data_nivel_receita = {label: 0 for label in NIVEIS_RECEITA}
    chart_data_nivel_receita["Não Definido"] = 0 
    
    chart_data_ranking_colab = {}

    for impl in impl_list:
        if not impl or not isinstance(impl, dict): continue

        impl_id = impl.get('id')
        cs_email_impl = impl.get('usuario_cs')
        cs_nome_impl = impl.get('cs_nome', cs_email_impl)
        status = impl.get('status')
        
        nivel_selecionado = impl.get('nivel_receita') 
        if nivel_selecionado and nivel_selecionado in chart_data_nivel_receita:
            chart_data_nivel_receita[nivel_selecionado] += 1
        else:
            chart_data_nivel_receita["Não Definido"] += 1

        if cs_nome_impl:
            chart_data_ranking_colab[cs_nome_impl] = chart_data_ranking_colab.get(cs_nome_impl, 0) + 1

        total_impl_global += 1 

        tma_dias = None
        if status == 'finalizada':
            dt_criacao = impl.get('data_criacao')
            dt_finalizacao = impl.get('data_finalizacao')
            
            dt_criacao_datetime = None
            dt_finalizacao_datetime = None
            
            if isinstance(dt_criacao, str):
                try: dt_criacao_datetime = datetime.fromisoformat(dt_criacao.replace('Z', '+00:00'))
                except ValueError: 
                    try: 
                        if '.' in dt_criacao: dt_criacao_datetime = datetime.strptime(dt_criacao, '%Y-%m-%d %H:%M:%S.%f')
                        else: dt_criacao_datetime = datetime.strptime(dt_criacao, '%Y-%m-%d %H:%M:%S')
                    except ValueError: pass
            elif isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime): 
                dt_criacao_datetime = datetime.combine(dt_criacao, datetime.min.time())
            elif isinstance(dt_criacao, datetime):
                dt_criacao_datetime = dt_criacao

            if isinstance(dt_finalizacao, str):
                try: dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao.replace('Z', '+00:00'))
                except ValueError: 
                    try: 
                        if '.' in dt_finalizacao: dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, '%Y-%m-%d %H:%M:%S.%f')
                        else: dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, '%Y-%m-%d %H:%M:%S')
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
            if tma_dias is not None:
                tma_dias_sum += tma_dias

        elif status == 'parada':
            total_paradas += 1
            parada_dias = calculate_time_in_status(impl_id, 'parada')
            motivo = impl.get('motivo_parada') or 'Motivo Não Especificado'
            implantacoes_paradas_detalhadas.append({
                'id': impl_id,
                'nome_empresa': impl.get('nome_empresa'),
                'motivo_parada': motivo,
                'dias_parada': parada_dias if parada_dias is not None else 0,
                'cs_nome': cs_nome_impl
            })
        
        elif status == 'nova':
            total_novas_global += 1
            
        elif status == 'futura': 
            total_futuras_global += 1

        elif status == 'andamento':
            total_andamento_global += 1

            data_inicio_obj = impl.get('data_inicio_efetivo') 
            dias_passados = 0
            
            data_inicio_datetime = None
            if isinstance(data_inicio_obj, str):
                try: data_inicio_datetime = datetime.fromisoformat(data_inicio_obj.replace('Z', '+00:00'))
                except ValueError: 
                    try: 
                        if '.' in data_inicio_obj: data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d %H:%M:%S.%f')
                        else: data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d %H:%M:%S')
                    except ValueError: 
                        try: data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d')
                        except ValueError: pass
            elif isinstance(data_inicio_obj, date) and not isinstance(data_inicio_obj, datetime): 
                data_inicio_datetime = datetime.combine(data_inicio_obj, datetime.min.time())
            elif isinstance(data_inicio_obj, datetime):
                data_inicio_datetime = data_inicio_datetime
            
            if data_inicio_datetime:
                agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
                inicio_naive = data_inicio_datetime.replace(tzinfo=None) if data_inicio_datetime.tzinfo else data_inicio_datetime
                try:
                    dias_passados_delta = agora_naive - inicio_naive
                    dias_passados = dias_passados_delta.days if dias_passados_delta.days >= 0 else 0
                except TypeError: dias_passados = -1 

            if dias_passados > 25:
                total_atrasadas_status += 1

    # 6. MONTAGEM DOS DADOS DE KPI (kpi_cards)
    global_metrics = {
        'total_clientes': total_impl_global, 
        'total_finalizadas': total_finalizadas,
        'total_andamento': total_andamento_global,
        'total_paradas': total_paradas,
        'total_novas': total_novas_global,
        'total_futuras': total_futuras_global,
        'total_sem_previsao': total_novas_global, # Corrigido
        'total_atrasadas': total_atrasadas_status, 
        'media_tma': round(tma_dias_sum / total_finalizadas, 1) if total_finalizadas > 0 and tma_dias_sum is not None else 0, 
    }
    
    status_data = {
        'Novas': total_novas_global,
        'Em Andamento': total_andamento_global,
        'Finalizadas': total_finalizadas,
        'Paradas': total_paradas,
        'Futuras': total_futuras_global,
        'Atrasadas': total_atrasadas_status
    }
    
    ranking_colab_data = sorted(
        chart_data_ranking_colab.items(), 
        key=lambda item: item[1], 
        reverse=True
    )
    
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
            'labels': [item[0] for item in ranking_colab_data], 
            'data': [item[1] for item in ranking_colab_data]  
        },
        'ranking_periodo': {
            'labels': meses_nomes, 
            'data': [chart_data_ranking_periodo.get(i, 0) for i in range(1, 13)]
        }
    }

    return {
        'kpi_cards': global_metrics,
        'implantacoes_lista_detalhada': impl_list,
        'chart_data': chart_data,
        'implantacoes_paradas_lista': implantacoes_paradas_detalhadas,
        'task_summary_data': task_summary_list,
        'default_task_start_date': default_task_start_date_str,
        'default_task_end_date': default_task_end_date_str,
    }