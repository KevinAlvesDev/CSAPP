"""
Módulo de Dashboard de Analytics
Dados consolidados do dashboard gerencial.
Princípio SOLID: Single Responsibility
"""

from datetime import date, datetime

from flask import current_app

from ...constants import NIVEIS_RECEITA
from ...db import query_db
from ..time_calculator import calculate_days_parada, calculate_days_passed
from .utils import _format_date_for_query, calculate_time_in_status, date_col_expr, date_param_expr


def get_analytics_data(
    target_cs_email=None,
    target_status=None,
    start_date=None,
    end_date=None,
    target_tag=None,
    task_cs_email=None,
    task_start_date=None,
    task_end_date=None,
    sort_impl_date=None,
    context=None,
):
    """Busca e processa dados de TODA a carteira (ou filtrada) para o módulo Gerencial."""

    is_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)
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
    
    if context:
        if context == "onboarding":
            query_impl += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "
        else:
            query_impl += " AND i.contexto = %s "
            args_impl.append(context)

    if target_status and target_status != "todas":
        if target_status == "nova":
            query_impl += " AND i.status = 'nova' "
        elif target_status == "futura":
            query_impl += " AND i.status = 'futura' "
        elif target_status == "cancelada":
            query_impl += " AND i.status = 'cancelada' "
        else:
            query_impl += " AND i.status = %s "
            args_impl.append(target_status)

    date_field_to_filter = "i.data_finalizacao" if target_status in ["finalizada", "cancelada"] else "i.data_criacao"

    start_op, start_date_val = _format_date_for_query(start_date, is_sqlite=is_sqlite)
    if start_op:
        query_impl += f" AND {date_col_expr(date_field_to_filter)} {start_op} {date_param_expr()} "
        args_impl.append(start_date_val)

    end_op, end_date_val = _format_date_for_query(end_date, is_end_date=True, is_sqlite=is_sqlite)
    if end_op:
        query_impl += f" AND {date_col_expr(date_field_to_filter)} {end_op} {date_param_expr()} "
        args_impl.append(end_date_val)

    if sort_impl_date in ["asc", "desc"]:
        order_dir = "ASC" if sort_impl_date == "asc" else "DESC"
        query_impl += f" ORDER BY {date_col_expr('i.data_criacao')} {order_dir}, i.nome_empresa "
    else:
        query_impl += " ORDER BY i.nome_empresa "

    impl_list = query_db(query_impl, tuple(args_impl))
    impl_list = impl_list if impl_list is not None else []

    impl_completas = [impl for impl in impl_list if isinstance(impl, dict) and impl.get("tipo") == "completa"]

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
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except ValueError:
                try:
                    return (
                        datetime.strptime(val, "%Y-%m-%d %H:%M:%S.%f")
                        if "." in val
                        else datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                    )
                except ValueError:
                    try:
                        return datetime.strptime(val, "%Y-%m-%d")
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

    if context:
        if context == "onboarding":
            query_modules += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "
        else:
            query_modules += " AND i.contexto = %s "
            args_modules.append(context)
    modules_rows = query_db(query_modules, tuple(args_modules)) or []

    for impl in modules_rows:
        if not isinstance(impl, dict):
            continue
        status = impl.get("status")
        dias = 0
        if status == "parada":
            try:
                dias_parada = calculate_time_in_status(impl.get("id"), "parada")
                dias = dias_parada if dias_parada is not None else 0
            except Exception:
                dias = 0
        elif status == "andamento":
            di = _to_dt(impl.get("data_inicio_efetivo"))
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
            dc = _to_dt(impl.get("data_criacao"))
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

        modules_implantacao_lista.append(
            {
                "impl_id": impl.get("id"),
                "id": impl.get("id"),
                "nome_empresa": impl.get("nome_empresa"),
                "cs_nome": impl.get("cs_nome", impl.get("usuario_cs")),
                "status": status,
                "modulo": impl.get("modulo"),
                "dias": dias,
            }
        )

    all_cs_profiles = query_db("SELECT usuario, nome, cargo, perfil_acesso FROM perfil_usuario")
    all_cs_profiles = all_cs_profiles if all_cs_profiles is not None else []

    primeiro_dia_mes = agora.replace(day=1)
    default_task_start_date_str = primeiro_dia_mes.strftime("%Y-%m-%d")
    default_task_end_date_str = agora.strftime("%Y-%m-%d")

    task_start_date_to_query = (
        task_start_date.strftime("%Y-%m-%d") if isinstance(task_start_date, (date, datetime)) else task_start_date
    ) or default_task_start_date_str
    task_end_date_to_query = (
        task_end_date.strftime("%Y-%m-%d") if isinstance(task_end_date, (date, datetime)) else task_end_date
    ) or default_task_end_date_str

    query_tasks = """
        SELECT
            i.usuario_cs,
            COALESCE(p.nome, i.usuario_cs) as cs_nome,
            COALESCE(ci.tag, 'Ação interna') as tag,
            COUNT(DISTINCT ci.id) as total_concluido
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        LEFT JOIN perfil_usuario p ON i.usuario_cs = p.usuario
        WHERE
            ci.tipo_item = 'subtarefa'
            AND ci.completed = TRUE
            AND ci.tag IN ('Ação interna', 'Reunião')
            AND ci.data_conclusao IS NOT NULL
    """
    args_tasks = []

    if task_cs_email:
        query_tasks += " AND i.usuario_cs = %s "
        args_tasks.append(task_cs_email)

    if context:
        if context == "onboarding":
            query_tasks += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "
        else:
            query_tasks += " AND i.contexto = %s "
            args_tasks.append(context)

    task_start_op, task_start_date_val = _format_date_for_query(task_start_date_to_query, is_sqlite=is_sqlite)
    if task_start_op:
        query_tasks += f" AND {date_col_expr('ci.data_conclusao')} {task_start_op} {date_param_expr()} "
        args_tasks.append(task_start_date_val)

    task_end_op, task_end_date_val = _format_date_for_query(
        task_end_date_to_query, is_end_date=True, is_sqlite=is_sqlite
    )
    if task_end_op:
        query_tasks += f" AND {date_col_expr('ci.data_conclusao')} {task_end_op} {date_param_expr()} "
        args_tasks.append(task_end_date_val)

    query_tasks += " GROUP BY i.usuario_cs, p.nome, ci.tag ORDER BY cs_nome, ci.tag "

    tasks_summary_raw = query_db(query_tasks, tuple(args_tasks))
    tasks_summary_raw = tasks_summary_raw if tasks_summary_raw is not None else []

    task_summary_processed = {}
    for row in tasks_summary_raw:
        if not row or not isinstance(row, dict):
            continue
        email = row.get("usuario_cs")
        if not email:
            continue

        if email not in task_summary_processed:
            task_summary_processed[email] = {
                "usuario_cs": email,
                "cs_nome": row.get("cs_nome", email),
                "Ação interna": 0,
                "Reunião": 0,
            }

        tag = row.get("tag")
        total = row.get("total_concluido", 0)
        if tag == "Ação interna":
            task_summary_processed[email]["Ação interna"] = total
        elif tag == "Reunião":
            task_summary_processed[email]["Reunião"] = total

    task_summary_list = list(task_summary_processed.values())

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

    if context:
        if context == "onboarding":
            query_impl_ano += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "
        else:
            query_impl_ano += " AND i.contexto = %s "
            args_impl_ano.append(context)

    impl_finalizadas_ano_corrente = query_db(query_impl_ano, tuple(args_impl_ano))
    impl_finalizadas_ano_corrente = impl_finalizadas_ano_corrente if impl_finalizadas_ano_corrente is not None else []

    chart_data_ranking_periodo = {i: 0 for i in range(1, 13)}

    for impl in impl_finalizadas_ano_corrente:
        if not impl or not isinstance(impl, dict):
            continue
        dt_finalizacao = impl.get("data_finalizacao")

        dt_finalizacao_datetime = None
        if isinstance(dt_finalizacao, str):
            try:
                dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao.replace("Z", "+00:00"))
            except ValueError:
                try:
                    if "." in dt_finalizacao:
                        dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
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
    total_canceladas_global = 0
    tma_dias_sum = 0
    implantacoes_paradas_detalhadas = []
    implantacoes_canceladas_detalhadas = []

    chart_data_nivel_receita = {label: 0 for label in NIVEIS_RECEITA}
    chart_data_nivel_receita["Não Definido"] = 0

    chart_data_ranking_colab = {}

    for impl in impl_completas:
        if not impl or not isinstance(impl, dict):
            continue

        impl_id = impl.get("id")
        cs_email_impl = impl.get("usuario_cs")
        cs_nome_impl = impl.get("cs_nome", cs_email_impl)
        status = impl.get("status")

        nivel_selecionado = impl.get("nivel_receita")
        if nivel_selecionado and nivel_selecionado in chart_data_nivel_receita:
            chart_data_nivel_receita[nivel_selecionado] += 1
        else:
            chart_data_nivel_receita["Não Definido"] += 1

        if cs_nome_impl:
            chart_data_ranking_colab[cs_nome_impl] = chart_data_ranking_colab.get(cs_nome_impl, 0) + 1

        total_impl_global += 1

        tma_dias = None
        if status == "finalizada":
            dt_criacao = impl.get("data_criacao")
            dt_finalizacao = impl.get("data_finalizacao")

            dt_criacao_datetime = None
            dt_finalizacao_datetime = None

            if isinstance(dt_criacao, str):
                try:
                    dt_criacao_datetime = datetime.fromisoformat(dt_criacao.replace("Z", "+00:00"))
                except ValueError:
                    try:
                        if "." in dt_criacao:
                            dt_criacao_datetime = datetime.strptime(dt_criacao, "%Y-%m-%d %H:%M:%S.%f")
                        else:
                            dt_criacao_datetime = datetime.strptime(dt_criacao, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
            elif isinstance(dt_criacao, date) and not isinstance(dt_criacao, datetime):
                dt_criacao_datetime = datetime.combine(dt_criacao, datetime.min.time())
            elif isinstance(dt_criacao, datetime):
                dt_criacao_datetime = dt_criacao

            if isinstance(dt_finalizacao, str):
                try:
                    dt_finalizacao_datetime = datetime.fromisoformat(dt_finalizacao.replace("Z", "+00:00"))
                except ValueError:
                    try:
                        if "." in dt_finalizacao:
                            dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, "%Y-%m-%d %H:%M:%S.%f")
                        else:
                            dt_finalizacao_datetime = datetime.strptime(dt_finalizacao, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
            elif isinstance(dt_finalizacao, date) and not isinstance(dt_finalizacao, datetime):
                dt_finalizacao_datetime = datetime.combine(dt_finalizacao, datetime.min.time())
            elif isinstance(dt_finalizacao, datetime):
                dt_finalizacao_datetime = dt_finalizacao

            if dt_criacao_datetime and dt_finalizacao_datetime:
                criacao_naive = (
                    dt_criacao_datetime.replace(tzinfo=None) if dt_criacao_datetime.tzinfo else dt_criacao_datetime
                )
                final_naive = (
                    dt_finalizacao_datetime.replace(tzinfo=None)
                    if dt_finalizacao_datetime.tzinfo
                    else dt_finalizacao_datetime
                )
                try:
                    delta = final_naive - criacao_naive
                    tma_dias = max(0, delta.days)
                except TypeError:
                    pass

            total_finalizadas += 1
            if tma_dias is not None:
                tma_dias_sum += tma_dias

        elif status == "parada":
            total_paradas += 1
            try:
                parada_dias = calculate_days_parada(impl_id)
            except Exception:
                parada_dias = 0
            motivo = impl.get("motivo_parada") or "Motivo Não Especificado"
            implantacoes_paradas_detalhadas.append(
                {
                    "id": impl_id,
                    "nome_empresa": impl.get("nome_empresa"),
                    "motivo_parada": motivo,
                    "dias_parada": parada_dias,
                    "cs_nome": cs_nome_impl,
                }
            )

        elif status == "nova":
            total_novas_global += 1

        elif status == "futura":
            total_futuras_global += 1

        elif status == "cancelada":
            total_canceladas_global += 1
            implantacoes_canceladas_detalhadas.append(
                {
                    "id": impl_id,
                    "nome_empresa": impl.get("nome_empresa"),
                    "cs_nome": cs_nome_impl,
                    "data_cancelamento": impl.get("data_cancelamento"),
                }
            )

        elif status == "andamento":
            total_andamento_global += 1

            try:
                dias_passados = calculate_days_passed(impl_id)
            except Exception:
                dias_passados = 0

    global_metrics = {
        "total_clientes": total_impl_global,
        "total_finalizadas": total_finalizadas,
        "total_andamento": total_andamento_global,
        "total_paradas": total_paradas,
        "total_novas": total_novas_global,
        "total_futuras": total_futuras_global,
        "total_canceladas": total_canceladas_global,
        "total_sem_previsao": total_novas_global,
        "media_tma": round(tma_dias_sum / total_finalizadas, 1)
        if total_finalizadas > 0 and tma_dias_sum is not None
        else 0,
    }

    status_data = {
        "Novas": total_novas_global,
        "Em Andamento": total_andamento_global,
        "Finalizadas": total_finalizadas,
        "Paradas": total_paradas,
        "Futuras": total_futuras_global,
        "Canceladas": total_canceladas_global,
    }

    ranking_colab_data = sorted(chart_data_ranking_colab.items(), key=lambda item: item[1], reverse=True)

    meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

    chart_data = {
        "status_clientes": {"labels": list(status_data.keys()), "data": list(status_data.values())},
        "nivel_receita": {
            "labels": list(chart_data_nivel_receita.keys()),
            "data": list(chart_data_nivel_receita.values()),
        },
        "ranking_colaborador": {
            "labels": [item[0] for item in ranking_colab_data],
            "data": [item[1] for item in ranking_colab_data],
        },
        "ranking_periodo": {
            "labels": meses_nomes,
            "data": [chart_data_ranking_periodo.get(i, 0) for i in range(1, 13)],
        },
    }

    # Get tags by user chart data
    from ..tags_analytics import get_tags_by_user_chart_data

    tags_chart_data = get_tags_by_user_chart_data(
        cs_email=task_cs_email,
        start_date=task_start_date_to_query,
        end_date=task_end_date_to_query,
        context=context,
    )

    return {
        "kpi_cards": global_metrics,
        "implantacoes_lista_detalhada": impl_completas,
        "modules_implantacao_lista": modules_implantacao_lista,
        "chart_data": chart_data,
        "tags_chart_data": tags_chart_data,
        "implantacoes_paradas_lista": implantacoes_paradas_detalhadas,
        "implantacoes_canceladas_lista": implantacoes_canceladas_detalhadas,
        "task_summary_data": task_summary_list,
        "default_task_start_date": default_task_start_date_str,
        "default_task_end_date": default_task_end_date_str,
    }
