"""
Checklist Service - Módulo de Compatibilidade
Este arquivo re-exporta todas as funções do novo pacote domain/checklist/
para manter compatibilidade com código existente.

REFATORAÇÃO SOLID: As funções foram movidas para módulos especializados:
- items.py      -> Operações em itens (toggle, delete, responsável, prazo)
- comments.py   -> Gerenciamento de comentários
- tree.py       -> Árvore e progresso
- history.py    -> Histórico de alterações
- utils.py      -> Funções auxiliares
"""

from .checklist import (
    _format_datetime,
    _invalidar_cache_progresso_local,
    add_comment_to_item,
    atualizar_prazo_item,
    build_nested_tree,
    contar_comentarios_implantacao,
    delete_checklist_item,
    excluir_comentario_service,
    get_checklist_tree,
    get_item_progress_stats,
    listar_comentarios_implantacao,
    listar_comentarios_item,
    listar_usuarios_cs,
    move_item,
    obter_comentario_para_email,
    obter_historico_prazos,
    obter_historico_responsavel,
    obter_progresso_global_service,
    plano_permite_excluir_tarefas,
    registrar_envio_email_comentario,
    toggle_item_status,
    update_comment_service,
    update_item_responsavel,
)

__all__ = [
    "toggle_item_status",
    "delete_checklist_item",
    "update_item_responsavel",
    "atualizar_prazo_item",
    "move_item",
    "add_comment_to_item",
    "contar_comentarios_implantacao",
    "listar_comentarios_implantacao",
    "listar_comentarios_item",
    "obter_comentario_para_email",
    "excluir_comentario_service",
    "update_comment_service",
    "get_checklist_tree",
    "build_nested_tree",
    "get_item_progress_stats",
    "obter_progresso_global_service",
    "obter_historico_responsavel",
    "obter_historico_prazos",
    "_invalidar_cache_progresso_local",
    "_format_datetime",
    "listar_usuarios_cs",
    "plano_permite_excluir_tarefas",
    "registrar_envio_email_comentario",
]
