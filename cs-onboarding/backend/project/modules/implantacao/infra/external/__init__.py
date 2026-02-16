"""
Módulo de Serviços Externos - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- oamd.py       -> Função principal de consulta OAMD
- query.py      -> Construção e execução de queries SQL
- mapper.py     -> Mapeamento de campos OAMD → Frontend
- utils.py      -> Funções auxiliares (serialização, extração de códigos)
"""

# Função principal de consulta
# Funções de mapeamento
from .mapper import (
    map_oamd_to_frontend,
)
from .oamd import (
    consultar_empresa_oamd,
)

# Funções de query (para uso interno ou testes)
from .query import (
    build_oamd_query,
    execute_oamd_search,
)

# Funções utilitárias
from .utils import (
    build_tela_apoio_link,
    extract_infra_code,
    json_safe_value,
    sanitize_empresa_data,
)

# Exports públicos
__all__ = [
    # Query
    "build_oamd_query",
    # Principal
    "consultar_empresa_oamd",
    "execute_oamd_search",
    "extract_infra_code",
    # Utils
    "json_safe_value",
    # Mapper
    "map_oamd_to_frontend",
    "sanitize_empresa_data",
]
