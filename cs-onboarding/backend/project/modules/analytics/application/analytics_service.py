"""
Analytics Service - Módulo de Compatibilidade
Este arquivo re-exporta todas as funções do novo pacote domain/analytics/
para manter compatibilidade com código existente.

REFATORAÇÃO SOLID: As funções foram movidas para módulos especializados:
- dashboard.py      -> Dados do dashboard gerencial
- charts.py         -> Gráficos de implantações e funil
- gamification.py   -> Ranking de gamificação
- cancelamentos.py  -> Análise de cancelamentos
- utils.py          -> Funções auxiliares de data
"""

# Re-exportar todas as funções do novo pacote para compatibilidade
from ..domain import (
    _format_date_for_query,
    # Utils
    calculate_time_in_status,
    date_col_expr,
    date_param_expr,
    # Dashboard
    get_analytics_data,
    # Cancelamentos
    get_cancelamentos_data,
    get_funnel_counts,
    # Gamification
    get_gamification_rank,
    # Charts
    get_implants_by_day,
)

# Manter __all__ para compatibilidade com imports *
__all__ = [
    "_format_date_for_query",
    # Utils
    "calculate_time_in_status",
    "date_col_expr",
    "date_param_expr",
    # Dashboard
    "get_analytics_data",
    # Cancelamentos
    "get_cancelamentos_data",
    "get_funnel_counts",
    # Gamification
    "get_gamification_rank",
    # Charts
    "get_implants_by_day",
]
