import hashlib
import logging
logger = logging.getLogger(__name__)

import json

from datetime import date, datetime, timezone



from flask import Blueprint, flash, g, jsonify, make_response, redirect, render_template, request, url_for



from ....blueprints.auth import permission_required

from ....common.context_navigation import (

    detect_current_context,

    get_current_dashboard_endpoint,

    normalize_context,

)

from ....common.validation import ValidationError, sanitize_string, validate_date, validate_email, validate_integer

from ....constants import PERFIS_COM_ANALYTICS, PERFIS_COM_GESTAO

from ....modules.management.application.management_service import listar_todos_cs_com_cache

from ..application.analytics_service import (

    get_analytics_data,

    get_funnel_counts,

    get_gamification_rank,

    get_implants_by_day,

)



analytics_bp = Blueprint("analytics", __name__)


def _coerce_iso_date(value):

    if not value:

        return None

    if isinstance(value, datetime):

        return value.date()

    if isinstance(value, date):

        return value

    if isinstance(value, str):

        raw = value.strip()[:10]

        if not raw:

            return None

        try:

            return datetime.strptime(raw, "%Y-%m-%d").date()

        except ValueError:

            return None

    return None


def _filter_canceladas_lista(canceladas_lista, cs_email=None, start_date=None, end_date=None):

    filtered = []

    start_date_obj = _coerce_iso_date(start_date)

    end_date_obj = _coerce_iso_date(end_date)

    for item in canceladas_lista or []:

        if cs_email and item.get("usuario_cs") != cs_email:

            continue

        data_cancelamento = _coerce_iso_date(item.get("data_cancelamento"))

        if start_date_obj and (not data_cancelamento or data_cancelamento < start_date_obj):

            continue

        if end_date_obj and (not data_cancelamento or data_cancelamento > end_date_obj):

            continue

        filtered.append(item)

    return filtered


def _filter_paradas_lista(paradas_lista, cs_email=None, tipo=None, days_sort="recent_first"):

    filtered = []

    for item in paradas_lista or []:

        if cs_email and item.get("usuario_cs") != cs_email:

            continue

        if tipo and item.get("tipo") != tipo:

            continue

        filtered.append(item)

    reverse = days_sort != "oldest_first"

    return sorted(
        filtered,
        key=lambda item: ((item.get("dias_parada") or 0), (item.get("nome_empresa") or "")),
        reverse=reverse,
    )


def _filter_implantacoes_lista(
    implantacoes_lista,
    cs_email=None,
    status=None,
    date_field="data_criacao",
    start_date=None,
    end_date=None,
):

    filtered = []
    start_date_obj = _coerce_iso_date(start_date)
    end_date_obj = _coerce_iso_date(end_date)
    effective_date_field = "data_inicio_efetivo" if date_field == "data_inicio_efetivo" else "data_criacao"

    for item in implantacoes_lista or []:
        if cs_email and item.get("usuario_cs") != cs_email:
            continue

        item_status = (item.get("status") or "").strip()
        if status and status != "todas" and item_status != status:
            continue

        date_value = _coerce_iso_date(item.get(effective_date_field))
        if start_date_obj and (not date_value or date_value < start_date_obj):
            continue
        if end_date_obj and (not date_value or date_value > end_date_obj):
            continue

        filtered.append(item)

    return filtered


def _normalize_mrr_bucket(raw_value):
    if raw_value is None:
        return "Nao Definido"
    value = str(raw_value).strip().lower()
    if not value:
        return "Nao Definido"
    if "grande" in value:
        return "Grandes contas"
    if "diamante" in value or "diamond" in value:
        return "Diamante (MRR > 2k)"
    if "platina" in value or "platinum" in value:
        return "Platina (MRR 1k-1.9k)"
    if "ouro" in value or "gold" in value:
        return "Ouro (MRR 700-999)"
    if "prata" in value:
        return "Prata (MRR < 699)"
    if "nao definido" in value or "não definido" in value or "pendente" in value:
        return "Nao Definido"
    return "Nao Definido"


def _build_mrr_chart_data(implantacoes_lista, cs_email=None):
    filtered = []
    counts = {
        "Prata (MRR < 699)": 0,
        "Ouro (MRR 700-999)": 0,
        "Platina (MRR 1k-1.9k)": 0,
        "Diamante (MRR > 2k)": 0,
        "Grandes contas": 0,
        "Nao Definido": 0,
    }

    for item in implantacoes_lista or []:
        if cs_email and item.get("usuario_cs") != cs_email:
            continue
        filtered.append(item)
        bucket = _normalize_mrr_bucket(item.get("nivel_receita"))
        counts[bucket] = counts.get(bucket, 0) + 1

    return {
        "labels": list(counts.keys()),
        "data": list(counts.values()),
    }, filtered





def _build_analytics_signature(analytics_data: dict) -> str:

    """Gera assinatura deterministica para detectar mudancas no dashboard."""

    payload = {

        "kpi_cards": analytics_data.get("kpi_cards", {}),

        "chart_data": analytics_data.get("chart_data", {}),

        "tags_chart_data": analytics_data.get("tags_chart_data", {}),

        "implantacoes_paradas_lista": analytics_data.get("implantacoes_paradas_lista", []),

        "implantacoes_canceladas_lista": analytics_data.get("implantacoes_canceladas_lista", []),

        "implantacoes_lista_detalhada": analytics_data.get("implantacoes_lista_detalhada", []),

        "modules_implantacao_lista": analytics_data.get("modules_implantacao_lista", []),

        "task_summary_data": analytics_data.get("task_summary_data", []),

    }

    serialized = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()





@analytics_bp.route("/analytics")

@permission_required(PERFIS_COM_ANALYTICS)

def analytics_dashboard():

    """Rota para o dashboard gerencial de metricas e relatorios, com filtros."""



    user_perfil = g.perfil.get("perfil_acesso")



    cs_email = None

    status_filter = "todas"

    start_date = None

    end_date = None

    sort_impl_date = None

    module_cs_email = None

    module_status_filter = "todas"

    module_days_min = None

    module_days_max = None
    module_days_sort = "recent_first"
    mrr_cs_email = None
    impl_list_cs_email = None
    impl_list_status = "todas"
    impl_list_date_field = "data_criacao"
    impl_list_start_date = None
    impl_list_end_date = None
    stop_cs_email = None
    stop_tipo = None
    stop_days_sort = "recent_first"
    cancel_cs_email = None
    cancel_start_date = None
    cancel_end_date = None

    try:

        cs_email_param = request.args.get("cs_email")

        if cs_email_param:

            try:

                cs_email = validate_email(cs_email_param)

            except ValidationError:

                cs_email = None

                flash("Erro nos filtros: Email invalido - ignorado", "warning")

        status_filter_param = request.args.get("status_filter", "todas")

        try:

            status_filter = sanitize_string(status_filter_param, max_length=20)

        except ValidationError:

            status_filter = "todas"

            flash("Erro nos filtros: Status invalido - ignorado", "warning")

        sort_param = request.args.get("sort_impl_date")

        if sort_param:

            try:

                sort_impl_date = sanitize_string(sort_param, max_length=4)

            except ValidationError:

                sort_impl_date = None

        start_date_param = request.args.get("start_date")

        if start_date_param:

            try:

                start_date = validate_date(start_date_param)

            except ValidationError:

                start_date = None

                flash("Erro nos filtros: Data inicial invalida - ignorada", "warning")

        end_date_param = request.args.get("end_date")

        if end_date_param:

            try:

                end_date = validate_date(end_date_param)

            except ValidationError:

                end_date = None

                flash("Erro nos filtros: Data final invalida - ignorada", "warning")

        module_cs_email_param = request.args.get("module_cs_email")
        if module_cs_email_param:
            try:
                module_cs_email = validate_email(module_cs_email_param)
            except ValidationError:
                module_cs_email = None
                flash("Erro nos filtros: Email invalido nos modulos - ignorado", "warning")

        module_status_param = request.args.get("module_status_filter", "todas")
        try:
            module_status_filter = sanitize_string(module_status_param, max_length=20)
        except ValidationError:
            module_status_filter = "todas"
            flash("Erro nos filtros: Status invalido nos modulos - ignorado", "warning")

        module_days_min_param = request.args.get("module_days_min")
        if module_days_min_param:
            try:
                module_days_min = validate_integer(module_days_min_param, min_value=0)
            except ValidationError:
                module_days_min = None
                flash("Erro nos filtros: Dias minimos invalidos - ignorado", "warning")

        module_days_max_param = request.args.get("module_days_max")
        if module_days_max_param:
            try:
                module_days_max = validate_integer(module_days_max_param, min_value=0)
            except ValidationError:
                module_days_max = None
                flash("Erro nos filtros: Dias maximos invalidos - ignorado", "warning")

        module_days_sort_param = request.args.get("module_days_sort", "recent_first")
        try:
            module_days_sort = sanitize_string(module_days_sort_param, max_length=20)
        except ValidationError:
            module_days_sort = "recent_first"

        mrr_cs_email_param = request.args.get("mrr_cs_email")
        if mrr_cs_email_param:
            try:
                mrr_cs_email = validate_email(mrr_cs_email_param)
            except ValidationError:
                mrr_cs_email = None
                flash("Erro nos filtros: Email invalido na carteira por MRR - ignorado", "warning")

        impl_list_cs_email_param = request.args.get("impl_list_cs_email")
        if impl_list_cs_email_param:
            try:
                impl_list_cs_email = validate_email(impl_list_cs_email_param)
            except ValidationError:
                impl_list_cs_email = None
                flash("Erro nos filtros: Email invalido na lista de implantacoes - ignorado", "warning")

        impl_list_status_param = request.args.get("impl_list_status", "todas")
        try:
            impl_list_status = sanitize_string(impl_list_status_param, max_length=20)
        except ValidationError:
            impl_list_status = "todas"

        impl_list_date_field_param = request.args.get("impl_list_date_field", "data_criacao")
        try:
            impl_list_date_field = sanitize_string(impl_list_date_field_param, max_length=30)
        except ValidationError:
            impl_list_date_field = "data_criacao"

        impl_list_start_date_param = request.args.get("impl_list_start_date")
        if impl_list_start_date_param:
            try:
                impl_list_start_date = validate_date(impl_list_start_date_param)
            except ValidationError:
                impl_list_start_date = None
                flash("Erro nos filtros: Data inicial invalida na lista de implantacoes - ignorada", "warning")

        impl_list_end_date_param = request.args.get("impl_list_end_date")
        if impl_list_end_date_param:
            try:
                impl_list_end_date = validate_date(impl_list_end_date_param)
            except ValidationError:
                impl_list_end_date = None
                flash("Erro nos filtros: Data final invalida na lista de implantacoes - ignorada", "warning")

        stop_cs_email_param = request.args.get("stop_cs_email")
        if stop_cs_email_param:
            try:
                stop_cs_email = validate_email(stop_cs_email_param)
            except ValidationError:
                stop_cs_email = None
                flash("Erro nos filtros: Email invalido nas paradas - ignorado", "warning")

        stop_tipo_param = request.args.get("stop_tipo")
        if stop_tipo_param:
            try:
                stop_tipo = sanitize_string(stop_tipo_param, max_length=20)
            except ValidationError:
                stop_tipo = None
                flash("Erro nos filtros: Tipo invalido nas paradas - ignorado", "warning")

        stop_days_sort_param = request.args.get("stop_days_sort", "recent_first")
        try:
            stop_days_sort = sanitize_string(stop_days_sort_param, max_length=20)
        except ValidationError:
            stop_days_sort = "recent_first"

        cancel_cs_email_param = request.args.get("cancel_cs_email")
        if cancel_cs_email_param:
            try:
                cancel_cs_email = validate_email(cancel_cs_email_param)
            except ValidationError:
                cancel_cs_email = None
                flash("Erro nos filtros: Email invalido nas canceladas - ignorado", "warning")

        cancel_start_date_param = request.args.get("cancel_start_date")
        if cancel_start_date_param:
            try:
                cancel_start_date = validate_date(cancel_start_date_param)
            except ValidationError:
                cancel_start_date = None
                flash("Erro nos filtros: Data inicial invalida nas canceladas - ignorada", "warning")

        cancel_end_date_param = request.args.get("cancel_end_date")
        if cancel_end_date_param:
            try:
                cancel_end_date = validate_date(cancel_end_date_param)
            except ValidationError:
                cancel_end_date = None
                flash("Erro nos filtros: Data final invalida nas canceladas - ignorada", "warning")



        context = normalize_context(request.args.get("context")) or detect_current_context()

    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)

        flash(f"Erro nos filtros: {e!s}", "warning")

        cs_email = None

        status_filter = "todas"

        start_date = None

        end_date = None

        context = detect_current_context()



    task_cs_email = None

    task_start_date = None

    task_end_date = None



    try:

        task_cs_email_param = request.args.get("task_cs_email")

        if task_cs_email_param:

            try:

                task_cs_email = validate_email(task_cs_email_param)

            except ValidationError:

                task_cs_email = None

        task_start_date_param = request.args.get("task_start_date")

        if task_start_date_param:

            try:

                task_start_date = validate_date(task_start_date_param)

            except ValidationError:

                task_start_date = None

        task_end_date_param = request.args.get("task_end_date")

        if task_end_date_param:

            try:

                task_end_date = validate_date(task_end_date_param)

            except ValidationError:

                task_end_date = None

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        task_end_date = None

        task_cs_email = None

        task_start_date = None

        task_end_date = None



    if user_perfil not in PERFIS_COM_GESTAO:

        cs_email = g.user_email

        task_cs_email = g.user_email
        module_cs_email = g.user_email
        mrr_cs_email = g.user_email
        impl_list_cs_email = g.user_email
        stop_cs_email = g.user_email
        cancel_cs_email = g.user_email

    base_target_cs_email = None if user_perfil in PERFIS_COM_GESTAO else g.user_email
    base_start_date = None
    base_end_date = None



    try:

        base_analytics_data = get_analytics_data(

            target_cs_email=base_target_cs_email,

            target_status="todas",

            start_date=base_start_date,

            end_date=end_date,

            target_tag=None,

            task_cs_email=task_cs_email,

            task_start_date=task_start_date,

            task_end_date=task_end_date,

            sort_impl_date=sort_impl_date,

            context=context,
            module_cs_email=module_cs_email,
            module_status_filter=module_status_filter,
            module_days_min=module_days_min,
            module_days_max=module_days_max,
            module_days_sort=module_days_sort,

        )

        if status_filter and status_filter != "todas":
            status_analytics_data = get_analytics_data(
                target_cs_email=cs_email,
                target_status=status_filter,
                start_date=start_date,
                end_date=end_date,
                target_tag=None,
                task_cs_email=task_cs_email,
                task_start_date=task_start_date,
                task_end_date=task_end_date,
                sort_impl_date=sort_impl_date,
                context=context,
                module_cs_email=module_cs_email,
                module_status_filter=module_status_filter,
                module_days_min=module_days_min,
                module_days_max=module_days_max,
                module_days_sort=module_days_sort,
            )
        else:
            status_analytics_data = base_analytics_data

        analytics_data = dict(base_analytics_data)
        analytics_data["kpi_cards"] = status_analytics_data.get("kpi_cards", {})
        merged_chart_data = dict(base_analytics_data.get("chart_data", {}))
        merged_chart_data["status_clientes"] = (
            status_analytics_data.get("chart_data", {}) or {}
        ).get("status_clientes", {})
        analytics_data["chart_data"] = merged_chart_data

        all_cs = listar_todos_cs_com_cache()



        status_options = [

            {"value": "todas", "label": "Todas as Implantacoes"},

            {"value": "nova", "label": "Novas"},

            {"value": "andamento", "label": "Em Andamento"},

            {"value": "futura", "label": "Futuras"},

            {"value": "sem_previsao", "label": "Sem Previsao"},

            {"value": "finalizada", "label": "Concluídas"},

            {"value": "parada", "label": "Paradas"},

            {"value": "cancelada", "label": "Canceladas"},

        ]



        current_task_cs_email = task_cs_email

        current_task_start_date = task_start_date

        current_task_end_date = task_end_date



        base_implantacoes_lista = analytics_data.get("implantacoes_lista_detalhada", [])
        mrr_chart_data, mrr_implantacoes_lista = _build_mrr_chart_data(
            base_implantacoes_lista,
            cs_email=mrr_cs_email,
        )
        implantacoes_lista = _filter_implantacoes_lista(
            base_implantacoes_lista,
            cs_email=impl_list_cs_email,
            status=impl_list_status,
            date_field=impl_list_date_field,
            start_date=impl_list_start_date,
            end_date=impl_list_end_date,
        )
        paradas_lista = _filter_paradas_lista(
            analytics_data.get("implantacoes_paradas_lista", []),
            cs_email=stop_cs_email,
            tipo=stop_tipo,
            days_sort=stop_days_sort,
        )
        canceladas_lista = _filter_canceladas_lista(
            analytics_data.get("implantacoes_canceladas_lista", []),
            cs_email=cancel_cs_email,
            start_date=cancel_start_date,
            end_date=cancel_end_date,
        )
        analytics_data["implantacoes_lista_detalhada"] = implantacoes_lista
        analytics_data["implantacoes_paradas_lista"] = paradas_lista
        analytics_data["implantacoes_canceladas_lista"] = canceladas_lista
        analytics_signature = _build_analytics_signature(analytics_data)

        return render_template(
            "pages/analytics.html",
            kpi_cards=analytics_data.get("kpi_cards", {}),
            implantacoes_lista_detalhada=implantacoes_lista,
            modules_implantacao_lista=analytics_data.get("modules_implantacao_lista", []),
            chart_data=analytics_data.get("chart_data", {}),
            mrr_chart_data=mrr_chart_data,
            mrr_implantacoes_lista=mrr_implantacoes_lista,
            tags_chart_data=analytics_data.get("tags_chart_data", {}),
            implantacoes_paradas_lista=paradas_lista,
            implantacoes_canceladas_lista=canceladas_lista,
            task_summary_data=analytics_data.get("task_summary_data", []),
            current_task_cs_email=current_task_cs_email,
            current_task_start_date=current_task_start_date,
            current_task_end_date=current_task_end_date,
            all_cs=all_cs,
            status_options=status_options,
            current_cs_email=cs_email,
            current_status_filter=status_filter,
            current_start_date=start_date,
            current_end_date=end_date,
            current_sort_impl_date=sort_impl_date,
            current_module_cs_email=module_cs_email,
            current_module_status_filter=module_status_filter,
            current_module_days_min=module_days_min,
            current_module_days_max=module_days_max,
            current_module_days_sort=module_days_sort,
            current_mrr_cs_email=mrr_cs_email,
            current_impl_list_cs_email=impl_list_cs_email,
            current_impl_list_status=impl_list_status,
            current_impl_list_date_field=impl_list_date_field,
            current_impl_list_start_date=impl_list_start_date,
            current_impl_list_end_date=impl_list_end_date,
            current_stop_cs_email=stop_cs_email,
            current_stop_tipo=stop_tipo,
            current_stop_days_sort=stop_days_sort,
            current_cancel_cs_email=cancel_cs_email,
            current_cancel_start_date=cancel_start_date,
            current_cancel_end_date=cancel_end_date,
            user_info=g.user,
            user_perfil=user_perfil,
            context=context,
            analytics_signature=analytics_signature,
        )



    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)

        from ....config.logging_config import get_logger

        analytics_logger = get_logger("analytics")
        analytics_logger.error(f"Erro ao carregar dashboard de analytics: {e}", exc_info=True)

        flash(f"Erro interno ao carregar os dados de relatorios: {e}", "error")

        return redirect(url_for(get_current_dashboard_endpoint(context)))





@analytics_bp.route("/analytics/live/check")

@permission_required(PERFIS_COM_ANALYTICS)

def analytics_live_check():

    """Endpoint leve para verificar se os dados do dashboard mudaram."""

    user_perfil = g.perfil.get("perfil_acesso")

    cs_email = None

    status_filter = "todas"

    start_date = None

    end_date = None

    sort_impl_date = None

    task_cs_email = None

    task_start_date = None

    task_end_date = None
    module_cs_email = None
    module_status_filter = "todas"
    module_days_min = None
    module_days_max = None
    module_days_sort = "recent_first"
    mrr_cs_email = None
    impl_list_cs_email = None
    impl_list_status = "todas"
    impl_list_date_field = "data_criacao"
    impl_list_start_date = None
    impl_list_end_date = None
    stop_cs_email = None
    stop_tipo = None
    stop_days_sort = "recent_first"
    cancel_cs_email = None
    cancel_start_date = None
    cancel_end_date = None



    try:

        cs_email_param = request.args.get("cs_email")

        if cs_email_param:

            cs_email = validate_email(cs_email_param)

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        cs_email = None



    try:

        status_filter_param = request.args.get("status_filter", "todas")

        status_filter = sanitize_string(status_filter_param, max_length=20)

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        status_filter = "todas"



    try:

        sort_param = request.args.get("sort_impl_date")

        if sort_param:

            sort_impl_date = sanitize_string(sort_param, max_length=4)

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        sort_impl_date = None



    try:

        start_date_param = request.args.get("start_date")

        if start_date_param:

            start_date = validate_date(start_date_param)

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        start_date = None



    try:

        end_date_param = request.args.get("end_date")

        if end_date_param:

            end_date = validate_date(end_date_param)

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        end_date = None



    context = normalize_context(request.args.get("context")) or detect_current_context()



    try:

        task_cs_email_param = request.args.get("task_cs_email")

        if task_cs_email_param:

            task_cs_email = validate_email(task_cs_email_param)

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        task_cs_email = None



    try:

        task_start_date_param = request.args.get("task_start_date")

        if task_start_date_param:

            task_start_date = validate_date(task_start_date_param)

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        task_start_date = None



    try:

        task_end_date_param = request.args.get("task_end_date")

        if task_end_date_param:

            task_end_date = validate_date(task_end_date_param)

    except Exception as exc:

        logger.exception("Unhandled exception", exc_info=True)

        task_end_date = None

    try:
        module_cs_email_param = request.args.get("module_cs_email")
        if module_cs_email_param:
            module_cs_email = validate_email(module_cs_email_param)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        module_cs_email = None

    try:
        module_status_param = request.args.get("module_status_filter", "todas")
        module_status_filter = sanitize_string(module_status_param, max_length=20)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        module_status_filter = "todas"

    try:
        module_days_min_param = request.args.get("module_days_min")
        if module_days_min_param:
            module_days_min = validate_integer(module_days_min_param, min_value=0)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        module_days_min = None

    try:
        module_days_max_param = request.args.get("module_days_max")
        if module_days_max_param:
            module_days_max = validate_integer(module_days_max_param, min_value=0)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        module_days_max = None

    try:
        module_days_sort_param = request.args.get("module_days_sort", "recent_first")
        module_days_sort = sanitize_string(module_days_sort_param, max_length=20)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        module_days_sort = "recent_first"

    try:
        mrr_cs_email_param = request.args.get("mrr_cs_email")
        if mrr_cs_email_param:
            mrr_cs_email = validate_email(mrr_cs_email_param)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        mrr_cs_email = None

    try:
        impl_list_cs_email_param = request.args.get("impl_list_cs_email")
        if impl_list_cs_email_param:
            impl_list_cs_email = validate_email(impl_list_cs_email_param)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        impl_list_cs_email = None

    try:
        impl_list_status_param = request.args.get("impl_list_status", "todas")
        impl_list_status = sanitize_string(impl_list_status_param, max_length=20)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        impl_list_status = "todas"

    try:
        impl_list_date_field_param = request.args.get("impl_list_date_field", "data_criacao")
        impl_list_date_field = sanitize_string(impl_list_date_field_param, max_length=30)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        impl_list_date_field = "data_criacao"

    try:
        impl_list_start_date_param = request.args.get("impl_list_start_date")
        if impl_list_start_date_param:
            impl_list_start_date = validate_date(impl_list_start_date_param)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        impl_list_start_date = None

    try:
        impl_list_end_date_param = request.args.get("impl_list_end_date")
        if impl_list_end_date_param:
            impl_list_end_date = validate_date(impl_list_end_date_param)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        impl_list_end_date = None

    try:
        stop_cs_email_param = request.args.get("stop_cs_email")
        if stop_cs_email_param:
            stop_cs_email = validate_email(stop_cs_email_param)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        stop_cs_email = None

    try:
        stop_tipo_param = request.args.get("stop_tipo")
        if stop_tipo_param:
            stop_tipo = sanitize_string(stop_tipo_param, max_length=20)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        stop_tipo = None

    try:
        stop_days_sort_param = request.args.get("stop_days_sort", "recent_first")
        stop_days_sort = sanitize_string(stop_days_sort_param, max_length=20)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        stop_days_sort = "recent_first"

    try:
        cancel_cs_email_param = request.args.get("cancel_cs_email")
        if cancel_cs_email_param:
            cancel_cs_email = validate_email(cancel_cs_email_param)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        cancel_cs_email = None

    try:
        cancel_start_date_param = request.args.get("cancel_start_date")
        if cancel_start_date_param:
            cancel_start_date = validate_date(cancel_start_date_param)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        cancel_start_date = None

    try:
        cancel_end_date_param = request.args.get("cancel_end_date")
        if cancel_end_date_param:
            cancel_end_date = validate_date(cancel_end_date_param)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        cancel_end_date = None



    if user_perfil not in PERFIS_COM_GESTAO:

        cs_email = g.user_email

        task_cs_email = g.user_email
        module_cs_email = g.user_email
        mrr_cs_email = g.user_email
        impl_list_cs_email = g.user_email
        stop_cs_email = g.user_email
        cancel_cs_email = g.user_email

    base_target_cs_email = None if user_perfil in PERFIS_COM_GESTAO else g.user_email
    base_start_date = None
    base_end_date = None



    base_analytics_data = get_analytics_data(

        target_cs_email=base_target_cs_email,

        target_status="todas",

        start_date=base_start_date,

        end_date=base_end_date,

        target_tag=None,

        task_cs_email=task_cs_email,

        task_start_date=task_start_date,

        task_end_date=task_end_date,

        sort_impl_date=sort_impl_date,

        context=context,
        module_cs_email=module_cs_email,
        module_status_filter=module_status_filter,
        module_days_min=module_days_min,
        module_days_max=module_days_max,
        module_days_sort=module_days_sort,

    )

    if status_filter and status_filter != "todas":
        status_analytics_data = get_analytics_data(
            target_cs_email=cs_email,
            target_status=status_filter,
            start_date=start_date,
            end_date=base_end_date,
            target_tag=None,
            task_cs_email=task_cs_email,
            task_start_date=task_start_date,
            task_end_date=task_end_date,
            sort_impl_date=sort_impl_date,
            context=context,
            module_cs_email=module_cs_email,
            module_status_filter=module_status_filter,
            module_days_min=module_days_min,
            module_days_max=module_days_max,
            module_days_sort=module_days_sort,
        )
    else:
        status_analytics_data = base_analytics_data

    analytics_data = dict(base_analytics_data)
    analytics_data["kpi_cards"] = status_analytics_data.get("kpi_cards", {})
    merged_chart_data = dict(base_analytics_data.get("chart_data", {}))
    merged_chart_data["status_clientes"] = (
        status_analytics_data.get("chart_data", {}) or {}
    ).get("status_clientes", {})
    analytics_data["chart_data"] = merged_chart_data

    analytics_data["implantacoes_lista_detalhada"] = _filter_implantacoes_lista(
        analytics_data.get("implantacoes_lista_detalhada", []),
        cs_email=impl_list_cs_email,
        status=impl_list_status,
        date_field=impl_list_date_field,
        start_date=impl_list_start_date,
        end_date=impl_list_end_date,
    )
    analytics_data["implantacoes_paradas_lista"] = _filter_paradas_lista(
        analytics_data.get("implantacoes_paradas_lista", []),
        cs_email=stop_cs_email,
        tipo=stop_tipo,
        days_sort=stop_days_sort,
    )
    analytics_data["implantacoes_canceladas_lista"] = _filter_canceladas_lista(
        analytics_data.get("implantacoes_canceladas_lista", []),
        cs_email=cancel_cs_email,
        start_date=cancel_start_date,
        end_date=cancel_end_date,
    )



    return jsonify(

        {

            "ok": True,

            "signature": _build_analytics_signature(analytics_data),

            "updated_at": datetime.now(timezone.utc).isoformat(),

        }

    )





@analytics_bp.route("/analytics/implants_by_day")

@permission_required(PERFIS_COM_ANALYTICS)

def api_implants_by_day():

    """Retorna contagem de implantacoes finalizadas por dia no periodo."""

    try:

        cs_email = request.args.get("cs_email")

        start_date = request.args.get("start_date")

        end_date = request.args.get("end_date")



        if cs_email:

            cs_email = validate_email(cs_email)

        if start_date:

            start_date = validate_date(start_date)

        if end_date:

            end_date = validate_date(end_date)



        if g.perfil.get("perfil_acesso") not in PERFIS_COM_GESTAO:

            cs_email = g.user_email



        context = normalize_context(request.args.get("context")) or detect_current_context()

        payload = get_implants_by_day(start_date=start_date, end_date=end_date, cs_email=cs_email, context=context)

        return jsonify({"ok": True, **payload})

    except ValidationError as e:

        return jsonify({"ok": False, "error": f"Parametro invalido: {e!s}"}), 400

    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)

        return jsonify({"ok": False, "error": f"Erro interno: {e!s}"}), 500

@analytics_bp.route("/analytics/funnel")

@permission_required(PERFIS_COM_ANALYTICS)

def api_funnel():

    """Retorna contagem por status para funil em periodo opcional."""

    try:

        cs_email = request.args.get("cs_email")

        start_date = request.args.get("start_date")

        end_date = request.args.get("end_date")



        if cs_email:

            cs_email = validate_email(cs_email)

        if start_date:

            start_date = validate_date(start_date)

        if end_date:

            end_date = validate_date(end_date)



        if g.perfil.get("perfil_acesso") not in PERFIS_COM_GESTAO:

            cs_email = g.user_email



        context = normalize_context(request.args.get("context")) or detect_current_context()

        payload = get_funnel_counts(start_date=start_date, end_date=end_date, cs_email=cs_email, context=context)

        return jsonify({"ok": True, **payload})

    except ValidationError as e:

        return jsonify({"ok": False, "error": f"Parametro invalido: {e!s}"}), 400

    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)

        return jsonify({"ok": False, "error": f"Erro interno: {e!s}"}), 500





@analytics_bp.route("/analytics/gamification_rank")

@permission_required(PERFIS_COM_ANALYTICS)

def api_gamification_rank():

    """Retorna ranking de gamificacao por mes/ano."""

    try:

        month = request.args.get("month")

        year = request.args.get("year")



        month_int: int | None = None

        year_int: int | None = None



        if month:

            month_int = int(sanitize_string(str(month), max_length=2))

        if year:

            year_int = int(sanitize_string(str(year), max_length=4))



        context = normalize_context(request.args.get("context")) or detect_current_context()

        payload = get_gamification_rank(month=month_int, year=year_int, context=context)

        return jsonify({"ok": True, **payload})

    except ValueError:

        return jsonify({"ok": False, "error": "Parametros month/year devem ser inteiros."}), 400

    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)

        return jsonify({"ok": False, "error": f"Erro interno: {e!s}"}), 500

