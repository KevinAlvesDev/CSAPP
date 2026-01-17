"""
Módulo de Gerenciamento - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- users.py   -> Listagem e consulta de usuários
- admin.py   -> Operações administrativas
"""

from .admin import (
    atualizar_perfil_usuario_service,
    excluir_usuario_service,
    limpar_implantacoes_orfas_service,
)
from .backup import perform_backup
from .users import (
    listar_todos_cs_com_cache,
    listar_usuarios_service,
    obter_perfil_usuario,
    obter_perfis_disponiveis,
    verificar_usuario_existe,
)

__all__ = [
    "listar_usuarios_service",
    "verificar_usuario_existe",
    "obter_perfil_usuario",
    "obter_perfis_disponiveis",
    "listar_todos_cs_com_cache",
    "atualizar_perfil_usuario_service",
    "excluir_usuario_service",
    "limpar_implantacoes_orfas_service",
    "perform_backup",
]
