"""
DataLoader Pattern — Batch queries para eliminar N+1.

Implementação inspirada no DataLoader do Facebook/GraphQL.
Agrupa múltiplas queries em uma única, reduzindo dramaticamente o número de roundtrips ao banco.

Uso:
    from backend.project.common.dataloader import ChecklistDataLoader

    loader = ChecklistDataLoader(implantacao_id=42)
    all_data = loader.load_all()
    # all_data = {
    #     "fases": [...],
    #     "grupos": [...],
    #     "tarefas": [...],
    #     "subtarefas": [...],
    #     "comentarios_map": {...},
    # }
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

from ..db import query_db

logger = logging.getLogger("database")


class ChecklistDataLoader:
    """
    Carrega toda a árvore de checklist de uma implantação em poucas queries.

    Substitui o padrão N+1 onde cada fase, grupo, tarefa e subtarefa
    executava uma query individual.

    Antes: ~50+ queries por implantação
    Depois: 2-3 queries totais
    """

    def __init__(self, implantacao_id: int):
        self.implantacao_id = implantacao_id
        self._items: list[dict] = []
        self._items_by_id: dict[int, dict] = {}
        self._items_by_parent: dict[int | None, list[dict]] = {}
        self._loaded = False

    def _load_items(self) -> None:
        """Carrega TODOS os items do checklist em uma única query."""
        if self._loaded:
            return

        try:
            self._items = (
                query_db(
                    """
                SELECT id, parent_id, title, tipo_item, completed, tag, ordem,
                       responsavel, prazo_inicio, prazo_fim,
                       implantacao_id, created_at
                FROM checklist_items
                WHERE implantacao_id = %s
                ORDER BY COALESCE(ordem, 0), id
                """,
                    (self.implantacao_id,),
                )
                or []
            )
        except Exception as e:
            logger.error(f"Erro ao carregar checklist items para implantação {self.implantacao_id}: {e}")
            self._items = []

        # Indexar por ID e por parent_id para lookup rápido
        for item in self._items:
            item_id = item["id"]
            parent_id = item.get("parent_id")

            self._items_by_id[item_id] = item
            self._items_by_parent.setdefault(parent_id, []).append(item)

        self._loaded = True

    def get_by_tipo(self, tipo_item: str) -> list[dict]:
        """Retorna todos os items de um tipo específico."""
        self._load_items()
        return [i for i in self._items if i.get("tipo_item") == tipo_item]

    def get_children(self, parent_id: int | None, tipo_item: str | None = None) -> list[dict]:
        """Retorna filhos de um item, opcionalmente filtrados por tipo."""
        self._load_items()
        children = self._items_by_parent.get(parent_id, [])
        if tipo_item:
            children = [c for c in children if c.get("tipo_item") == tipo_item]
        return children

    def get_fases(self) -> list[dict]:
        """Retorna todas as fases (items root)."""
        return self.get_children(None, tipo_item="fase")

    def get_grupos(self, fase_id: int) -> list[dict]:
        """Retorna todos os grupos de uma fase."""
        return self.get_children(fase_id, tipo_item="grupo")

    def get_tarefas(self, grupo_id: int) -> list[dict]:
        """Retorna todas as tarefas de um grupo."""
        return self.get_children(grupo_id, tipo_item="tarefa")

    def get_subtarefas(self, tarefa_id: int) -> list[dict]:
        """Retorna todas as subtarefas de uma tarefa."""
        return self.get_children(tarefa_id, tipo_item="subtarefa")

    def get_all_items(self) -> list[dict]:
        """Retorna todos os items carregados."""
        self._load_items()
        return self._items

    @property
    def total_items(self) -> int:
        """Total de items no checklist."""
        self._load_items()
        return len(self._items)

    @property
    def completed_items(self) -> int:
        """Total de items concluídos (somente tarefas/subtarefas folha)."""
        self._load_items()
        leaf_types = {"tarefa", "subtarefa"}
        return sum(1 for i in self._items if i.get("tipo_item") in leaf_types and bool(i.get("completed")))

    @property
    def progress_percentage(self) -> float:
        """Percentual de progresso (0-100)."""
        self._load_items()
        leaf_types = {"tarefa", "subtarefa"}
        leaves = [i for i in self._items if i.get("tipo_item") in leaf_types]
        if not leaves:
            return 0.0
        completed = sum(1 for i in leaves if bool(i.get("completed")))
        return round((completed / len(leaves)) * 100, 1)


class ComentariosDataLoader:
    """
    Carrega TODOS os comentários de uma implantação em uma única query.

    Antes: 1 query por tarefa para buscar comentários
    Depois: 1 query total
    """

    def __init__(self, implantacao_id: int):
        self.implantacao_id = implantacao_id
        self._comentarios_by_item: dict[int, list[dict]] = {}
        self._loaded = False

    def _load_comentarios(self) -> None:
        """Carrega todos os comentários em uma query."""
        if self._loaded:
            return

        try:
            comentarios = (
                query_db(
                    """
                SELECT cc.id, cc.item_id, cc.autor, cc.texto, cc.created_at,
                       cc.tag, cc.editado, cc.editado_em,
                       pu.nome AS autor_nome, pu.foto_url AS autor_foto
                FROM checklist_comentarios cc
                LEFT JOIN perfil_usuario pu ON pu.usuario = cc.autor
                WHERE cc.item_id IN (
                    SELECT id FROM checklist_items WHERE implantacao_id = %s
                )
                ORDER BY cc.created_at ASC
                """,
                    (self.implantacao_id,),
                )
                or []
            )
        except Exception as e:
            logger.error(f"Erro ao carregar comentários para implantação {self.implantacao_id}: {e}")
            comentarios = []

        for c in comentarios:
            item_id = c["item_id"]
            self._comentarios_by_item.setdefault(item_id, []).append(c)

        self._loaded = True

    def get_by_item(self, item_id: int) -> list[dict]:
        """Retorna comentários de um item específico."""
        self._load_comentarios()
        return self._comentarios_by_item.get(item_id, [])

    def get_all(self) -> dict[int, list[dict]]:
        """Retorna mapa de item_id → comentários."""
        self._load_comentarios()
        return self._comentarios_by_item

    @property
    def total_comentarios(self) -> int:
        """Total de comentários carregados."""
        self._load_comentarios()
        return sum(len(v) for v in self._comentarios_by_item.values())


class ImplantacaoDataLoader:
    """
    DataLoader combinado que carrega checklist + comentários de uma implantação.

    Uso simplificado:
        loader = ImplantacaoDataLoader(impl_id=42)
        data = loader.load_all()
    """

    def __init__(self, implantacao_id: int):
        self.implantacao_id = implantacao_id
        self.checklist = ChecklistDataLoader(implantacao_id)
        self.comentarios = ComentariosDataLoader(implantacao_id)

    def load_all(self) -> dict[str, Any]:
        """
        Carrega todos os dados necessários para a página de detalhes.

        Retorna um dicionário com toda a hierarquia montada (2-3 queries no total).
        """
        fases = self.checklist.get_fases()
        tarefas_agrupadas = OrderedDict()

        for fase in fases:
            grupos = self.checklist.get_grupos(fase["id"])

            for grupo in grupos:
                modulo_nome = grupo.get("title") or grupo.get("nome") or f"Grupo {grupo['id']}"
                tarefas = self.checklist.get_tarefas(grupo["id"])

                for tarefa in tarefas:
                    subtarefas = self.checklist.get_subtarefas(tarefa["id"])

                    if subtarefas:
                        for sub in subtarefas:
                            comentarios = self.comentarios.get_by_item(sub["id"])
                            tarefas_agrupadas.setdefault(modulo_nome, []).append(
                                {
                                    "id": sub["id"],
                                    "tarefa_filho": sub.get("title") or sub.get("nome"),
                                    "concluida": bool(sub.get("completed")),
                                    "tag": sub.get("tag", ""),
                                    "ordem": sub.get("ordem", 0),
                                    "responsavel": sub.get("responsavel"),
                                    "prazo_inicio": sub.get("prazo_inicio"),
                                    "prazo_fim": sub.get("prazo_fim"),
                                    "comentarios": comentarios,
                                    "toggle_url": f"/api/checklist/toggle/{sub['id']}",
                                    "comment_url": f"/api/checklist/comment/{sub['id']}",
                                    "delete_url": f"/api/checklist/delete/{sub['id']}",
                                }
                            )
                    else:
                        comentarios = self.comentarios.get_by_item(tarefa["id"])
                        tarefas_agrupadas.setdefault(modulo_nome, []).append(
                            {
                                "id": tarefa["id"],
                                "tarefa_filho": tarefa.get("title") or tarefa.get("nome"),
                                "concluida": bool(tarefa.get("completed")),
                                "tag": tarefa.get("tag", ""),
                                "ordem": tarefa.get("ordem", 0),
                                "responsavel": tarefa.get("responsavel"),
                                "prazo_inicio": tarefa.get("prazo_inicio"),
                                "prazo_fim": tarefa.get("prazo_fim"),
                                "comentarios": comentarios,
                                "toggle_url": f"/api/checklist/toggle/{tarefa['id']}",
                                "comment_url": f"/api/checklist/comment/{tarefa['id']}",
                                "delete_url": f"/api/checklist/delete/{tarefa['id']}",
                            }
                        )

                # Ordenar tarefas por ordem
                if modulo_nome in tarefas_agrupadas:
                    tarefas_agrupadas[modulo_nome].sort(key=lambda x: x.get("ordem", 0))

        return {
            "tarefas_agrupadas": tarefas_agrupadas,
            "progress": {
                "total": self.checklist.total_items,
                "completed": self.checklist.completed_items,
                "percentage": self.checklist.progress_percentage,
            },
            "total_comentarios": self.comentarios.total_comentarios,
            "todos_modulos": list(tarefas_agrupadas.keys()),
        }
