"""
Modulo de Relatorio de Gamificacao.
Geracao do relatorio mensal com calculo em lote.
"""

import calendar
import logging
from datetime import date, datetime, timezone

from ....common.context_profiles import resolve_context
from ....db import execute_db, query_db
from .calculator import _calculate_user_gamification_score
from .metrics import _get_gamification_automatic_data_bulk
from .rules import _get_gamification_rules_as_dict

logger = logging.getLogger(__name__)


def get_gamification_report_data(mes, ano, target_cs_email=None, all_cs_users_list=None, context=None):
    """
    Busca e calcula o relatorio de gamificacao em lote.

    Args:
        mes: Mes de referencia
        ano: Ano de referencia
        target_cs_email: Email especifico de um CS (opcional)
        all_cs_users_list: Lista pre-carregada de usuarios (opcional)
        context: Contexto do modulo (onboarding, ongoing, grandes_contas)
    """
    from flask import current_app
    from ....core.extensions import gamification_rules_cache

    persist_calculated_metrics = bool(current_app.config.get("GAMIFICATION_REPORT_PERSIST_CALCULATED", False))

    regras_db = _get_gamification_rules_as_dict()
    if not regras_db:
        cache_key = "gamification_rules_dict"
        if cache_key in gamification_rules_cache:
            del gamification_rules_cache[cache_key]
            current_app.logger.warning("Cache de regras vazio; tentando recarregar.")
            regras_db = _get_gamification_rules_as_dict()

        if not regras_db:
            current_app.logger.error("Tabela gamificacao_regras vazia ou inacessivel.")
            raise ValueError(
                "Falha ao carregar regras de pontuacao da gamificacao. "
                "Verifique se a tabela gamificacao_regras possui dados."
            )

    try:
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        ultimo_dia = date(ano, mes, ultimo_dia_mes)
        fim_ultimo_dia = datetime.combine(ultimo_dia, datetime.max.time())
        dias_no_mes = ultimo_dia_mes
    except ValueError as exc:
        raise ValueError(f"Mes ({mes}) ou Ano ({ano}) invalido.") from exc

    primeiro_dia_str = primeiro_dia.isoformat()
    fim_ultimo_dia_str = fim_ultimo_dia.isoformat()
    ctx = resolve_context(context)

    if all_cs_users_list is None:
        sql_users = """
            SELECT u.usuario AS usuario, u.nome, u.cargo, u.foto_url
            FROM perfil_usuario u
            LEFT JOIN perfil_usuario_contexto puc ON puc.usuario = u.usuario AND puc.contexto = %s
            WHERE COALESCE(puc.perfil_acesso, 'Sem Acesso') IS NOT NULL
                AND COALESCE(puc.perfil_acesso, 'Sem Acesso') != ''
        """
        args_users = [ctx]
        if target_cs_email:
            sql_users += " AND u.usuario = %s"
            args_users.append(target_cs_email)
        sql_users += " ORDER BY u.nome"

        all_cs_users_list = query_db(sql_users, tuple(args_users)) or []

    usuarios_filtrados = [
        u.get("usuario")
        for u in all_cs_users_list
        if isinstance(u, dict) and u.get("usuario")
    ]

    metricas_manuais_map = {}
    if usuarios_filtrados:
        placeholders = ",".join(["%s"] * len(usuarios_filtrados))
        sql_metricas = (
            "SELECT * FROM gamificacao_metricas_mensais "
            f"WHERE mes = %s AND ano = %s AND contexto = %s AND usuario_cs IN ({placeholders})"
        )
        args_metricas = [mes, ano, ctx, *usuarios_filtrados]

        metricas_manuais_raw = query_db(sql_metricas, tuple(args_metricas)) or []
        for metrica in metricas_manuais_raw:
            if isinstance(metrica, dict):
                metricas_manuais_map[metrica["usuario_cs"]] = metrica

    tma_data_map, iniciadas_map, tarefas_map = _get_gamification_automatic_data_bulk(
        mes, ano, primeiro_dia_str, fim_ultimo_dia_str, target_cs_email, context=context
    )

    report_data = []

    for user_profile in all_cs_users_list:
        if not isinstance(user_profile, dict):
            continue

        user_email = user_profile.get("usuario")
        if not user_email:
            continue

        try:
            metricas_manuais = metricas_manuais_map.get(user_email, {})
            dados_tma = tma_data_map.get(user_email, {})
            count_iniciadas = iniciadas_map.get(user_email, 0)
            dados_tarefas = tarefas_map.get(user_email, {})

            resultado, dados_automaticos_calculados = _calculate_user_gamification_score(
                user_profile,
                metricas_manuais,
                regras_db,
                dias_no_mes,
                dados_tma,
                count_iniciadas,
                dados_tarefas,
            )

            report_data.append(
                {
                    "usuario_nome": user_profile.get("nome", user_email),
                    "cargo": user_profile.get("cargo", "N/A"),
                    "foto_url": user_profile.get("foto_url"),
                    "usuario_cs": user_email,
                    "mes": mes,
                    "ano": ano,
                    "status_calculo": "Calculado/Atualizado",
                    **resultado,
                }
            )

            if persist_calculated_metrics:
                try:
                    dados_para_salvar = {
                        key: value
                        for key, value in dados_automaticos_calculados.items()
                        if value is not None
                    }
                    dados_para_salvar["data_registro"] = datetime.now(timezone.utc)

                    existing_record_id = metricas_manuais.get("id")
                    if existing_record_id and dados_para_salvar:
                        set_clauses_calc = [f"{key} = %s" for key in dados_para_salvar]
                        sql_update_calc = (
                            f"UPDATE gamificacao_metricas_mensais "
                            f"SET {', '.join(set_clauses_calc)} WHERE id = %s"
                        )
                        args_update_calc = [*list(dados_para_salvar.values()), existing_record_id]
                        execute_db(sql_update_calc, tuple(args_update_calc))  # nosec B608
                except Exception as exc:
                    logger.warning(
                        "Falha ao salvar metricas calculadas automaticamente para %s: %s",
                        user_email,
                        exc,
                        exc_info=True,
                    )

        except Exception as exc:
            logger.exception("Falha ao calcular dados do relatorio para %s", user_email, exc_info=True)
            report_data.append(
                {
                    "usuario_nome": user_profile.get("nome", user_email),
                    "cargo": user_profile.get("cargo", "N/A"),
                    "foto_url": user_profile.get("foto_url"),
                    "usuario_cs": user_email,
                    "mes": mes,
                    "ano": ano,
                    "elegivel": False,
                    "pontuacao_final": 0,
                    "motivo_inelegibilidade": f"Erro interno no sistema: {exc}",
                    "detalhamento_pontos": {},
                    "status_calculo": "Erro Critico",
                }
            )

    report_data_sorted = sorted(report_data, key=lambda x: x["pontuacao_final"], reverse=True)
    return report_data_sorted
