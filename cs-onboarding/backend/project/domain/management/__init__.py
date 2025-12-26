"""
Módulo de Gerenciamento - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- users.py   -> Listagem e consulta de usuários
- admin.py   -> Operações administrativas
"""

# Importações de users.py
from .users import (
    listar_usuarios_service,
    verificar_usuario_existe,
    obter_perfil_usuario,
    obter_perfis_disponiveis,
    listar_todos_cs_com_cache,
)

# Importações de admin.py
from .admin import (
    atualizar_perfil_usuario_service,
    excluir_usuario_service,
    limpar_implantacoes_orfas_service,
)

# Exports públicos
__all__ = [
    'listar_usuarios_service',
    'verificar_usuario_existe',
    'obter_perfil_usuario',
    'obter_perfis_disponiveis',
    'listar_todos_cs_com_cache',
    'atualizar_perfil_usuario_service',
    'excluir_usuario_service',
    'limpar_implantacoes_orfas_service',
]
