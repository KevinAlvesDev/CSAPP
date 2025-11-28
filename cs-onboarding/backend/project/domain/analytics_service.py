

from flask import current_app
from ..db import query_db
from ..constants import NIVEIS_RECEITA 
from datetime import datetime, timedelta, date 

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


def _format_date_for_query(val, is_end_date=False, is_sqlite=False):
    if not val:
        return None, None

    if isinstance(val, datetime):
        date_obj = val.date()
        date_str = date_obj.strftime('%Y-%m-%d')
    elif isinstance(val, date):
        date_obj = val
        date_str = val.strftime('%Y-%m-%d')
    else:
        date_str = str(val)
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None, None

    if is_end_date and not is_sqlite:
        return '<', (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
    return '<=' if is_end_date else '>=', date_str

def date_col_expr(col: str) -> str:
    """Retorna expressão SQL para extrair a porção de data da coluna conforme o banco."""
    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    return f"date({col})" if is_sqlite else f"CAST({col} AS DATE)"

def date_param_expr() -> str:
    """Retorna expressão SQL para parâmetro de data conforme o banco."""
    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    return "date(%s)" if is_sqlite else "CAST(%s AS DATE)"

def get_analytics_data(target_cs_email=None, target_status=None, start_date=None, end_date=None, target_tag=None,
                       task_cs_email=None, task_start_date=None, task_end_date=None,
                       sort_impl_date=None
                       ):
    """Busca e processa dados de TODA a carteira (ou filtrada) para o módulo Gerencial."""

    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    date_func = "date" if is_sqlite else ""
    agora = datetime.now() 
    ano_corrente = agora.year

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
            else:             
                query_impl += " AND i.status = 'andamento' AND i.data_inicio_efetivo IS NOT NULL AND i.data_inicio_efetivo <= NOW() - INTERVAL '26 days' " 
        elif target_status == 'nova':
            query_impl += " AND i.status = 'nova' "
        elif target_status == 'futura': 
            query_impl += " AND i.status = 'futura' "
        elif target_status == 'cancelada':
             query_impl += " AND i.status = 'cancelada' "
        else:
            query_impl += " AND i.status = %s "
            args_impl.append(target_status)

    date_field_to_filter = "i.data_finalizacao" if target_status in ['finalizada', 'cancelada'] else "i.data_criacao"

    start_op, start_date_val = _format_date_for_query(start_date, is_sqlite=is_sqlite)
    if start_op:
        query_impl += f" AND {date_col_expr(date_field_to_filter)} {start_op} {date_param_expr()} "
        args_impl.append(start_date_val)

    end_op, end_date_val = _format_date_for_query(end_date, is_end_date=True, is_sqlite=is_sqlite)
    if end_op:
        query_impl += f" AND {date_col_expr(date_field_to_filter)} {end_op} {date_param_expr()} "
        args_impl.append(end_date_val)


    if sort_impl_date in ['asc', 'desc']:
        order_dir = 'ASC' if sort_impl_date == 'asc' else 'DESC'
        query_impl += f" ORDER BY {date_col_expr('i.data_criacao')} {order_dir}, i.nome_empresa "
    else:
        query_impl += " ORDER BY i.nome_empresa "

    impl_list = query_db(query_impl, tuple(args_impl))
    impl_list = impl_list if impl_list is not None else []

    impl_completas = [impl for impl in impl_list if isinstance(impl, dict) and impl.get('tipo') == 'completa']

    modules_implantacao_lista = []
    def _to_dt(val):
        if not val:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, date) and not isinstance(val, datetime):
            return datetime.combine(val, datetime.min.time())
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val.replace('Z', '+00:00'))
            except ValueError:
                try:
                    return datetime.strptime(val, '%Y-%m-%d %H:%M:%S.%f') if '.' in val else datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        return datetime.strptime(val, '%Y-%m-%d')
                    except ValueError:
                        return None
        return None
    
    query_modules = """
        SELECT i.*, p.nome as cs_nome, p.cargo as cs_cargo, p.perfil_acesso as cs_perfil
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        WHERE i.tipo = 'modulo'
    """
    args_modules = []
    if target_cs_email:
        query_modules += " AND i.usuario_cs = %s "
        args_modules.append(target_cs_email)
    modules_rows = query_db(query_modules, tuple(args_modules)) or []

    for impl in modules_rows:
        if not isinstance(impl, dict):
            continue
        status = impl.get('status')
        dias = 0
        if status == 'parada':
            try:
                dias_parada = calculate_time_in_status(impl.get('id'), 'parada')
                dias = dias_parada if dias_parada is not None else 0
            except Exception:
                dias = 0
        elif status in ['andamento', 'atrasada']:
            di = _to_dt(impl.get('data_inicio_efetivo'))
            if di:
                agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
                inicio_naive = di.replace(tzinfo=None) if di.tzinfo else di
                try:
                    delta = agora_naive - inicio_naive
                    dias = delta.days if delta.days >= 0 else 0
                except TypeError:
                    dias = 0
            else:
                dias = 0
        else:
            dc = _to_dt(impl.get('data_criacao'))
            if dc:
                agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
                criacao_naive = dc.replace(tzinfo=None) if dc.tzinfo else dc
                try:
                    delta = agora_naive - criacao_naive
                    dias = delta.days if delta.days >= 0 else 0
                except TypeError:
                    dias = 0
            else:
                dias = 0

        modules_implantacao_lista.append({
            'impl_id': impl.get('id'),
            'id': impl.get('id'),
            'nome_empresa': impl.get('nome_empresa'),
            'cs_nome': impl.get('cs_nome', impl.get('usuario_cs')),
            'status': status,
            'modulo': impl.get('modulo'),
            'dias': dias,
        })
    
    all_cs_profiles = query_db("SELECT usuario, nome, cargo, perfil_acesso FROM perfil_usuario")
    all_cs_profiles = all_cs_profiles if all_cs_profiles is not None else [] 

    primeiro_dia_mes = agora.replace(day=1)
    default_task_start_date_str = primeiro_dia_mes.strftime('%Y-%m-%d')
    default_task_end_date_str = agora.strftime('%Y-%m-%d')

    task_start_date_to_query = (task_start_date.strftime('%Y-%m-%d') if isinstance(task_start_date, (date, datetime)) else task_start_date) or default_task_start_date_str
    task_end_date_to_query = (task_end_date.strftime('%Y-%m-%d') if isinstance(task_end_date, (date, datetime)) else task_end_date) or default_task_end_date_str

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

    task_start_op, task_start_date_val = _format_date_for_query(task_start_date_to_query, is_sqlite=is_sqlite)
    if task_start_op:
        query_tasks += f" AND {date_col_expr('t.data_conclusao')} {task_start_op} {date_param_expr()} "
        args_tasks.append(task_start_date_val)

    task_end_op, task_end_date_val = _format_date_for_query(task_end_date_to_query, is_end_date=True, is_sqlite=is_sqlite)
    if task_end_op:
        query_tasks += f" AND {date_col_expr('t.data_conclusao')} {task_end_op} {date_param_expr()} "
        args_tasks.append(task_end_date_val)

    query_tasks += " GROUP BY i.usuario_cs, p.nome, t.tag ORDER BY cs_nome, t.tag "

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

    cs_metrics_ranking = {p['usuario']: {
        'email': p['usuario'], 'nome': p['nome'] or p['usuario'], 'cargo': p['cargo'] or 'N/A',
        'perfil': p['perfil_acesso'] or 'Nenhum',
        'impl_total_ranking': 0, 'tma_sum_ranking': 0, 'impl_finalizadas_ranking': 0,
        'tma_medio_ranking': 'N/A'
    } for p in all_cs_profiles if p and p.get('usuario')} 
    
    query_impl_ano = """
        SELECT i.usuario_cs, i.data_finalizacao, i.data_criacao
        FROM implantacoes i
        WHERE i.status = 'finalizada' AND i.tipo = 'completa'
    """
    args_impl_ano = []
    
    if is_sqlite:
         query_impl_ano += " AND strftime('%Y', i.data_finalizacao) = %s "
         args_impl_ano.append(str(ano_corrente))
    else:           
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
            

    total_impl_global = 0
    total_finalizadas = 0
    total_andamento_global = 0
    total_paradas = 0
    total_novas_global = 0
    total_futuras_global = 0 
    total_atrasadas_status = 0
    total_canceladas_global = 0                
    tma_dias_sum = 0
    implantacoes_paradas_detalhadas = []
    implantacoes_canceladas_detalhadas = []
    
    chart_data_nivel_receita = {label: 0 for label in NIVEIS_RECEITA}
    chart_data_nivel_receita["Não Definido"] = 0 
    
    chart_data_ranking_colab = {}

    for impl in impl_completas:
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
            
        elif status == 'cancelada':             
            total_canceladas_global += 1
            implantacoes_canceladas_detalhadas.append({
                'id': impl_id,
                'nome_empresa': impl.get('nome_empresa'),
                'cs_nome': cs_nome_impl,
                'data_cancelamento': impl.get('data_cancelamento')
            })

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

    global_metrics = {
        'total_clientes': total_impl_global, 
        'total_finalizadas': total_finalizadas,
        'total_andamento': total_andamento_global,
        'total_paradas': total_paradas,
        'total_novas': total_novas_global,
        'total_futuras': total_futuras_global,
        'total_canceladas': total_canceladas_global,\
        'total_sem_previsao': total_novas_global, 
        'total_atrasadas': total_atrasadas_status, 
        'media_tma': round(tma_dias_sum / total_finalizadas, 1) if total_finalizadas > 0 and tma_dias_sum is not None else 0, 
    }
    
    status_data = {
        'Novas': total_novas_global,
        'Em Andamento': total_andamento_global,
        'Finalizadas': total_finalizadas,
        'Paradas': total_paradas,
        'Futuras': total_futuras_global,
        'Atrasadas': total_atrasadas_status,
        'Canceladas': total_canceladas_global\
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
        'implantacoes_lista_detalhada': impl_completas,
        'modules_implantacao_lista': modules_implantacao_lista,
        'chart_data': chart_data,
        'implantacoes_paradas_lista': implantacoes_paradas_detalhadas,
        'implantacoes_canceladas_lista': implantacoes_canceladas_detalhadas,
        'task_summary_data': task_summary_list,
        'default_task_start_date': default_task_start_date_str,
        'default_task_end_date': default_task_end_date_str,
    }

def get_implants_by_day(start_date=None, end_date=None, cs_email=None):
    """Contagem de implantações finalizadas por dia, com filtros opcionais."""
    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    query = f"""
        SELECT {date_col_expr('i.data_finalizacao')} AS dia, COUNT(*) AS total
        FROM implantacoes i
        WHERE i.status = 'finalizada'
    """
    args = []

    if cs_email:
        query += " AND i.usuario_cs = %s"
        args.append(cs_email)

    def _fmt(val, is_end=False):
        if not val:
            return None, None
        if isinstance(val, datetime):
            dt = val.date()
            ds = dt.strftime('%Y-%m-%d')
        elif isinstance(val, date):
            dt = val
            ds = val.strftime('%Y-%m-%d')
        else:
            ds = str(val)
            try:
                dt = datetime.strptime(ds, '%Y-%m-%d').date()
            except ValueError:
                return None, None
        if is_end and not is_sqlite:
            return '<', (dt + timedelta(days=1)).strftime('%Y-%m-%d')
        return '<=' if is_end else '>=', ds

    if start_date:
        op, val = _fmt(start_date, is_end=False)
        if op:
            query += f" AND {date_col_expr('i.data_finalizacao')} {op} {date_param_expr()}"
            args.append(val)

    if end_date:
        op, val = _fmt(end_date, is_end=True)
        if op:
            query += f" AND {date_col_expr('i.data_finalizacao')} {op} {date_param_expr()}"
            args.append(val)

    query += f" GROUP BY {date_col_expr('i.data_finalizacao')} ORDER BY {date_col_expr('i.data_finalizacao')}"
    rows = query_db(query, tuple(args)) or []
    labels = [r.get('dia') for r in rows]
    data = [r.get('total', 0) for r in rows]
    return { 'labels': labels, 'data': data }


def get_funnel_counts(start_date=None, end_date=None, cs_email=None):
    """Contagem de implantações por status, com período opcional (data_criacao)."""
    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    query = """
        SELECT i.status, COUNT(*) AS total
        FROM implantacoes i
        WHERE 1=1
    """
    args = []

    if cs_email:
        query += " AND i.usuario_cs = %s"
        args.append(cs_email)

    def _fmt(val, is_end=False):
        if not val:
            return None, None
        if isinstance(val, datetime):
            dt = val.date()
            ds = dt.strftime('%Y-%m-%d')
        elif isinstance(val, date):
            dt = val
            ds = val.strftime('%Y-%m-%d')
        else:
            ds = str(val)
            try:
                dt = datetime.strptime(ds, '%Y-%m-%d').date()
            except ValueError:
                return None, None
        if is_end and not is_sqlite:
            return '<', (dt + timedelta(days=1)).strftime('%Y-%m-%d')
        return '<=' if is_end else '>=', ds

    if start_date:
        op, val = _fmt(start_date, is_end=False)
        if op:
            query += f" AND {date_col_expr('i.data_criacao')} {op} {date_param_expr()}"
            args.append(val)

    if end_date:
        op, val = _fmt(end_date, is_end=True)
        if op:
            query += f" AND {date_col_expr('i.data_criacao')} {op} {date_param_expr()}"
            args.append(val)

    query += " GROUP BY i.status"
    rows = query_db(query, tuple(args)) or []
    mapping = { r.get('status'): r.get('total', 0) for r in rows }
    ordered_labels = ['nova', 'futura', 'andamento', 'parada', 'finalizada', 'cancelada']
    labels_pt = ['Novas', 'Futuras', 'Em Andamento', 'Paradas', 'Finalizadas', 'Canceladas']
    data = [mapping.get(k, 0) for k in ordered_labels]
    return { 'labels': labels_pt, 'data': data }


def get_gamification_rank(month=None, year=None):
    """Ranking de gamificação por mês/ano, usando tabela de métricas mensais."""
    agora = datetime.now()
    m = month or agora.month
    y = year or agora.year
    query = """
        SELECT gm.usuario_cs,
               COALESCE(p.nome, gm.usuario_cs) AS nome,
               COALESCE(gm.pontuacao_calculada, 0) AS pontos
        FROM gamificacao_metricas_mensais gm
        LEFT JOIN perfil_usuario p ON gm.usuario_cs = p.usuario
        WHERE gm.mes = %s AND gm.ano = %s
        ORDER BY gm.pontuacao_calculada DESC, nome ASC
    """
    rows = query_db(query, (m, y)) or []
    labels = [r.get('nome') for r in rows]
    data = [r.get('pontos', 0) for r in rows]
    return { 'labels': labels, 'data': data, 'month': m, 'year': y }

def get_cancelamentos_data(cs_email=None, start_date=None, end_date=None):
    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    args = []
    query = (
        """
            SELECT i.id, i.nome_empresa, i.usuario_cs, i.data_criacao, i.data_cancelamento,
                   i.motivo_cancelamento, i.seguimento, i.tipos_planos, i.alunos_ativos,
                   i.nivel_receita, i.valor_atribuido
            FROM implantacoes i
            WHERE i.status = 'cancelada'
        """
    )
    if cs_email:
        query += " AND i.usuario_cs = %s"
        args.append(cs_email)
    def _fmt(val, is_end=False):
        if not val:
            return None, None
        if isinstance(val, datetime):
            dt = val.date()
            ds = dt.strftime('%Y-%m-%d')
        elif isinstance(val, date):
            dt = val
            ds = val.strftime('%Y-%m-%d')
        else:
            ds = str(val)
            try:
                dt = datetime.strptime(ds, '%Y-%m-%d').date()
            except ValueError:
                return None, None
        if is_end and not is_sqlite:
            return '<', (dt + timedelta(days=1)).strftime('%Y-%m-%d')
        return '<=' if is_end else '>=', ds
    if start_date:
        op, val = _fmt(start_date, False)
        if op:
            query += f" AND {date_col_expr('i.data_cancelamento')} {op} {date_param_expr()}"
            args.append(val)
    if end_date:
        op, val = _fmt(end_date, True)
        if op:
            query += f" AND {date_col_expr('i.data_cancelamento')} {op} {date_param_expr()}"
            args.append(val)
    query += " ORDER BY i.data_cancelamento DESC"
    rows = query_db(query, tuple(args)) or []
    def _to_dt(val):
        if not val:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, date):
            return datetime.combine(val, datetime.min.time())
        if isinstance(val, str):
            for fmt in ['%Y-%m-%d %H:%M:%S.%f','%Y-%m-%d %H:%M:%S','%Y-%m-%d']:
                try:
                    return datetime.strptime(val, fmt)
                except ValueError:
                    pass
        return None
    for r in rows:
        dc = _to_dt(r.get('data_cancelamento'))
        cri = _to_dt(r.get('data_criacao'))
        if dc and cri:
            try:
                r['tempo_permanencia_dias'] = max(0, (dc.date() - cri.date()).days)
            except Exception:
                r['tempo_permanencia_dias'] = max(0, (dc - cri).days)
        else:
            r['tempo_permanencia_dias'] = None
    motivos = {}
    for r in rows:
        m = (r.get('motivo_cancelamento') or '').strip().lower()
        if not m:
            m = 'não informado'
        cat = 'preço' if ('preço' in m or 'valor' in m) else ('produto' if ('funcional' in m or 'bug' in m or 'suporte' in m) else ('processo' if ('processo' in m or 'implant' in m) else 'outros'))
        motivos[cat] = motivos.get(cat, 0) + 1
    total_cancel = sum(motivos.values()) if motivos else 0
    motivo_labels = list(motivos.keys())
    motivo_counts = [motivos[k] for k in motivo_labels]
    motivo_perc = [(c/total_cancel*100) if total_cancel>0 else 0 for c in motivo_counts]
    series = {}
    for r in rows:
        dc = _to_dt(r.get('data_cancelamento'))
        if not dc:
            continue
        key = dc.strftime('%Y-%m')
        series[key] = series.get(key, 0) + 1
    labels = sorted(series.keys())
    data_ts = [series[k] for k in labels]
    ma3 = []
    for i in range(len(data_ts)):
        window = data_ts[max(0, i-2):i+1]
        ma3.append(round(sum(window)/len(window), 2))
    seg_counts = {}
    planos_counts = {}
    tamanho_counts = {'micro':0,'pequena':0,'media':0,'grande':0}
    for r in rows:
        seg = (r.get('seguimento') or 'não informado')
        seg_counts[seg] = seg_counts.get(seg, 0) + 1
        plano = (r.get('tipos_planos') or 'não informado')
        planos_counts[plano] = planos_counts.get(plano, 0) + 1
        alunos = r.get('alunos_ativos') or 0
        if alunos < 100:
            tamanho_counts['micro'] += 1
        elif alunos < 500:
            tamanho_counts['pequena'] += 1
        elif alunos < 2000:
            tamanho_counts['media'] += 1
        else:
            tamanho_counts['grande'] += 1
    tempos = [r['tempo_permanencia_dias'] for r in rows if r.get('tempo_permanencia_dias') is not None]
    tempos_sorted = sorted(tempos)
    def pct(p):
        if not tempos_sorted:
            return None
        idx = max(0, min(len(tempos_sorted)-1, int(round(p*(len(tempos_sorted)-1)))))
        return tempos_sorted[idx]
    dist = {'p50': pct(0.5), 'p75': pct(0.75), 'p90': pct(0.9)}
    def parse_val(v):
        if not v:
            return 0.0
        s = str(v).replace('R$','').replace('.','').replace(',','.')
        try:
            return float(s)
        except:
            return 0.0
    valores = [parse_val(r.get('valor_atribuido')) for r in rows]
    valor_medio = round(sum(valores)/len(valores), 2) if valores else 0.0
    perda_anual = round(sum(valores)*12/ max(1, len(labels)), 2) if labels else 0.0
    nivel_counts = {}
    for r in rows:
        nv = (r.get('nivel_receita') or 'não informado')
        nivel_counts[nv] = nivel_counts.get(nv, 0) + 1
    valor_buckets = {'<300':0,'300-500':0,'500-800':0,'800-1200':0,'>1200':0}
    for v in valores:
        if v < 300:
            valor_buckets['<300'] += 1
        elif v < 500:
            valor_buckets['300-500'] += 1
        elif v < 800:
            valor_buckets['500-800'] += 1
        elif v < 1200:
            valor_buckets['800-1200'] += 1
        else:
            valor_buckets['>1200'] += 1
    tempo_bins = {'0-30d':0,'31-90d':0,'91-180d':0,'181-365d':0,'>365d':0}
    for d in tempos:
        if d <= 30:
            tempo_bins['0-30d'] += 1
        elif d <= 90:
            tempo_bins['31-90d'] += 1
        elif d <= 180:
            tempo_bins['91-180d'] += 1
        elif d <= 365:
            tempo_bins['181-365d'] += 1
        else:
            tempo_bins['>365d'] += 1
    chart_data = {
        'motivos': { 'labels': motivo_labels, 'data': motivo_counts, 'perc': motivo_perc },
        'segmento': { 'labels': list(seg_counts.keys()), 'data': list(seg_counts.values()) },
        'nivel_receita': { 'labels': list(nivel_counts.keys()), 'data': list(nivel_counts.values()) },
        'valor_atribuido_buckets': { 'labels': list(valor_buckets.keys()), 'data': list(valor_buckets.values()) },
        'tempo_dias_hist': { 'labels': list(tempo_bins.keys()), 'data': list(tempo_bins.values()) }
    }
    metrics = {
        'total_cancelamentos': total_cancel,
        'valor_medio_perdido': valor_medio,
        'perda_anual_estimada': perda_anual,
        'distribuicao_tempo': dist,
        'perda_estim_6m': round(sum(valores)*6, 2)
    }
    return { 'dataset': rows, 'chart_data': chart_data, 'metrics': metrics }
