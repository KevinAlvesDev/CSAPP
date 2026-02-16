"""
Módulo de Histórico do Checklist
Histórico de responsáveis e prazos.
Princípio SOLID: Single Responsibility
"""

from ....db import query_db
from .utils import _format_datetime


def obter_historico_responsavel(item_id):
    """
    Retorna o histórico de alterações de responsável de um item.
    """
    entries = (
        query_db(
            """
        SELECT id, old_responsavel, new_responsavel, changed_by, changed_at
        FROM checklist_responsavel_history
        WHERE checklist_item_id = %s
        ORDER BY changed_at DESC
        """,
            (item_id,),
        )
        or []
    )

    for e in entries:
        e["changed_at"] = _format_datetime(e.get("changed_at"))

    return entries


def obter_historico_prazos(item_id):
    """
    Retorna o histórico de alterações de prazo de um item.
    """
    impl = query_db("SELECT implantacao_id FROM checklist_items WHERE id = %s", (item_id,), one=True)
    if not impl:
        raise ValueError("Item não encontrado")

    impl_id = impl["implantacao_id"]
    logs = (
        query_db(
            """
        SELECT id, usuario_cs, detalhes, data_criacao
        FROM timeline_log
        WHERE implantacao_id = %s AND tipo_evento = 'prazo_alterado'
        ORDER BY id DESC
        """,
            (impl_id,),
        )
        or []
    )

    entries = []

    # Buscar título do item para filtrar logs
    item_title = query_db("SELECT title FROM checklist_items WHERE id = %s", (item_id,), one=True)["title"]

    for log in logs:
        det = log.get("detalhes") or ""
        # Heuristic matching - filtrar logs que contêm o título do item
        if item_title in det:
            entries.append(
                {
                    "usuario_cs": log.get("usuario_cs"),
                    "detalhes": det,
                    "data_criacao": _format_datetime(log.get("data_criacao")),
                }
            )

    return entries
