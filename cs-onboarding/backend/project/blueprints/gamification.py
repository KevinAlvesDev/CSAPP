import calendar
from datetime import datetime, timezone
import logging
import time
logger = logging.getLogger(__name__)

from typing import cast
from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from flask_limiter.util import get_remote_address
from werkzeug.routing import BuildError

from ..blueprints.auth import permission_required
from ..common.context_navigation import redirect_to_current_dashboard
from ..common.validation import ValidationError, sanitize_string, validate_email, validate_integer
from ..constants import PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..modules.gamification.application.gamification_service import (
    _get_all_gamification_rules_grouped,
    _get_gamification_automatic_data_bulk,
    criar_regra_gamificacao,
    deletar_regra_gamificacao,
    get_all_cs_users_for_gamification,
    get_all_metricas_mensais,
    get_participantes,
    toggle_participante,
    get_gamification_report_data,
    obter_metricas_mensais,
    salvar_metricas_mensais,
    salvar_regras_gamificacao,
)

gamification_bp = Blueprint("gamification", __name__, url_prefix="/gamification")


@gamification_bp.route("/rules")
@permission_required(PERFIS_COM_GESTAO)
def manage_gamification_rules():
    """Rota para configurar regras e pontuações da gamificação."""
    context = request.args.get("context")
    valid_contexts = ("onboarding", "ongoing", "grandes_contas")
    if context and context not in valid_contexts:
        context = None

    regras_agrupadas = _get_all_gamification_rules_grouped()
    return render_template(
        "pages/gamification_rules_form.html",
        regras_agrupadas=regras_agrupadas,
        current_context=context,
    )


@gamification_bp.route("/save-rules-modal", methods=["POST"])
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def save_gamification_rules_from_modal():
    """
    Rota (apenas POST) para salvar as regras de gamificação
    enviadas pelo formulário dentro do modal em base.html.
    """
    fallback_redirect = redirect_to_current_dashboard()

    try:
        updates_to_make = []
        for key, value in request.form.items():
            if key.startswith("regra-"):
                regra_id = key.replace("regra-", "")
                try:
                    regra_id = sanitize_string(regra_id, max_length=50)
                    valor_pontos = validate_integer(value, min_value=-1000, max_value=10000)
                    updates_to_make.append((valor_pontos, regra_id))
                except ValidationError:
                    pass
                except (ValueError, TypeError):
                    pass

        if not updates_to_make:
            flash("Nenhum dado válido foi enviado para atualização.", "warning")
            return fallback_redirect

        total_atualizado = salvar_regras_gamificacao(updates_to_make)
        flash(f"{total_atualizado} regras de pontuação foram atualizadas com sucesso!", "success")

    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        flash(f"Erro ao salvar as regras: {e}", "error")

    return fallback_redirect


@gamification_bp.route("/rules/add", methods=["POST"])
@permission_required(PERFIS_COM_GESTAO)
def add_gamification_rule():
    """Rota para adicionar uma regra de gamificação completamente personalizada."""
    context = request.args.get("context")
    try:
        regra_id = request.form.get("regra_id", "").strip()
        categoria = request.form.get("categoria", "Personalizada").strip()
        descricao = request.form.get("descricao", "").strip()
        valor_pontos = request.form.get("valor_pontos")
        tipo_valor = request.form.get("tipo_valor", "pontos")

        if not regra_id or not descricao or not valor_pontos:
            flash("Preencha todos os campos obrigatórios para criar a regra.", "warning")
            return redirect(url_for("gamification.manage_gamification_rules", context=context))

        valor_pontos_val = validate_integer(valor_pontos, min_value=-10000, max_value=10000)
        valor_pontos_int = int(valor_pontos_val) if valor_pontos_val is not None else 0

        # Converter regra_id para padrão snake_case sem espaços
        regra_id_clean = regra_id.lower().replace(" ", "_").replace("-", "_")

        criar_regra_gamificacao(regra_id_clean, categoria, descricao, valor_pontos_int, tipo_valor)
        flash(f"Regra '{descricao}' criada com sucesso!", "success")
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        flash(f"Erro ao criar regra: {e}", "error")

    return redirect(url_for("gamification.manage_gamification_rules", context=context))


@gamification_bp.route("/rules/delete/<path:regra_id>", methods=["POST"])
@permission_required(PERFIS_COM_GESTAO)
def delete_gamification_rule(regra_id):
    """Rota para deletar uma regra de gamificação."""
    context = request.args.get("context")
    try:
        deletar_regra_gamificacao(regra_id)
        flash("Regra deletada com sucesso.", "success")
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        flash(f"Erro ao deletar regra: {e}", "error")

    return redirect(url_for("gamification.manage_gamification_rules", context=context))



_VALID_CONTEXTS = ("onboarding", "ongoing", "grandes_contas")

_FLOAT_METRIC_FIELDS = [
    "nota_qualidade", "assiduidade", "planos_sucesso_perc", "satisfacao_processo",
    "tma_medio_mes", "reunioes_concluidas_dia_media", "acoes_concluidas_dia_media",
]
_INT_METRIC_FIELDS = [
    "reclamacoes", "perda_prazo", "nao_preenchimento", "elogios", "recomendacoes",
    "certificacoes", "treinamentos_pacto_part", "treinamentos_pacto_aplic",
    "reunioes_presenciais", "cancelamentos_resp", "nao_envolvimento",
    "desc_incompreensivel", "hora_extra", "perda_sla_grupo", "finalizacao_incompleta",
    "impl_finalizadas_mes", "impl_iniciadas_mes",
]
_PERCENTUAL_FIELDS = ["nota_qualidade", "assiduidade", "planos_sucesso_perc", "satisfacao_processo"]


def _load_automatic_metrics(target_cs_email, target_mes, target_ano, context):
    """Busca e formata as métricas automáticas do CS para o período indicado."""
    primeiro_dia = datetime(target_ano, target_mes, 1)
    dias_no_mes = calendar.monthrange(target_ano, target_mes)[1]
    ultimo_dia = datetime(target_ano, target_mes, dias_no_mes)
    fim_ultimo_dia = datetime.combine(ultimo_dia, datetime.max.time())

    tma_data_map, iniciadas_map, tarefas_map = _get_gamification_automatic_data_bulk(
        target_mes, target_ano,
        primeiro_dia.isoformat(), fim_ultimo_dia.isoformat(),
        target_cs_email, context=context,
    )

    dados_tma = tma_data_map.get(target_cs_email, {})
    count_finalizadas = dados_tma.get("count", 0)
    tma_total_dias = dados_tma.get("total_dias", 0)
    tma_medio = round(tma_total_dias / count_finalizadas, 1) if count_finalizadas > 0 else 0.0

    dados_tarefas = tarefas_map.get(target_cs_email, {})
    media_reunioes_dia = round(dados_tarefas.get("Reunião", 0) / dias_no_mes, 2) if dias_no_mes > 0 else 0.0
    media_acoes_dia = round(dados_tarefas.get("Ação interna", 0) / dias_no_mes, 2) if dias_no_mes > 0 else 0.0

    return {
        "impl_finalizadas_mes": count_finalizadas,
        "tma_medio_mes_raw": tma_medio,
        "tma_medio_mes": f"{tma_medio} dias" if tma_medio > 0 else "N/A",
        "impl_iniciadas_mes": iniciadas_map.get(target_cs_email, 0),
        "reunioes_concluidas_dia_media": f"{media_reunioes_dia:.2f}",
        "acoes_concluidas_dia_media": f"{media_acoes_dia:.2f}",
    }


def _post_needs_automatic_defaults():
    """Retorna True quando o POST depende de preencher campos autom�ticos."""
    auto_fields = (
        "tma_medio_mes",
        "impl_finalizadas_mes",
        "impl_iniciadas_mes",
        "reunioes_concluidas_dia_media",
        "acoes_concluidas_dia_media",
    )
    for field in auto_fields:
        value = request.form.get(field)
        if value is None or str(value).strip() == "":
            return True
    return False


def _automatic_metrics_from_saved(metricas_atuais):
    """Fallback r�pido usando valores j� salvos no m�s (evita rec�lculo pesado no POST)."""
    try:
        tma_raw = float(metricas_atuais.get("tma_medio_mes") or 0)
    except (TypeError, ValueError):
        tma_raw = 0.0
    try:
        reunioes_media = float(metricas_atuais.get("reunioes_concluidas_dia_media") or 0)
    except (TypeError, ValueError):
        reunioes_media = 0.0
    try:
        acoes_media = float(metricas_atuais.get("acoes_concluidas_dia_media") or 0)
    except (TypeError, ValueError):
        acoes_media = 0.0

    return {
        "impl_finalizadas_mes": int(metricas_atuais.get("impl_finalizadas_mes") or 0),
        "tma_medio_mes_raw": tma_raw,
        "tma_medio_mes": f"{tma_raw} dias" if tma_raw > 0 else "N/A",
        "impl_iniciadas_mes": int(metricas_atuais.get("impl_iniciadas_mes") or 0),
        "reunioes_concluidas_dia_media": f"{reunioes_media:.2f}",
        "acoes_concluidas_dia_media": f"{acoes_media:.2f}",
    }

def _parse_metrics_form(metricas_automaticas):
    """
    Lê e converte os campos do formulário POST para os tipos corretos.
    Retorna (data_to_save, error_message_or_None).
    """
    data_to_save: dict = {}

    for field in _FLOAT_METRIC_FIELDS:
        value_str = request.form.get(field)
        if value_str:
            try:
                data_to_save[field] = float(value_str)
            except ValueError:
                data_to_save[field] = 0.0
        else:
            data_to_save[field] = None

    # Some bonus fields use abbreviated names in the HTML form (derived via replace('bonus_', ''))
    _FORM_FIELD_ALIASES = {
        "treinamentos_pacto_part": "trein_pacto_part",
        "treinamentos_pacto_aplic": "trein_pacto_aplic",
    }
    for field in _INT_METRIC_FIELDS:
        form_name = _FORM_FIELD_ALIASES.get(field, field)
        value_str = request.form.get(form_name)
        try:
            data_to_save[field] = int(value_str) if value_str else 0
        except ValueError:
            data_to_save[field] = 0

    # Usar métricas automáticas apenas quando o usuário não preencheu o campo no formulário
    for auto_key, form_key, conv in [
        ("tma_medio_mes_raw",              "tma_medio_mes",                float),
        ("impl_finalizadas_mes",           "impl_finalizadas_mes",         int),
        ("impl_iniciadas_mes",             "impl_iniciadas_mes",           int),
        ("reunioes_concluidas_dia_media",  "reunioes_concluidas_dia_media", float),
        ("acoes_concluidas_dia_media",     "acoes_concluidas_dia_media",   float),
    ]:
        # Só aplica automático se o usuário deixou o campo vazio no formulário
        if request.form.get(form_key):
            continue
        raw = metricas_automaticas.get(auto_key, 0) or 0
        try:
            data_to_save[form_key] = conv(raw)
        except (ValueError, TypeError):
            pass

    return data_to_save


def _validate_metrics_data(data_to_save, target_cs_email, target_mes, target_ano, context):
    """
    Valida regras de negócio dos dados do formulário.
    Retorna redirect response se inválido, ou None se válido.
    """
    redirect_url = url_for(
        "gamification.manage_gamification_metrics",
        cs_email=target_cs_email, mes=target_mes, ano=target_ano, context=context,
    )

    for p in _PERCENTUAL_FIELDS:
        v = data_to_save.get(p)
        if v is not None and not (0 <= cast(float, v) <= 100):
            flash(f"Valor inválido para {p.replace('_', ' ')}: {v}. Deve estar entre 0 e 100.", "error")
            return redirect(redirect_url)

    ocorrencias_fields = [f for f in _INT_METRIC_FIELDS if f not in ("impl_finalizadas_mes", "impl_iniciadas_mes")]
    for f in ocorrencias_fields:
        v = data_to_save.get(f)
        if not isinstance(v, int):
            continue
        if v < 0:
            flash(f"O valor para {f.replace('_', ' ')} não pode ser negativo.", "error")
            return redirect(redirect_url)
        if v > 1000:
            flash(f"Valor muito alto para {f.replace('_', ' ')}: {v}. Verifique e tente novamente.", "error")
            return redirect(redirect_url)

    return None


@gamification_bp.route("/metrics", methods=["GET", "POST"])
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def manage_gamification_metrics():
    """Rota para gestores inserirem/atualizarem as métricas manuais de um CS."""
    context = request.args.get("context")
    if context and context not in _VALID_CONTEXTS:
        context = None

    all_cs_users = get_all_cs_users_for_gamification(context=context)
    regras_agrupadas = _get_all_gamification_rules_grouped()

    target_cs_email = None
    try:
        cs_email_param = request.args.get("cs_email")
        if cs_email_param:
            target_cs_email = validate_email(cs_email_param)
    except ValidationError as e:
        flash(f"Email inválido no filtro: {e!s}", "warning")

    hoje = datetime.now(timezone.utc)
    try:
        val_mes = validate_integer(request.values.get("mes", hoje.month), min_value=1, max_value=12)
        target_mes = int(val_mes) if val_mes is not None else hoje.month
        val_ano = validate_integer(request.values.get("ano", hoje.year), min_value=2020, max_value=hoje.year + 10)
        target_ano = int(val_ano) if val_ano is not None else hoje.year
    except ValidationError:
        target_mes, target_ano = hoje.month, hoje.year

    metricas_atuais = {}
    metricas_automaticas = {}

    if target_cs_email and request.method != "POST":
        metricas_atuais = dict(obter_metricas_mensais(target_cs_email, target_mes, target_ano) or {})
        # Add short-name aliases so the template (which derives names via replace('bonus_', '')) finds the values
        metricas_atuais["trein_pacto_part"] = metricas_atuais.get("treinamentos_pacto_part", 0)
        metricas_atuais["trein_pacto_aplic"] = metricas_atuais.get("treinamentos_pacto_aplic", 0)
        try:
            metricas_automaticas = _load_automatic_metrics(target_cs_email, target_mes, target_ano, context)
        except Exception as e_auto:
            logger.exception("Unhandled exception", exc_info=True)
            flash(f"Erro ao buscar dados automáticos: {e_auto}", "warning")

    if request.method == "POST":
        if not target_cs_email:
            flash("É necessário selecionar um usuário para salvar as métricas.", "error")
            return redirect(url_for("gamification.manage_gamification_metrics", context=context))

        try:
            metricas_atuais = dict(obter_metricas_mensais(target_cs_email, target_mes, target_ano) or {})
            metricas_atuais["trein_pacto_part"] = metricas_atuais.get("treinamentos_pacto_part", 0)
            metricas_atuais["trein_pacto_aplic"] = metricas_atuais.get("treinamentos_pacto_aplic", 0)

            if _post_needs_automatic_defaults():
                metricas_automaticas = _automatic_metrics_from_saved(metricas_atuais)
                if not metricas_atuais:
                    metricas_automaticas = _load_automatic_metrics(target_cs_email, target_mes, target_ano, context)

            data_to_save = {
                "usuario_cs": target_cs_email,
                "mes": target_mes,
                "ano": target_ano,
                "data_registro": datetime.now(timezone.utc),
                **_parse_metrics_form(metricas_automaticas),
            }

            validation_redirect = _validate_metrics_data(data_to_save, target_cs_email, target_mes, target_ano, context)
            if validation_redirect:
                return validation_redirect

            existing_record_id = metricas_atuais.get("id")
            salvar_metricas_mensais(data_to_save, existing_record_id)

            flash(
                "Métricas manuais atualizadas com sucesso!" if existing_record_id else "Métricas manuais salvas com sucesso!",
                "success",
            )
            return redirect(url_for(
                "gamification.manage_gamification_metrics",
                cs_email=target_cs_email, mes=target_mes, ano=target_ano, context=context,
            ))

        except Exception as e:
            logger.exception("Unhandled exception", exc_info=True)
            flash(f"Erro ao salvar métricas: {e}", "error")

    return render_template(
        "pages/gamification_metrics_form.html",
        all_cs_users=all_cs_users,
        current_cs_email=target_cs_email,
        current_mes=target_mes,
        current_ano=target_ano,
        metricas_atuais=metricas_atuais,
        metricas_automaticas=metricas_automaticas,
        current_year=hoje.year,
        regras_agrupadas=regras_agrupadas,
        current_context=context,
    )


@gamification_bp.route("/metrics/overview")
@permission_required(PERFIS_COM_GESTAO)
def metrics_overview():
    """Visão geral de todos os lançamentos mensais — permite ao gestor ver e corrigir métricas."""
    context = request.args.get("context")
    if context and context not in _VALID_CONTEXTS:
        context = None

    hoje = datetime.now(timezone.utc)
    try:
        val_mes = validate_integer(request.args.get("mes", hoje.month), min_value=1, max_value=12)
        target_mes = int(val_mes) if val_mes is not None else hoje.month
        val_ano = validate_integer(request.args.get("ano", hoje.year), min_value=2020, max_value=hoje.year + 10)
        target_ano = int(val_ano) if val_ano is not None else hoje.year
    except ValidationError:
        target_mes, target_ano = hoje.month, hoje.year

    all_cs_users = get_all_cs_users_for_gamification(context=context)
    metricas_rows = get_all_metricas_mensais(target_mes, target_ano, context=context)
    metricas_map = {row["usuario_cs"]: row for row in metricas_rows if isinstance(row, dict)}
    participantes_map = get_participantes(context=context)  # {email: ativo} — ausente = ativo por padrão

    rows = []
    for cs in all_cs_users:
        email = cs.get("usuario")
        metrica = metricas_map.get(email) or {}
        # Se não há registro em gamificacao_participantes, o usuário participa por padrão
        participando = participantes_map.get(email, True)
        rows.append({
            "email": email,
            "nome": cs.get("nome") or email,
            "cargo": cs.get("cargo") or "",
            "foto_url": cs.get("foto_url") or "",
            "participando": participando,
            "tem_lancamento": bool(metrica),
            "nota_qualidade": metrica.get("nota_qualidade"),
            "assiduidade": metrica.get("assiduidade"),
            "planos_sucesso_perc": metrica.get("planos_sucesso_perc"),
            "impl_finalizadas_mes": metrica.get("impl_finalizadas_mes"),
            "pontuacao_calculada": metrica.get("pontuacao_calculada"),
            "elegivel": metrica.get("elegivel"),
        })

    # Ordenar: participando primeiro, depois com lançamento, depois por nome
    rows.sort(key=lambda r: (0 if r["participando"] else 1, 0 if r["tem_lancamento"] else 1, r["nome"]))

    return render_template(
        "pages/gamification_metrics_overview.html",
        rows=rows,
        current_mes=target_mes,
        current_ano=target_ano,
        current_year=hoje.year,
        current_context=context,
    )


@gamification_bp.route("/metrics/toggle-participante", methods=["POST"])
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("60 per minute", key_func=lambda: g.user_email or get_remote_address())
def toggle_participante_route():
    """Alterna a participação de um CS na gamificação."""
    from flask import jsonify
    context = request.args.get("context")
    if context and context not in _VALID_CONTEXTS:
        context = None

    try:
        cs_email = validate_email(request.form.get("cs_email", ""))
    except (ValidationError, Exception):
        return jsonify({"error": "Email inválido"}), 400

    novo_estado = toggle_participante(cs_email, context=context)
    if novo_estado is None:
        return jsonify({"error": "Funcionalidade indisponível: tabela gamificacao_participantes não existe."}), 503
    return jsonify({"ativo": novo_estado, "cs_email": cs_email})


@gamification_bp.route("/report")
@permission_required(PERFIS_COM_GESTAO)
def gamification_report():
    """Rota para exibir o relatório de pontuação da gamificação."""
    # Obter contexto do request
    context = request.args.get("context")
    valid_contexts = ("onboarding", "ongoing", "grandes_contas")
    if context and context not in valid_contexts:
        context = None  # Ignorar valores inválidos

    all_cs_users = get_all_cs_users_for_gamification(context=context)

    hoje = datetime.now(timezone.utc)

    default_mes = int(request.args.get("mes", hoje.month))
    default_ano = int(request.args.get("ano", hoje.year))

    try:
        val_sel_month = validate_integer(default_mes, min_value=1, max_value=12)
        selected_month = int(val_sel_month) if val_sel_month is not None else hoje.month
        val_sel_year = validate_integer(default_ano, min_value=2020, max_value=hoje.year + 10)
        selected_year = int(val_sel_year) if val_sel_year is not None else hoje.year
    except ValidationError:
        selected_month = hoje.month
        selected_year = hoje.year

    target_cs_email = request.args.get("cs_email")
    if target_cs_email:
        try:
            target_cs_email = validate_email(target_cs_email)
        except ValidationError:
            flash("Email inválido no filtro do relatório.", "warning")
            target_cs_email = None

    try:
        start_report = time.perf_counter()
        report_data_sorted = get_gamification_report_data(
            selected_month, selected_year, target_cs_email, all_cs_users_list=all_cs_users, context=context
        )
        elapsed_ms = (time.perf_counter() - start_report) * 1000
        current_app.logger.info(
            "Gamification report generated in %.1fms (context=%s, mes=%s, ano=%s, filtro_cs=%s, rows=%s)",
            elapsed_ms,
            context or "onboarding",
            selected_month,
            selected_year,
            bool(target_cs_email),
            len(report_data_sorted),
        )
    except Exception as e:
        current_app.logger.error(f"ERRO CRÍTICO ao gerar relatório de gamificação: {e}", exc_info=True)
        flash(f"Erro ao gerar relatório: {e}", "error")
        report_data_sorted = []

    try:
        metrics_overview_url = url_for(
            "gamification.metrics_overview",
            context=context,
            mes=selected_month,
            ano=selected_year,
        )
    except BuildError:
        current_app.logger.warning(
            "Endpoint gamification.metrics_overview indisponível; usando fallback para manage_gamification_metrics."
        )
        metrics_overview_url = url_for(
            "gamification.manage_gamification_metrics",
            context=context,
            mes=selected_month,
            ano=selected_year,
        )

    return render_template(
        "pages/gamification_report.html",
        report_data=report_data_sorted,
        all_cs_users=all_cs_users,
        current_cs_email=target_cs_email,
        selected_month=selected_month,
        selected_year=selected_year,
        metrics_overview_url=metrics_overview_url,
        current_year=hoje.year,
        current_context=context,
    )
