"""
Gamification Service - Módulo de Compatibilidade
Este arquivo re-exporta todas as funções do novo pacote domain/gamification/
para manter compatibilidade com código existente.

REFATORAÇÃO SOLID: As funções foram movidas para módulos especializados:
- rules.py       -> Regras de gamificação
- metrics.py     -> Métricas mensais
- calculator.py  -> Cálculos de pontuação
- report.py      -> Relatório de gamificação
- utils.py       -> Funções auxiliares
"""

# Re-exportar todas as funções do novo pacote para compatibilidade
from .gamification import (
    _calculate_bonus,
    _calculate_penalties,
    _calculate_points,
    _calculate_user_gamification_score,
    # Calculator
    _check_eligibility,
    _get_all_gamification_rules_grouped,
    # Metrics
    _get_gamification_automatic_data_bulk,
    # Rules
    _get_gamification_rules_as_dict,
    # Utils
    clear_gamification_cache,
    get_all_cs_users_for_gamification,
    # Report
    get_gamification_report_data,
    obter_metricas_mensais,
    salvar_metricas_mensais,
    salvar_regras_gamificacao,
)

# Manter __all__ para compatibilidade com imports *
__all__ = [
    # Rules
    "_get_gamification_rules_as_dict",
    "_get_all_gamification_rules_grouped",
    "salvar_regras_gamificacao",
    # Metrics
    "_get_gamification_automatic_data_bulk",
    "obter_metricas_mensais",
    "salvar_metricas_mensais",
    # Calculator
    "_check_eligibility",
    "_calculate_points",
    "_calculate_bonus",
    "_calculate_penalties",
    "_calculate_user_gamification_score",
    # Report
    "get_gamification_report_data",
    # Utils
    "clear_gamification_cache",
    "get_all_cs_users_for_gamification",
]
