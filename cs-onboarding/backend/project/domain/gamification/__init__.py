"""
Módulo de Gamificação - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- rules.py       -> Regras de gamificação
- metrics.py     -> Métricas mensais
- calculator.py  -> Cálculos de pontuação
- report.py      -> Relatório de gamificação
- utils.py       -> Funções auxiliares
"""

# Importações de rules.py
# Importações de calculator.py
from .calculator import (
    _calculate_bonus,
    _calculate_penalties,
    _calculate_points,
    _calculate_user_gamification_score,
    _check_eligibility,
)

# Importações de metrics.py
from .metrics import (
    _get_gamification_automatic_data_bulk,
    obter_metricas_mensais,
    salvar_metricas_mensais,
)

# Importações de report.py
from .report import (
    get_gamification_report_data,
)
from .rules import (
    _get_all_gamification_rules_grouped,
    _get_gamification_rules_as_dict,
    salvar_regras_gamificacao,
)

# Importações de utils.py
from .utils import (
    clear_gamification_cache,
    get_all_cs_users_for_gamification,
)

# Exports públicos
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
