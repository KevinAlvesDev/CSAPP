

from flask import g, current_app
from ..db import query_db, execute_db
from .implantacao_service import _get_progress
from ..constants import (
    PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR
)
from ..common.utils import format_date_iso_for_json, format_date_br
from ..config.cache_config import cache
from datetime import datetime, date

def get_dashboard_data(user_email, filtered_cs_email=None, page=None, per_page=None, use_cache=True):
    """
    Busca e processa todos os dados para o dashboard.
    Agora com cache e suporte opcional a paginação.

    Args:
        user_email: Email do usuário
        filtered_cs_email: Email do CS para filtrar (gestores)
        page: Número da página (opcional, se None retorna todos)
        per_page: Itens por página (opcional, padrão 100)

    Returns:
        Se page é None: (dashboard_data, metrics) - comportamento original
        Se page é fornecido: (dashboard_data, metrics, pagination) - com paginação
    """

    if page is not None and per_page is None:
        per_page = 100

    cache_key = f'dashboard_data_{user_email}_{filtered_cs_email or "all"}_p{page}_pp{per_page}'

    if cache and use_cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

    perfil_acesso = g.perfil.get('perfil_acesso') if g.get('perfil') else None
    manager_profiles = [PERFIL_ADMIN, PERFIL_GERENTE, PERFIL_COORDENADOR]

    is_manager_view = perfil_acesso in manager_profiles


    query_sql = """
        SELECT
            i.*,
            p.nome as cs_nome,
            COALESCE(t_counts.total_tarefas, 0) as total_tarefas,
            COALESCE(t_counts.tarefas_concluidas, 0) as tarefas_concluidas
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        LEFT JOIN (
            SELECT
                implantacao_id,
                COUNT(*) as total_tarefas,
                COUNT(CASE WHEN concluida = TRUE THEN 1 END) as tarefas_concluidas
            FROM tarefas
            GROUP BY implantacao_id
        ) t_counts ON t_counts.implantacao_id = i.id
    """
    args = []

    if not is_manager_view:
        query_sql += " WHERE i.usuario_cs = %s "
        args.append(user_email)
    elif is_manager_view and filtered_cs_email:
        query_sql += " WHERE i.usuario_cs = %s "
        args.append(filtered_cs_email)

    query_sql += """
        ORDER BY CASE i.status
                     WHEN 'nova' THEN 1
                     WHEN 'andamento' THEN 2
                     WHEN 'parada' THEN 3
                     WHEN 'futura' THEN 4
                     WHEN 'finalizada' THEN 5
                     ELSE 6
                 END, i.data_criacao DESC
    """

    pagination = None
    if page is not None:

        count_sql = """
            SELECT COUNT(*) as total
            FROM implantacoes i
        """
        count_args = []

        if not is_manager_view:
            count_sql += " WHERE i.usuario_cs = %s "
            count_args.append(user_email)
        elif is_manager_view and filtered_cs_email:
            count_sql += " WHERE i.usuario_cs = %s "
            count_args.append(filtered_cs_email)

        total_result = query_db(count_sql, tuple(count_args), one=True)
        total = total_result.get('total', 0) if total_result else 0

        from ..database import Pagination
        pagination = Pagination(page=page, per_page=per_page, total=total)

        query_sql += " LIMIT %s OFFSET %s"
        args.extend([pagination.limit, pagination.offset])

    impl_list = query_db(query_sql, tuple(args))
    impl_list = impl_list if impl_list is not None else []


    dashboard_data = {
        'andamento': [], 'atrasadas': [], 'futuras': [], 'sem_previsao': [],
        'finalizadas': [], 'paradas': [], 'novas': [] 
    }
    metrics = {
        'impl_andamento_total': 0, 'implantacoes_atrasadas': 0,
        'implantacoes_futuras': 0, 'implantacoes_sem_previsao': 0, 'impl_finalizadas': 0, 'impl_paradas': 0,
        'impl_novas': 0,
        'modulos_total': 0,
        'total_valor_andamento': 0.0,
        'total_valor_atrasadas': 0.0,
        'total_valor_futuras': 0.0,
        'total_valor_sem_previsao': 0.0,
        'total_valor_finalizadas': 0.0,
        'total_valor_paradas': 0.0,
        'total_valor_novas': 0.0, 
    }


    agora = datetime.now() 

    for impl in impl_list:
        if not impl or not isinstance(impl, dict):
            continue

        impl_id = impl.get('id')
        if impl_id is None:
            continue

        status = impl.get('status')
        try:
            if impl.get('tipo') == 'modulo' and status in ['nova','andamento','atrasada','parada','futura','sem_previsao']:
                metrics['modulos_total'] += 1
        except Exception:
            pass

        impl['data_criacao_iso'] = format_date_iso_for_json(impl.get('data_criacao'), only_date=True)
        impl['data_inicio_efetivo_iso'] = format_date_iso_for_json(impl.get('data_inicio_efetivo'), only_date=True)
        impl['data_inicio_producao_iso'] = format_date_iso_for_json(impl.get('data_inicio_producao'), only_date=True)
        impl['data_final_implantacao_iso'] = format_date_iso_for_json(impl.get('data_final_implantacao'), only_date=True)

        try:
            prog_percent, _, _ = _get_progress(impl_id)
        except Exception:
            total_tasks = impl.get('total_tarefas', 0) or 0
            done_tasks = impl.get('tarefas_concluidas', 0) or 0
            prog_percent = int(round((done_tasks / total_tasks) * 100)) if total_tasks > 0 else 100
        impl['progresso'] = prog_percent

        try:
            impl_valor = float(impl.get('valor_atribuido', 0.0))
        except (ValueError, TypeError):
            impl_valor = 0.0
        impl['valor_atribuido'] = impl_valor


        dias_passados = 0
        data_inicio_obj = impl.get('data_inicio_efetivo') 
        
        if data_inicio_obj:
            data_inicio_datetime = None
            if isinstance(data_inicio_obj, str):
                try:
                    data_inicio_datetime = datetime.fromisoformat(data_inicio_obj.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        if '.' in data_inicio_obj:
                            data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d %H:%M:%S.%f')
                        else:
                            data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                         try:
                            data_inicio_datetime = datetime.strptime(data_inicio_obj, '%Y-%m-%d')
                         except ValueError:
                            current_app.logger.warning(f"Invalid data_inicio_efetivo format for impl {impl_id}: {data_inicio_obj}")
            
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
                    current_app.logger.warning(f"Type error calculating dias_passados for impl {impl_id}: {te}")
                    dias_passados = -1
                    
        impl['dias_passados'] = dias_passados 

        if status == 'finalizada':
            dashboard_data['finalizadas'].append(impl)
            metrics['impl_finalizadas'] += 1
            metrics['total_valor_finalizadas'] += impl_valor
        elif status == 'parada':

            dias_parada = 0
            data_finalizacao_obj = impl.get('data_finalizacao')
            if data_finalizacao_obj:
                data_inicio_parada_datetime = None
                if isinstance(data_finalizacao_obj, str):
                    try:
                        data_inicio_parada_datetime = datetime.fromisoformat(data_finalizacao_obj.replace('Z', '+00:00'))
                    except ValueError:
                        try:
                            if '.' in data_finalizacao_obj:
                                data_inicio_parada_datetime = datetime.strptime(data_finalizacao_obj, '%Y-%m-%d %H:%M:%S.%f')
                            else:
                                data_inicio_parada_datetime = datetime.strptime(data_finalizacao_obj, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                data_inicio_parada_datetime = datetime.strptime(data_finalizacao_obj, '%Y-%m-%d')
                            except ValueError:
                                current_app.logger.warning(f"Invalid data_finalizacao format for impl {impl_id}: {data_finalizacao_obj}")
                elif isinstance(data_finalizacao_obj, date) and not isinstance(data_finalizacao_obj, datetime):
                    data_inicio_parada_datetime = datetime.combine(data_finalizacao_obj, datetime.min.time())
                elif isinstance(data_finalizacao_obj, datetime):
                    data_inicio_parada_datetime = data_finalizacao_obj

                if data_inicio_parada_datetime:
                    try:
                        agora_naive = agora.replace(tzinfo=None) if agora.tzinfo else agora
                        parada_naive = data_inicio_parada_datetime.replace(tzinfo=None) if data_inicio_parada_datetime.tzinfo else data_inicio_parada_datetime
                        dias_parada_delta = agora_naive - parada_naive
                        dias_parada = dias_parada_delta.days if dias_parada_delta.days >= 0 else 0
                    except TypeError as te:
                        current_app.logger.warning(f"Error calculating dias_parada for impl {impl_id}: {te}")

            impl['dias_parada'] = dias_parada
            dashboard_data['paradas'].append(impl)
            metrics['impl_paradas'] += 1
            metrics['total_valor_paradas'] += impl_valor
        elif status == 'futura': 
            dashboard_data['futuras'].append(impl)
            metrics['implantacoes_futuras'] += 1
            metrics['total_valor_futuras'] += impl_valor
            
            data_prevista_str = impl.get('data_inicio_previsto')
            data_prevista_obj = None

            if data_prevista_str and isinstance(data_prevista_str, str):
                try:
                    data_prevista_obj = datetime.strptime(data_prevista_str, '%Y-%m-%d').date()
                except ValueError:
                    current_app.logger.warning(f"Invalid data_inicio_previsto format for impl {impl_id}: {data_prevista_str}")
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

        elif status == 'sem_previsao':
            dashboard_data['sem_previsao'].append(impl)
            metrics['implantacoes_sem_previsao'] += 1
            metrics['total_valor_sem_previsao'] += impl_valor

        elif status == 'andamento':
            metrics['impl_andamento_total'] += 1 
            if dias_passados > 25:
                try:
                    execute_db("UPDATE implantacoes SET status = 'atrasada' WHERE id = %s AND status = 'andamento'", (impl_id,))
                    status = 'atrasada'
                    impl['status'] = 'atrasada'
                except Exception:
                    pass
                dashboard_data['atrasadas'].append(impl)
                metrics['implantacoes_atrasadas'] += 1
                metrics['total_valor_atrasadas'] += impl_valor
            else:
                dashboard_data['andamento'].append(impl)
                metrics['total_valor_andamento'] += impl_valor 
        elif status == 'atrasada':
            metrics['implantacoes_atrasadas'] += 1
            if dias_passados <= 25:
                try:
                    execute_db("UPDATE implantacoes SET status = 'andamento' WHERE id = %s AND status = 'atrasada'", (impl_id,))
                    status = 'andamento'
                    impl['status'] = 'andamento'
                    dashboard_data['andamento'].append(impl)
                    metrics['total_valor_andamento'] += impl_valor
                except Exception:
                    dashboard_data['atrasadas'].append(impl)
                    metrics['total_valor_atrasadas'] += impl_valor
            else:
                dashboard_data['atrasadas'].append(impl)
                metrics['total_valor_atrasadas'] += impl_valor

        else:
            current_app.logger.warning(f"Unknown or null status for implantacao {impl_id}: '{status}'. Skipping categorization.")

    if not is_manager_view and not filtered_cs_email and impl_list:
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
            current_app.logger.error(f"Failed to update metrics for user {user_email}: {update_err}")

    if pagination:
        result = (dashboard_data, metrics, pagination)
    else:
        result = (dashboard_data, metrics)

    if cache and use_cache:
        cache.set(cache_key, result, timeout=300)

    return result
