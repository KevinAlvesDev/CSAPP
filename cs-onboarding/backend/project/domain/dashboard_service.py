"""
Dashboard Service - Módulo de Compatibilidade
Este arquivo re-exporta todas as funções do novo pacote domain/dashboard/
para manter compatibilidade com código existente.

REFATORAÇÃO SOLID: As funções foram movidas para módulos especializados:
- data.py   -> Buscar dados do dashboard
- utils.py  -> Formatação de tempo relativo
"""

# Re-exportar todas as funções do novo pacote para compatibilidade
from .dashboard import (
    # Data
    get_dashboard_data,
    # Utils
    format_relative_time,
)

# Manter __all__ para compatibilidade com imports *
__all__ = [
    'get_dashboard_data',
    'format_relative_time',
]
