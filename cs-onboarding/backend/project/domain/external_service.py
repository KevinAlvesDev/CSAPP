"""
External Service - Módulo de Compatibilidade
Este arquivo re-exporta todas as funções do novo pacote domain/external/
para manter compatibilidade com código existente.

REFATORAÇÃO SOLID: As funções foram movidas para módulos especializados:
- oamd.py       -> Função principal de consulta OAMD
- query.py      -> Construção e execução de queries SQL
- mapper.py     -> Mapeamento de campos OAMD → Frontend
- utils.py      -> Funções auxiliares (serialização, extração de códigos)

A função gigante `consultar_empresa_oamd` foi quebrada em partes menores:
- execute_oamd_search: Execução de queries com diferentes estratégias
- map_oamd_to_frontend: Mapeamento de campos para o frontend
- sanitize_empresa_data: Sanitização de dados para JSON
- extract_infra_code: Extração do código de infra (ZW_###)
"""

# Re-exportar a função principal para compatibilidade
from .external import (
    consultar_empresa_oamd,
)

# Manter __all__ para compatibilidade com imports *
__all__ = [
    'consultar_empresa_oamd',
]
