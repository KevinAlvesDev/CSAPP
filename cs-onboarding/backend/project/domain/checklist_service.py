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

# Re-exportar todas as funções do novo pacote para compatibilidade
from .checklist import (
    # Items
    toggle_item_status,
    delete_checklist_item,
    update_item_responsavel,
    atualizar_prazo_item,
    move_item,
    # Comments
    add_comment_to_item,
    listar_comentarios_implantacao,
    listar_comentarios_item,
    obter_comentario_para_email,
    excluir_comentario_service,
    update_comment_service,
    # Tree
    get_checklist_tree,
    build_nested_tree,
    get_item_progress_stats,
    obter_progresso_global_service,
    # History
    obter_historico_responsavel,
    obter_historico_prazos,
    # Utils
    _invalidar_cache_progresso_local,
    _format_datetime,
    listar_usuarios_cs,
)

__all__ = [
    # Items
    'toggle_item_status',
    'delete_checklist_item',
    'update_item_responsavel',
    'atualizar_prazo_item',
    'move_item',
    # Comments
    'add_comment_to_item',
    'listar_comentarios_implantacao',
    'listar_comentarios_item',
    'obter_comentario_para_email',
    'excluir_comentario_service',
    'update_comment_service',
    # Tree
    'get_checklist_tree',
    'build_nested_tree',
    'get_item_progress_stats',
    'obter_progresso_global_service',
    # History
    'obter_historico_responsavel',
    'obter_historico_prazos',
    # Utils
    '_invalidar_cache_progresso_local',
    '_format_datetime',
    'listar_usuarios_cs',
]
