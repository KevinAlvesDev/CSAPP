"""
Módulo de Analytics - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- dashboard.py      -> Dados do dashboard gerencial
- charts.py         -> Gráficos de implantações e funil
- gamification.py   -> Ranking de gamificação
- cancelamentos.py  -> Análise de cancelamentos
- utils.py          -> Funções auxiliares de data
"""

# Importações de dashboard.py (VERSÃO OTIMIZADA V2)
# Importações de cancelamentos.py
from .cancelamentos import (
    get_cancelamentos_data,
)

# Importações de charts.py
from .charts import (
    get_funnel_counts,
    get_implants_by_day,
)
from .dashboard_v2 import (
    get_analytics_data_v2 as get_analytics_data,
)

# Importações de gamification.py
from .gamification import (
    get_gamification_rank,
)

# Importações de utils.py
from .utils import (
    _format_date_for_query,
    calculate_time_in_status,
    date_col_expr,
    date_param_expr,
)

# Exports públicos
__all__ = [
    # Dashboard
    "get_analytics_data",
    # Charts
    "get_implants_by_day",
    "get_funnel_counts",
    # Gamification
    "get_gamification_rank",
    # Cancelamentos
    "get_cancelamentos_data",
    # Utils
    "calculate_time_in_status",
    "_format_date_for_query",
    "date_col_expr",
    "date_param_expr",
]
