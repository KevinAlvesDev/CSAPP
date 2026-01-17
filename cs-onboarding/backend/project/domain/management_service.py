"""
Management Service - Módulo de Compatibilidade
Este arquivo re-exporta todas as funções do novo pacote domain/management/
para manter compatibilidade com código existente.

REFATORAÇÃO SOLID: As funções foram movidas para módulos especializados:
- users.py   -> Listagem e consulta de usuários
- admin.py   -> Operações administrativas
"""

from .management import (
    atualizar_perfil_usuario_service,
    excluir_usuario_service,
    limpar_implantacoes_orfas_service,
    listar_todos_cs_com_cache,
    listar_usuarios_service,
    obter_perfil_usuario,
    obter_perfis_disponiveis,
    perform_backup,
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
