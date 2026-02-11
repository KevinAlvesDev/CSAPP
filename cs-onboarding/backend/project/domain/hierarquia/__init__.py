"""
Módulo de Hierarquia - Pacote SOLID
Re-exporta todas as funções para manter compatibilidade com código existente.

Estrutura:
- tree.py       -> Estrutura hierárquica da implantação
- tasks.py      -> Operações em tarefas/subtarefas
- comments.py   -> Comentários em tarefas
"""

# Importações de tree.py
# Importações de comments.py
from .comments import (
    adicionar_comentario_tarefa,
    get_comentarios_tarefa,
)

# Importações de tasks.py
from .tasks import (
    calcular_progresso_implantacao,
    toggle_subtarefa,
)
from .tree import (
    get_hierarquia_implantacao,
)

# Exports públicos
__all__ = [
    "adicionar_comentario_tarefa",
    "calcular_progresso_implantacao",
    "get_comentarios_tarefa",
    "get_hierarquia_implantacao",
    "toggle_subtarefa",
]
