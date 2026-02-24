from flask import current_app, flash, g, redirect, render_template, request, session, url_for

from ....blueprints.auth import login_required
from ....blueprints.grandes_contas import grandes_contas_bp
from ....common.context_profiles import resolve_context
from ....common.validation import ValidationError, sanitize_string, validate_integer
from ....constants import (
    CARGOS_RESPONSAVEL,
    FORMAS_PAGAMENTO,
    HORARIOS_FUNCIONAMENTO,
    MODALIDADES_LIST,
    NIVEIS_RECEITA,
    PERFIS_COM_CRIACAO,
    PERFIS_COM_GESTAO,
    RECORRENCIA_USADA,
    SEGUIMENTOS_LIST,
    SIM_NAO_OPTIONS,
    SISTEMAS_ANTERIORES,
    TIPOS_PLANOS,
)
from ..application.dashboard_service import get_dashboard_data, get_tags_metrics
from ..application.management_service import listar_todos_cs_com_cache


@grandes_contas_bp.route("/dashboard")
@login_required
def dashboard():
    user_email = g.user_email
    user_info = g.user
    session_key = "grandes_contas_dashboard_filters"
    saved_filters = session.get(session_key, {})
    if not isinstance(saved_filters, dict):
        saved_filters = {}

    clear_filters = request.args.get("clear_filters") in {"1", "true", "True"}
    if clear_filters:
        session.pop(session_key, None)
        saved_filters = {}

    def _arg_or_saved(name: str, default=None):
        if name in request.args:
            return request.args.get(name)
        return saved_filters.get(name, default)

    contexto_atual = resolve_context(getattr(g, "modulo_atual", "grandes_contas"))

    perfil_acesso = g.perfil.get("perfil_acesso") if g.get("perfil") else None

    # Garantia explicita: Implantador visualiza apenas sua carteira (sem filtro de dashboard)
    is_manager = False if perfil_acesso == "Implantador" else perfil_acesso in PERFIS_COM_GESTAO

    current_cs_filter = None
    sort_days = None
    try:
        cs_filter_param = _arg_or_saved("cs_filter", None)
        if cs_filter_param and is_manager:
            current_cs_filter = sanitize_string(cs_filter_param, max_length=100)
        sort_days_param = _arg_or_saved("sort_days", None)
        if sort_days_param:
            sort_days = sanitize_string(sort_days_param, max_length=4)
    except ValidationError as e:
        flash(f"Filtro invalido: {e!s}", "warning")
        current_cs_filter = None
        sort_days = None

    search_term = _arg_or_saved("search", None)
    if search_term:
        search_term = sanitize_string(search_term, max_length=100)

    tipo_filter = _arg_or_saved("tipo", None)
    if tipo_filter:
        tipo_filter = sanitize_string(tipo_filter, max_length=20)

    # Filtros de data para relatorio de tags
    start_date = _arg_or_saved("start_date")
    end_date = _arg_or_saved("end_date")
    date_type_param = _arg_or_saved("date_type")
    date_type_request_param = request.args.get("date_type")
    date_type = date_type_param or "criacao"
    if date_type not in ["criacao", "inicio", "finalizacao", "parada", "cancelamento"]:
        date_type = "criacao"
    if (
        date_type_request_param is not None
        and date_type in ["criacao", "inicio"]
        and not (start_date or end_date)
    ):
        flash("Para filtrar por Criacao ou Inicio, informe ao menos uma data.", "warning")
        date_type = "criacao"
        start_date = None
        end_date = None

    session[session_key] = {
        "search": search_term or "",
        "cs_filter": current_cs_filter or "",
        "sort_days": sort_days or "",
        "tipo": tipo_filter or "",
        "start_date": start_date or "",
        "end_date": end_date or "",
        "date_type": date_type or "criacao",
    }

    # Buscar metricas de tags
    tags_report_email = current_cs_filter if is_manager else user_email

    tags_report = {}
    try:
        tags_report = get_tags_metrics(start_date, end_date, tags_report_email, context=contexto_atual)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar tags metrics: {e}")

    try:
        # Usar versao otimizada do dashboard (consolidada)
        # Passando context='grandes_contas' para filtrar apenas este modulo
        dashboard_data, metrics = get_dashboard_data(
            user_email,
            filtered_cs_email=current_cs_filter,
            context=contexto_atual,
            search_term=search_term,
            tipo=tipo_filter,
            start_date=start_date,
            end_date=end_date,
            date_type=date_type,
        )

        if sort_days in ["asc", "desc"]:
            andamento_list = dashboard_data.get("andamento", [])
            try:
                andamento_list_sorted = sorted(
                    andamento_list, key=lambda x: (x.get("dias_passados") or 0), reverse=(sort_days == "desc")
                )
                dashboard_data["andamento"] = andamento_list_sorted
            except Exception:
                pass

        perfil_data = g.perfil if g.perfil else {}
        default_metrics = {
            "nome": user_info.get("name", user_email),
            "impl_andamento": 0,
            "impl_finalizadas": 0,
            "impl_paradas": 0,
            "progresso_medio_carteira": 0,
            "impl_andamento_total": 0,
            "implantacoes_futuras": 0,
            "implantacoes_sem_previsao": 0,
            "total_valor_sem_previsao": 0.0,
        }
        final_metrics = {**default_metrics, **perfil_data}
        final_metrics.update(metrics)
        final_metrics["impl_andamento_total"] = len(dashboard_data.get("andamento", []))

        all_cs_users = listar_todos_cs_com_cache()

        return render_template(
            "pages/grandes_contas/dashboard.html",
            user_info=user_info,
            metrics=final_metrics,
            tags_report=tags_report,
            current_start_date=start_date,
            current_end_date=end_date,
            implantacoes_andamento=dashboard_data.get("andamento", []),
            implantacoes_novas=dashboard_data.get("novas", []),
            implantacoes_futuras=dashboard_data.get("futuras", []),
            implantacoes_sem_previsao=dashboard_data.get("sem_previsao", []),
            implantacoes_finalizadas=dashboard_data.get("finalizadas", []),
            implantacoes_paradas=dashboard_data.get("paradas", []),
            implantacoes_canceladas=dashboard_data.get("canceladas", []),
            cargos_responsavel=CARGOS_RESPONSAVEL,
            PERFIS_COM_CRIACAO=PERFIS_COM_CRIACAO,
            NIVEIS_RECEITA=NIVEIS_RECEITA,
            SEGUIMENTOS_LIST=SEGUIMENTOS_LIST,
            TIPOS_PLANOS=TIPOS_PLANOS,
            MODALIDADES_LIST=MODALIDADES_LIST,
            HORARIOS_FUNCIONAMENTO=HORARIOS_FUNCIONAMENTO,
            FORMAS_PAGAMENTO=FORMAS_PAGAMENTO,
            SISTEMAS_ANTERIORES=SISTEMAS_ANTERIORES,
            RECORRENCIA_USADA=RECORRENCIA_USADA,
            SIM_NAO_OPTIONS=SIM_NAO_OPTIONS,
            all_cs_users=all_cs_users,
            is_manager=is_manager,
            current_cs_filter=current_cs_filter,
            sort_days=sort_days,
            current_search=search_term,
            current_tipo=tipo_filter,
            current_date_type=date_type,
            dashboard_data=dashboard_data,
        )

    except Exception as e:
        flash("Erro ao carregar dados do dashboard.", "error")
        current_app.logger.error(f"Erro no dashboard: {e}", exc_info=True)

        return render_template(
            "pages/grandes_contas/dashboard.html",
            user_info=user_info,
            metrics={},
            implantacoes_andamento=[],
            implantacoes_novas=[],
            implantacoes_futuras=[],
            implantacoes_sem_previsao=[],
            implantacoes_finalizadas=[],
            implantacoes_paradas=[],
            implantacoes_canceladas=[],
            dashboard_data={
                "total_ativos": [],
                "novas": [],
                "andamento": [],
                "paradas": [],
                "futuras": [],
                "sem_previsao": [],
                "finalizadas": [],
                "canceladas": [],
            },
            error="Falha.",
        )


@grandes_contas_bp.route("/implantacao/<int:impl_id>")
@login_required
def ver_implantacao(impl_id):
    from ....config.logging_config import get_logger
    from ....modules.implantacao.domain import get_implantacao_details

    logger = get_logger("grandes_contas")

    logger.info(f"Tentando acessar implantacao ID {impl_id} - Usuario: {g.user_email}")

    try:
        impl_id = validate_integer(impl_id, min_value=1)
        logger.info(f"ID validado: {impl_id}")
    except ValidationError as e:
        logger.error(f"ID de implantacao invalido: {e!s}")
        flash(f"ID de implantacao invalido: {e!s}", "error")
        return redirect(url_for("grandes_contas.dashboard"))

    try:
        logger.info(f"Chamando get_implantacao_details para ID {impl_id}")
        user_perfil = g.perfil if hasattr(g, "perfil") and g.perfil else {}
        plano_historico_id = request.args.get("plano_historico_id", type=int)
        context_data = get_implantacao_details(
            impl_id=impl_id,
            usuario_cs_email=g.user_email,
            user_perfil=user_perfil,
            plano_historico_id=plano_historico_id,
        )
        logger.info(f"Dados da implantacao {impl_id} obtidos com sucesso")

        return render_template("pages/grandes_contas/implantacao_detalhes.html", **context_data)

    except ValueError as e:
        logger.warning(f"Acesso negado a implantacao {impl_id}: {e!s}")
        flash(str(e), "error")
        return redirect(url_for("grandes_contas.dashboard"))

    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.error(f"Erro ao carregar detalhes da implantacao ID {impl_id}: {e}\n{error_trace}")
        flash(f"Erro ao carregar detalhes da implantacao: {e!s}", "error")
        return redirect(url_for("grandes_contas.dashboard"))
