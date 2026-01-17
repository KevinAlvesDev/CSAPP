"""
Hierarquia Service - Módulo de Compatibilidade
Este arquivo re-exporta todas as funções do novo pacote domain/hierarquia/
para manter compatibilidade com código existente.

REFATORAÇÃO SOLID: As funções foram movidas para módulos especializados:
- tree.py       -> Estrutura hierárquica da implantação
- tasks.py      -> Operações em tarefas/subtarefas
- comments.py   -> Comentários em tarefas
"""

# Re-exportar todas as funções do novo pacote para compatibilidade
from .hierarquia import (
    # Comments
    adicionar_comentario_tarefa,
    calcular_progresso_implantacao,
    get_comentarios_tarefa,
    # Tree
    get_hierarquia_implantacao,
    # Tasks
    toggle_subtarefa,
)

# Manter __all__ para compatibilidade com imports *
__all__ = [
    "get_hierarquia_implantacao",
    "toggle_subtarefa",
    "calcular_progresso_implantacao",
    "adicionar_comentario_tarefa",
    "get_comentarios_tarefa",
]
