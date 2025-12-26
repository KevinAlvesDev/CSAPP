"""
Módulo de Relatório de Gamificação
Geração do relatório de gamificação mensal.
Princípio SOLID: Single Responsibility
"""
import calendar
from datetime import date, datetime

from ...db import execute_db, query_db
from .rules import _get_gamification_rules_as_dict
from .metrics import _get_gamification_automatic_data_bulk
from .calculator import _calculate_user_gamification_score


def get_gamification_report_data(mes, ano, target_cs_email=None, all_cs_users_list=None):
    """
    Função principal para buscar e calcular o relatório de gamificação.
    Resolve o problema N+1 ao buscar todos os dados em massa.
    """
    from flask import current_app

    from ...core.extensions import gamification_rules_cache

    regras_db = _get_gamification_rules_as_dict()
    if not regras_db:
        # Limpar cache se estiver vazio e tentar novamente
        cache_key = 'gamification_rules_dict'
        if cache_key in gamification_rules_cache:
            del gamification_rules_cache[cache_key]
            current_app.logger.warning("Cache de regras estava vazio, limpando e tentando novamente...")
            regras_db = _get_gamification_rules_as_dict()

        if not regras_db:
            current_app.logger.error("Tabela gamificacao_regras está vazia ou não acessível.")
            raise ValueError("Falha ao carregar as regras de pontuação da gamificação do banco de dados. Verifique se a tabela gamificacao_regras tem dados.")

    try:
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        ultimo_dia = date(ano, mes, ultimo_dia_mes)
        fim_ultimo_dia = datetime.combine(ultimo_dia, datetime.max.time())
        dias_no_mes = ultimo_dia_mes
    except ValueError:
        raise ValueError(f"Mês ({mes}) ou Ano ({ano}) inválido.")

    primeiro_dia_str = primeiro_dia.isoformat()
    fim_ultimo_dia_str = fim_ultimo_dia.isoformat()

    if all_cs_users_list is None:
        sql_users = "SELECT usuario, nome, cargo FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != ''"
        args_users = []
        if target_cs_email:
            sql_users += " AND usuario = %s"
            args_users.append(target_cs_email)
        sql_users += " ORDER BY nome"

        all_cs_users_list = query_db(sql_users, tuple(args_users))
        all_cs_users_list = all_cs_users_list if all_cs_users_list is not None else []

    usuarios_filtrados = [u['usuario'] for u in all_cs_users_list if isinstance(u, dict)]
    metricas_manuais_map = {}

    if usuarios_filtrados:
        placeholders = ','.join(['%s'] * len(usuarios_filtrados))
        sql_metricas = f"SELECT * FROM gamificacao_metricas_mensais WHERE mes = %s AND ano = %s AND usuario_cs IN ({placeholders})"
        args_metricas = [mes, ano] + usuarios_filtrados

        metricas_manuais_raw = query_db(sql_metricas, tuple(args_metricas))
        metricas_manuais_raw = metricas_manuais_raw if metricas_manuais_raw is not None else []

        for metrica in metricas_manuais_raw:
            if isinstance(metrica, dict):
                metricas_manuais_map[metrica['usuario_cs']] = metrica

    tma_data_map, iniciadas_map, tarefas_map = _get_gamification_automatic_data_bulk(
        mes, ano, primeiro_dia_str, fim_ultimo_dia_str, target_cs_email
    )

    report_data = []

    for user_profile in all_cs_users_list:
        if not isinstance(user_profile, dict): continue
        user_email = user_profile.get('usuario')
        if not user_email: continue

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
                dados_tarefas
            )

            report_data.append({
                'usuario_nome': user_profile.get('nome', user_email),
                'cargo': user_profile.get('cargo', 'N/A'),
                'usuario_cs': user_email,
                'mes': mes,
                'ano': ano,
                'status_calculo': 'Calculado/Atualizado',
                **resultado
            })

            try:
                dados_para_salvar = {
                    key: value for key, value in dados_automaticos_calculados.items()
                    if value is not None
                }

                dados_para_salvar['data_registro'] = datetime.now()

                existing_record_id = metricas_manuais.get('id')

                if existing_record_id:
                    set_clauses_calc = [f"{key} = %s" for key in dados_para_salvar.keys()]

                    if set_clauses_calc:
                        sql_update_calc = f"UPDATE gamificacao_metricas_mensais SET {', '.join(set_clauses_calc)} WHERE id = %s"
                        args_update_calc = list(dados_para_salvar.values()) + [existing_record_id]
                        execute_db(sql_update_calc, tuple(args_update_calc))

            except Exception:
                pass

        except Exception as e:
            report_data.append({
                'usuario_nome': user_profile.get('nome', user_email),
                'cargo': user_profile.get('cargo', 'N/A'),
                'usuario_cs': user_email,
                'mes': mes,
                'ano': ano,
                'elegivel': False,
                'pontuacao_final': 0,
                'motivo_inelegibilidade': f'Erro interno no sistema: {e}',
                'detalhamento_pontos': {},
                'status_calculo': 'Erro Crítico'
            })

    report_data_sorted = sorted(report_data, key=lambda x: x['pontuacao_final'], reverse=True)
    return report_data_sorted
