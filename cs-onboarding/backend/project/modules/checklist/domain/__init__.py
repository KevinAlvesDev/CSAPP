"""
Módulo de Checklist - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- items.py      -> Operações em itens (toggle, delete, responsável, prazo)
- comments.py   -> Gerenciamento de comentários
- tree.py       -> Árvore e progresso
- history.py    -> Histórico de alterações
- utils.py      -> Funções auxiliares
"""

# Importações de items.py
# Importações de comments.py
from .comments import (
    add_comment_to_item,
    excluir_comentario_service,
    listar_comentarios_implantacao,
    listar_comentarios_item,
    obter_comentario_para_email,
    registrar_envio_email_comentario,
    update_comment_service,
)

# Importações de history.py
from .history import (
    obter_historico_prazos,
    obter_historico_responsavel,
)
from .items import (
    atualizar_prazo_item,
    delete_checklist_item,
    move_item,
    toggle_item_status,
    update_item_responsavel,
)

# Importações de tree.py
from .tree import (
    build_nested_tree,
    get_checklist_tree,
    get_item_progress_stats,
    obter_progresso_global_service,
)
from .utils import (
    _format_datetime,
    _invalidar_cache_progresso_local,
    listar_usuarios_cs,
    plano_permite_excluir_tarefas,
)

__all__ = [
    "_format_datetime",
    "_invalidar_cache_progresso_local",
    "add_comment_to_item",
    "atualizar_prazo_item",
    "build_nested_tree",
    "delete_checklist_item",
    "excluir_comentario_service",
    "get_checklist_tree",
    "get_item_progress_stats",
    "listar_comentarios_implantacao",
    "listar_comentarios_item",
    "listar_usuarios_cs",
    "move_item",
    "obter_comentario_para_email",
    "obter_historico_prazos",
    "obter_historico_responsavel",
    "obter_progresso_global_service",
    "plano_permite_excluir_tarefas",
    "registrar_envio_email_comentario",
    "toggle_item_status",
    "update_comment_service",
    "update_item_responsavel",
]
