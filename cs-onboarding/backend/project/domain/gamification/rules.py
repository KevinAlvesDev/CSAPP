"""
Módulo de Regras de Gamificação
Buscar e salvar regras de gamificação.
Princípio SOLID: Single Responsibility
"""

from collections import OrderedDict

from flask import current_app

from ...db import execute_db, query_db
from .utils import clear_gamification_cache


def _get_gamification_rules_as_dict():
    """Busca todas as regras do DB e retorna um dicionário (com cache)."""
    from ...core.extensions import gamification_rules_cache

    cache_key = "gamification_rules_dict"
    if cache_key in gamification_rules_cache:
        cached_result = gamification_rules_cache[cache_key]
        if cached_result:
            return cached_result

    try:
        regras_raw = query_db("SELECT regra_id, valor_pontos FROM gamificacao_regras")
        if not regras_raw:
            current_app.logger.warning("Tabela gamificacao_regras está vazia. Verifique se as regras foram inseridas.")
            result = {}
        else:
            result = {r["regra_id"]: r["valor_pontos"] for r in regras_raw}
            current_app.logger.info(f"Carregadas {len(result)} regras de gamificação do banco de dados.")

        gamification_rules_cache[cache_key] = result
        return result
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar regras de gamificação: {e}", exc_info=True)
        return {}


def _get_all_gamification_rules_grouped():
    """Busca todas as regras de gamificação e as agrupa por categoria (com cache)."""
    from ...core.extensions import gamification_rules_cache

    cache_key = "gamification_rules_grouped"
    if cache_key in gamification_rules_cache:
        return gamification_rules_cache[cache_key]

    try:
        regras = query_db("SELECT * FROM gamificacao_regras ORDER BY categoria, id")
        if not regras:
            result = {}
        else:
            regras_agrupadas = OrderedDict()
            for regra in regras:
                categoria = regra["categoria"]
                if categoria not in regras_agrupadas:
                    regras_agrupadas[categoria] = []
                regras_agrupadas[categoria].append(regra)
            result = regras_agrupadas

        gamification_rules_cache[cache_key] = result
        return result
    except Exception:
        return {}


def salvar_regras_gamificacao(updates_list):
    """
    Salva atualizações de regras de gamificação.

    Args:
        updates_list: Lista de tuplas (valor_pontos, regra_id)

    Returns:
        int: Número de regras atualizadas
    """
    if not updates_list:
        return 0

    total_atualizado = 0
    for valor, regra_id in updates_list:
        execute_db("UPDATE gamificacao_regras SET valor_pontos = %s WHERE regra_id = %s", (valor, regra_id))
        total_atualizado += 1

    clear_gamification_cache()
    return total_atualizado
