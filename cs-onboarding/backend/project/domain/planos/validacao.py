"""
Módulo de Validação de Planos
Validações de estrutura hierárquica e checklist.
Princípio SOLID: Single Responsibility
"""
from typing import Dict, List

from ...common.exceptions import ValidationError


# Tags válidas para tarefas/subtarefas
VALID_TAGS = {"Ação interna", "Reunião"}


def validar_estrutura_hierarquica(estrutura: Dict) -> bool:
    """
    Valida estrutura hierárquica no formato fases/grupos/tarefas/subtarefas.
    """
    if not isinstance(estrutura, dict):
        raise ValidationError("Estrutura deve ser um dicionário")

    fases = estrutura.get('fases', [])
    if not isinstance(fases, list):
        raise ValidationError("'fases' deve ser uma lista")

    if not fases:
        raise ValidationError("Plano deve ter pelo menos uma fase")

    ordens_fases = set()
    for i, fase in enumerate(fases):
        if not isinstance(fase, dict):
            raise ValidationError(f"Fase {i+1} deve ser um dicionário")

        if 'nome' not in fase or not fase['nome']:
            raise ValidationError(f"Fase {i+1} deve ter um nome")

        ordem = fase.get('ordem', 0)
        if ordem in ordens_fases:
            raise ValidationError(f"Ordem {ordem} duplicada nas fases")
        ordens_fases.add(ordem)

        grupos = fase.get('grupos', [])
        if not isinstance(grupos, list):
            raise ValidationError(f"'grupos' da fase '{fase['nome']}' deve ser uma lista")

        for j, grupo in enumerate(grupos):
            if not isinstance(grupo, dict):
                raise ValidationError(f"Grupo {j+1} da fase '{fase['nome']}' deve ser um dicionário")

            if 'nome' not in grupo or not grupo['nome']:
                raise ValidationError(f"Grupo {j+1} da fase '{fase['nome']}' deve ter um nome")

            tarefas = grupo.get('tarefas', [])
            if not isinstance(tarefas, list):
                raise ValidationError(
                    f"'tarefas' do grupo '{grupo['nome']}' deve ser uma lista"
                )

            for k, tarefa in enumerate(tarefas):
                if not isinstance(tarefa, dict):
                    raise ValidationError(
                        f"Tarefa {k+1} do grupo '{grupo['nome']}' deve ser um dicionário"
                    )

                if 'nome' not in tarefa or not tarefa['nome']:
                    raise ValidationError(
                        f"Tarefa {k+1} do grupo '{grupo['nome']}' deve ter um nome"
                    )

                tag = tarefa.get('tag')
                if tag and tag not in VALID_TAGS:
                    raise ValidationError(
                        f"Tarefa '{tarefa['nome']}' tem tag inválida '{tag}'. Tags permitidas: {', '.join(VALID_TAGS)}"
                    )

                subtarefas = tarefa.get('subtarefas', [])
                if not isinstance(subtarefas, list):
                    raise ValidationError(
                        f"'subtarefas' da tarefa '{tarefa['nome']}' deve ser uma lista"
                    )

                for idx, subtarefa in enumerate(subtarefas):
                    if not isinstance(subtarefa, dict):
                        raise ValidationError(
                            f"Subtarefa {idx+1} da tarefa '{tarefa['nome']}' deve ser um dicionário"
                        )

                    if 'nome' not in subtarefa or not subtarefa['nome']:
                        raise ValidationError(
                            f"Subtarefa {idx+1} da tarefa '{tarefa['nome']}' deve ter um nome"
                        )

                    tag_sub = subtarefa.get('tag')
                    if tag_sub and tag_sub not in VALID_TAGS:
                        raise ValidationError(
                            f"Subtarefa '{subtarefa['nome']}' tem tag inválida '{tag_sub}'. Tags permitidas: {', '.join(VALID_TAGS)}"
                        )

    return True


def validar_estrutura_checklist(estrutura: Dict) -> bool:
    """
    Valida estrutura de checklist_items (hierarquia infinita).
    Aceita estrutura aninhada ou plana com parent_id.
    """
    if not isinstance(estrutura, dict):
        raise ValidationError("Estrutura deve ser um dicionário")

    if 'items' in estrutura:
        items = estrutura['items']
        if not isinstance(items, list):
            raise ValidationError("'items' deve ser uma lista")

        if len(items) > 0:
            _validar_items_recursivo(items, set(), 0)
        return True
    elif 'fases' in estrutura:
        return validar_estrutura_hierarquica(estrutura)
    else:
        raise ValidationError("Estrutura deve conter 'items' ou 'fases'")


def _validar_items_recursivo(items: List[Dict], titles_set: set, depth: int, max_depth: int = 100):
    """
    Valida itens recursivamente, verificando loops e profundidade máxima.
    """
    if depth > max_depth:
        raise ValidationError(f"Hierarquia muito profunda (máximo {max_depth} níveis)")

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValidationError(f"Item {i+1} deve ser um dicionário")

        title = item.get('title') or item.get('nome', '')
        if not title or not str(title).strip():
            raise ValidationError(f"Item {i+1} deve ter um título (title ou nome)")

        tag = item.get('tag')
        if tag and tag not in VALID_TAGS:
            raise ValidationError(
                 f"Item '{title}' tem tag inválida '{tag}'. Tags permitidas: {', '.join(VALID_TAGS)}"
            )

        children = item.get('children', [])
        if children:
            if not isinstance(children, list):
                raise ValidationError(f"Children do item '{title}' deve ser uma lista")
            _validar_items_recursivo(children, titles_set, depth + 1, max_depth)
