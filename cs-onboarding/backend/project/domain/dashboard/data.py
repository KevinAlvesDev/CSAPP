"""
Módulo de Dados do Dashboard
Buscar e processar dados para o dashboard.
Princípio SOLID: Single Responsibility
"""
from datetime import date, datetime

from flask import current_app, g

from ...common.utils import format_date_br, format_date_iso_for_json
from ...config.cache_config import cache
from ...constants import PERFIL_ADMIN, PERFIL_COORDENADOR, PERFIL_GERENTE
from ...db import execute_db, query_db
from ..implantacao_service import _get_progress
from ..time_calculator import calculate_days_parada, calculate_days_passed
from .utils import format_relative_time


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
            COALESCE(t_counts.tarefas_concluidas, 0) as tarefas_concluidas,
            last_activity.ultima_atividade as ultima_atividade
        FROM implantacoes i
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        LEFT JOIN (
            SELECT
                ci.implantacao_id,
                COUNT(DISTINCT ci.id) as total_tarefas,
                COUNT(DISTINCT CASE WHEN ci.completed = TRUE THEN ci.id END) as tarefas_concluidas
            FROM checklist_items ci
            WHERE ci.tipo_item = 'subtarefa'
            GROUP BY ci.implantacao_id
        ) t_counts ON t_counts.implantacao_id = i.id
        LEFT JOIN (
            SELECT
                ci.implantacao_id,
                MAX(ch.data_criacao) as ultima_atividade
            FROM comentarios_h ch
            INNER JOIN checklist_items ci ON ch.checklist_item_id = ci.id
            WHERE ch.deleted_at IS NULL
            GROUP BY ci.implantacao_id
        ) last_activity ON last_activity.implantacao_id = i.id
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
                     WHEN 'cancelada' THEN 6
                     ELSE 7
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

        from ...database import Pagination
        pagination = Pagination(page=page, per_page=per_page, total=total)

        query_sql += " LIMIT %s OFFSET %s"
        args.extend([pagination.limit, pagination.offset])

    impl_list = query_db(query_sql, tuple(args))
    impl_list = impl_list if impl_list is not None else []

    dashboard_data = {
        'andamento': [], 'futuras': [], 'sem_previsao': [],
        'finalizadas': [], 'paradas': [], 'novas': [], 'canceladas': []
    }
    metrics = {
        'impl_andamento_total': 0,
        'implantacoes_futuras': 0, 'implantacoes_sem_previsao': 0, 'impl_finalizadas': 0, 'impl_paradas': 0,
        'impl_novas': 0, 'impl_canceladas': 0,
        'modulos_total': 0,
        'total_valor_andamento': 0.0,
        'total_valor_futuras': 0.0,
        'total_valor_sem_previsao': 0.0,
        'total_valor_finalizadas': 0.0,
        'total_valor_paradas': 0.0,
        'total_valor_novas': 0.0,
        'total_valor_canceladas': 0.0,
        'total_valor_modulos': 0.0,
    }

    agora = datetime.now()

    for impl in impl_list:
        if not impl or not isinstance(impl, dict):
            continue

        impl_id = impl.get('id')
        if impl_id is None:
            current_app.logger.warning(f"Skipping implantacao without id: {impl}")
            continue

        status_raw = impl.get('status')
        if isinstance(status_raw, str):
            status = status_raw.replace('\xa0', ' ').strip().lower()
        else:
            status = str(status_raw).strip().lower() if status_raw else ''

        if not status:
            current_app.logger.warning(f"Implantacao {impl_id} has empty/null status. Raw value: {status_raw}. Will try to categorize anyway.")
            status = 'andamento'
        try:
            if impl.get('tipo') == 'modulo' and status in ['nova', 'andamento', 'parada', 'futura', 'sem_previsao']:
                metrics['modulos_total'] += 1
                try:
                    modulo_valor = float(impl.get('valor_monetario', 0.0) or 0.0)
                except (ValueError, TypeError):
                    modulo_valor = 0.0
                metrics['total_valor_modulos'] += modulo_valor
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
            impl_valor = float(impl.get('valor_monetario', 0.0) or 0.0)
        except (ValueError, TypeError):
            impl_valor = 0.0
        impl['valor_monetario_float'] = impl_valor

        try:
            dias_passados = calculate_days_passed(impl_id)
            if dias_passados is None:
                dias_passados = 0
        except Exception as e:
            current_app.logger.warning(f"Error calculating dias_passados for impl {impl_id}: {e}")
            dias_passados = 0
        except:
            current_app.logger.error(f"Unexpected error calculating dias_passados for impl {impl_id}")
            dias_passados = 0

        # Processar última atividade (baseada no último comentário)
        try:
            ultima_atividade_raw = impl.get('ultima_atividade')
            
            # Formatar tempo relativo com fallback seguro
            if ultima_atividade_raw:
                try:
                    ultima_atividade_text, ultima_atividade_dias, ultima_atividade_status = format_relative_time(ultima_atividade_raw)
                except Exception as e:
                    current_app.logger.warning(f"Erro ao formatar tempo relativo para impl {impl_id}: {e}")
                    ultima_atividade_text, ultima_atividade_dias, ultima_atividade_status = 'Sem comentários', None, 'gray'
            else:
                # Não há comentários registrados
                ultima_atividade_text, ultima_atividade_dias, ultima_atividade_status = 'Sem comentários', None, 'gray'
            
            # Garantir valores seguros
            impl['ultima_atividade_text'] = ultima_atividade_text or 'Sem comentários'
            impl['ultima_atividade_dias'] = ultima_atividade_dias if ultima_atividade_dias is not None else 0
            impl['ultima_atividade_status'] = ultima_atividade_status or 'gray'
            
        except Exception as e:
            # Fallback completo em caso de erro crítico
            current_app.logger.error(f"Erro crítico ao processar ultima_atividade para impl {impl_id}: {e}")
            impl['ultima_atividade_text'] = 'Sem comentários'
            impl['ultima_atividade_dias'] = 0
            impl['ultima_atividade_status'] = 'gray'

        impl['dias_passados'] = dias_passados

        if status == 'finalizada':
            dashboard_data['finalizadas'].append(impl)
            metrics['impl_finalizadas'] += 1
            metrics['total_valor_finalizadas'] += impl_valor
        elif status == 'cancelada':
            dashboard_data['canceladas'].append(impl)
            metrics['impl_canceladas'] += 1
            metrics['total_valor_canceladas'] += impl_valor
        elif status == 'parada':
            try:
                dias_parada = calculate_days_parada(impl_id)
            except Exception as e:
                current_app.logger.warning(f"Error calculating dias_parada for impl {impl_id}: {e}")
                dias_parada = 0

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

        elif status == 'andamento' or status == 'atrasada':
            if status == 'atrasada':
                try:
                    execute_db("UPDATE implantacoes SET status = 'andamento' WHERE id = %s AND status = 'atrasada'", (impl_id,))
                    status = 'andamento'
                    impl['status'] = 'andamento'
                except Exception as e:
                    current_app.logger.warning(f"Error updating status from atrasada to andamento for impl {impl_id}: {e}")
            dashboard_data['andamento'].append(impl)
            metrics['impl_andamento_total'] += 1
            metrics['total_valor_andamento'] += impl_valor
        else:
            current_app.logger.warning(f"Unknown or null status for implantacao {impl_id}: '{status}' (raw: '{status_raw}'). Categorizing as 'andamento' by default.")
            dashboard_data['andamento'].append(impl)
            metrics['impl_andamento_total'] += 1
            metrics['total_valor_andamento'] += impl_valor

    for bucket in dashboard_data.values():
        for item in bucket:
            if isinstance(item, dict) and 'dias_passados' not in item:
                item['dias_passados'] = 0

    if not is_manager_view and not filtered_cs_email and impl_list:
        try:
            execute_db(
                """
                UPDATE perfil_usuario
                SET impl_andamento_total = %s,
                    impl_finalizadas = %s, impl_paradas = %s
                WHERE usuario = %s
                """,
                (metrics['impl_andamento_total'],
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
