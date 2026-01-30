import calendar
from datetime import datetime

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from flask_limiter.util import get_remote_address

from ..blueprints.auth import permission_required
from ..common.validation import ValidationError, sanitize_string, validate_email, validate_integer
from ..constants import PERFIS_COM_GESTAO
from ..core.extensions import limiter
from ..domain.gamification_service import (
    _get_all_gamification_rules_grouped,
    _get_gamification_automatic_data_bulk,
    clear_gamification_cache,
    get_all_cs_users_for_gamification,
    get_gamification_report_data,
    obter_metricas_mensais,
    salvar_metricas_mensais,
    salvar_regras_gamificacao,
)

gamification_bp = Blueprint("gamification", __name__, url_prefix="/gamification")


@gamification_bp.route("/save-rules-modal", methods=["POST"])
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def save_gamification_rules_from_modal():
    """
    Rota (apenas POST) para salvar as regras de gamificação
    enviadas pelo formulário dentro do modal em base.html.
    """
    fallback_redirect = redirect(request.referrer or url_for("onboarding.dashboard"))

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
        flash(f"Erro ao salvar as regras: {e}", "error")

    return fallback_redirect


@gamification_bp.route("/metrics", methods=["GET", "POST"])
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def manage_gamification_metrics():
    """Rota para gestores inserirem/atualizarem as métricas manuais de um CS."""

    all_cs_users = get_all_cs_users_for_gamification()
    regras_agrupadas = _get_all_gamification_rules_grouped()

    target_cs_email = None
    try:
        cs_email_param = request.args.get("cs_email")
        if cs_email_param:
            target_cs_email = validate_email(cs_email_param)
    except ValidationError as e:
        flash(f"Email inválido no filtro: {str(e)}", "warning")
        target_cs_email = None

    hoje = datetime.now()
    default_mes = hoje.month
    default_ano = hoje.year
    max_ano = hoje.year + 10

    try:
        target_mes = validate_integer(request.values.get("mes", default_mes), min_value=1, max_value=12)
        target_ano = validate_integer(request.values.get("ano", default_ano), min_value=2020, max_value=max_ano)
    except ValidationError:
        target_mes = default_mes
        target_ano = default_ano

    metricas_atuais = None
    metricas_automaticas = {}

    # Obter contexto do request
    context = request.args.get("context")
    valid_contexts = ("onboarding", "ongoing", "grandes_contas")
    if context and context not in valid_contexts:
        context = None  # Ignorar valores inválidos

    if target_cs_email:
        metricas_atuais = obter_metricas_mensais(target_cs_email, target_mes, target_ano)

        if context and context not in valid_contexts:
            context = None  # Ignorar valores inválidos

        try:
            primeiro_dia = datetime(target_ano, target_mes, 1)
            dias_no_mes = calendar.monthrange(target_ano, target_mes)[1]
            ultimo_dia = datetime(target_ano, target_mes, dias_no_mes)
            fim_ultimo_dia = datetime.combine(ultimo_dia, datetime.max.time())

            primeiro_dia_str = primeiro_dia.isoformat()
            fim_ultimo_dia_str = fim_ultimo_dia.isoformat()

            tma_data_map, iniciadas_map, tarefas_map = _get_gamification_automatic_data_bulk(
                target_mes, target_ano, primeiro_dia_str, fim_ultimo_dia_str, target_cs_email, context=context
            )

            dados_tma = tma_data_map.get(target_cs_email, {})
            count_iniciadas = iniciadas_map.get(target_cs_email, 0)
            dados_tarefas = tarefas_map.get(target_cs_email, {})

            count_finalizadas = dados_tma.get("count", 0)
            tma_total_dias = dados_tma.get("total_dias", 0)
            tma_medio = round(tma_total_dias / count_finalizadas, 1) if count_finalizadas > 0 else 0.0

            count_acao_interna = dados_tarefas.get("Ação interna", 0)
            count_reuniao = dados_tarefas.get("Reunião", 0)

            media_reunioes_dia = round(count_reuniao / dias_no_mes, 2) if dias_no_mes > 0 else 0.0
            media_acoes_dia = round(count_acao_interna / dias_no_mes, 2) if dias_no_mes > 0 else 0.0

            metricas_automaticas = {
                "impl_finalizadas_mes": count_finalizadas,
                "tma_medio_mes_raw": tma_medio,
                "tma_medio_mes": f"{tma_medio} dias" if tma_medio > 0 else "N/A",
                "impl_iniciadas_mes": count_iniciadas,
                "reunioes_concluidas_dia_media": f"{media_reunioes_dia:.2f}",
                "acoes_concluidas_dia_media": f"{media_acoes_dia:.2f}",
            }

        except Exception as e_auto:
            flash(f"Erro ao buscar dados automáticos: {e_auto}", "warning")

    if not metricas_atuais:
        metricas_atuais = {}

    if request.method == "POST":
        if not target_cs_email:
            flash("É necessário selecionar um usuário para salvar as métricas.", "error")
            return redirect(url_for("gamification.manage_gamification_metrics", context=context))

        try:
            data_to_save = {
                "usuario_cs": target_cs_email,
                "mes": target_mes,
                "ano": target_ano,
                "data_registro": datetime.now(),
            }

            float_fields = [
                "nota_qualidade",
                "assiduidade",
                "planos_sucesso_perc",
                "satisfacao_processo",
                "tma_medio_mes",
                "reunioes_concluidas_dia_media",
                "acoes_concluidas_dia_media",
            ]
            int_fields = [
                "reclamacoes",
                "perda_prazo",
                "nao_preenchimento",
                "elogios",
                "recomendacoes",
                "certificacoes",
                "treinamentos_pacto_part",
                "treinamentos_pacto_aplic",
                "reunioes_presenciais",
                "cancelamentos_resp",
                "nao_envolvimento",
                "desc_incompreensivel",
                "hora_extra",
                "perda_sla_grupo",
                "finalizacao_incompleta",
                "impl_finalizadas_mes",
                "impl_iniciadas_mes",
            ]

            for field in float_fields:
                value_str = request.form.get(field)
                if value_str:
                    try:
                        data_to_save[field] = float(value_str)
                    except ValueError:
                        data_to_save[field] = None
                else:
                    data_to_save[field] = None

            for field in int_fields:
                value_str = request.form.get(field)
                try:
                    if value_str is not None and value_str != "":
                        data_to_save[field] = int(value_str)
                    else:
                        data_to_save[field] = None
                except ValueError:
                    data_to_save[field] = None

            percentuais = ["nota_qualidade", "assiduidade", "planos_sucesso_perc", "satisfacao_processo"]
            for p in percentuais:
                v = data_to_save.get(p)
                if v is not None and (v < 0 or v > 100):
                    flash(f"Valor inválido para {p.replace('_', ' ')}: {v}. Deve estar entre 0 e 100.", "error")
                    return redirect(
                        url_for(
                            "gamification.manage_gamification_metrics",
                            cs_email=target_cs_email,
                            mes=target_mes,
                            ano=target_ano,
                            context=context,
                        )
                    )

            try:
                tma_raw = float(metricas_automaticas.get("tma_medio_mes_raw", 0) or 0)
                data_to_save["tma_medio_mes"] = tma_raw
            except Exception:
                data_to_save["tma_medio_mes"] = None

            try:
                impl_finalizadas_auto = int(metricas_automaticas.get("impl_finalizadas_mes", 0) or 0)
                data_to_save["impl_finalizadas_mes"] = impl_finalizadas_auto
            except Exception:
                pass

            try:
                impl_iniciadas_auto = int(metricas_automaticas.get("impl_iniciadas_mes", 0) or 0)
                data_to_save["impl_iniciadas_mes"] = impl_iniciadas_auto
            except Exception:
                pass

            try:
                reunioes_media_auto = float(metricas_automaticas.get("reunioes_concluidas_dia_media", 0) or 0)
                acoes_media_auto = float(metricas_automaticas.get("acoes_concluidas_dia_media", 0) or 0)
                data_to_save["reunioes_concluidas_dia_media"] = reunioes_media_auto
                data_to_save["acoes_concluidas_dia_media"] = acoes_media_auto
            except Exception:
                pass

            ocorrencias_fields = [f for f in int_fields if f not in ["impl_finalizadas_mes", "impl_iniciadas_mes"]]
            for f in ocorrencias_fields:
                v = data_to_save.get(f)
                if v is not None:
                    if v < 0:
                        flash(f"O valor para {f.replace('_', ' ')} não pode ser negativo.", "error")
                        return redirect(
                            url_for(
                                "gamification.manage_gamification_metrics",
                                cs_email=target_cs_email,
                                mes=target_mes,
                                ano=target_ano,
                                context=context,
                            )
                        )
                    if v > 1000:
                        flash(
                            f"Valor muito alto para {f.replace('_', ' ')}: {v}. Verifique e tente novamente.", "error"
                        )
                        return redirect(
                            url_for(
                                "gamification.manage_gamification_metrics",
                                cs_email=target_cs_email,
                                mes=target_mes,
                                ano=target_ano,
                                context=context,
                            )
                        )

            existing_record_id = metricas_atuais.get("id") if metricas_atuais else None

            salvar_metricas_mensais(data_to_save, existing_record_id)

            flash(
                "Métricas manuais atualizadas com sucesso!"
                if existing_record_id
                else "Métricas manuais salvas com sucesso!",
                "success",
            )
            return redirect(
                url_for(
                    "gamification.manage_gamification_metrics", cs_email=target_cs_email, mes=target_mes, ano=target_ano, context=context
                )
            )

        except Exception as e:
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
    )


@gamification_bp.route("/report")
@permission_required(PERFIS_COM_GESTAO)
def gamification_report():
    """Rota para exibir o relatório de pontuação da gamificação."""

    all_cs_users = get_all_cs_users_for_gamification()

    hoje = datetime.now()

    default_mes = int(request.args.get("mes", hoje.month))
    default_ano = int(request.args.get("ano", hoje.year))

    try:
        selected_month = validate_integer(default_mes, min_value=1, max_value=12)
        selected_year = validate_integer(default_ano, min_value=2020, max_value=hoje.year + 10)
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

    # Obter contexto do request
    context = request.args.get("context")
    valid_contexts = ("onboarding", "ongoing", "grandes_contas")
    if context and context not in valid_contexts:
        context = None  # Ignorar valores inválidos

    try:
        # Limpar cache antes de gerar relatório para garantir dados atualizados
        clear_gamification_cache()
        report_data_sorted = get_gamification_report_data(
            selected_month, selected_year, target_cs_email, all_cs_users_list=all_cs_users, context=context
        )
    except Exception as e:
        current_app.logger.error(f"ERRO CRÍTICO ao gerar relatório de gamificação: {e}", exc_info=True)
        flash(f"Erro ao gerar relatório: {e}", "error")
        report_data_sorted = []

    return render_template(
        "pages/gamification_report.html",
        report_data=report_data_sorted,
        all_cs_users=all_cs_users,
        current_cs_email=target_cs_email,
        selected_month=selected_month,
        selected_year=selected_year,
        current_year=hoje.year,
    )
