"""
Módulo de Dashboard - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- data.py   -> Buscar dados do dashboard
- utils.py  -> Formatação de tempo relativo
"""

# Importações de data.py
from .data import (
    get_dashboard_data,
)

# Importações de utils.py
from .utils import (
    format_relative_time,
)

# Exports públicos
__all__ = [
    'get_dashboard_data',
    'format_relative_time',
]
