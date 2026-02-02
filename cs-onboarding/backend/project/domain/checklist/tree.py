"""
Módulo de Árvore do Checklist
Construção de árvore hierárquica e cálculo de progresso.
Princípio SOLID: Single Responsibility
"""

import logging
from datetime import datetime, timezone

from flask import current_app

from ...common.exceptions import DatabaseError
from ...db import db_transaction_with_lock, query_db
from .utils import _format_datetime

logger = logging.getLogger(__name__)


def get_checklist_tree(implantacao_id=None, root_item_id=None, include_progress=True):
    """
    Retorna a árvore completa do checklist.
    """
    try:
        if implantacao_id:
            implantacao_id = int(implantacao_id)
        if root_item_id:
            root_item_id = int(root_item_id)
    except (ValueError, TypeError):
        raise ValueError("IDs devem ser inteiros válidos") from None

    with db_transaction_with_lock() as (conn, cursor, db_type):
        try:
            query = ""
            params = []

            if db_type == "postgres":
                if implantacao_id:
                    query = """
                        SELECT
                            id, parent_id, title, completed, comment,
                            level, ordem, implantacao_id, obrigatoria, tag,
                            responsavel, previsao_original, nova_previsao, data_conclusao,
                            created_at, updated_at
                        FROM checklist_items
                        WHERE implantacao_id = %s
                        ORDER BY ordem ASC, id ASC
                    """
                    params = (implantacao_id,)
                elif root_item_id:
                    query = """
                        WITH RECURSIVE subtree AS (
                            SELECT id, parent_id, title, completed, comment,
                                   level, ordem, implantacao_id, obrigatoria, tag,
                                   created_at, updated_at
                            FROM checklist_items
                            WHERE id = %s

                            UNION ALL

                            SELECT ci.id, ci.parent_id, ci.title, ci.completed, ci.comment,
                                   ci.level, ci.ordem, ci.implantacao_id, ci.obrigatoria, ci.tag,
                                   ci.created_at, ci.updated_at
                            FROM checklist_items ci
                            INNER JOIN subtree st ON ci.parent_id = st.id
                        )
                        SELECT * FROM subtree
                        ORDER BY ordem ASC, id ASC
                    """
                    params = (root_item_id,)
            else:
                if implantacao_id:
                    query = """
                        SELECT
                            id, parent_id, title, completed, comment,
                            level, ordem, implantacao_id, obrigatoria, tag,
                            responsavel, previsao_original, nova_previsao, data_conclusao,
                            created_at, updated_at
                        FROM checklist_items
                        WHERE implantacao_id = ?
                        ORDER BY ordem ASC, id ASC
                    """
                    params = (implantacao_id,)
                elif root_item_id:
                    query = """
                        WITH RECURSIVE subtree(id, parent_id, title, completed, comment,
                                               level, ordem, implantacao_id, obrigatoria, tag, created_at, updated_at) AS (
                            SELECT id, parent_id, title, completed, comment,
                                   level, ordem, implantacao_id, obrigatoria, tag, created_at, updated_at
                            FROM checklist_items
                            WHERE id = ?

                            UNION ALL

                            SELECT ci.id, ci.parent_id, ci.title, ci.completed, ci.comment,
                                   ci.level, ci.ordem, ci.implantacao_id, ci.obrigatoria, ci.tag, ci.created_at, ci.updated_at
                            FROM checklist_items ci
                            INNER JOIN subtree st ON ci.parent_id = st.id
                        )
                        SELECT * FROM subtree
                        ORDER BY ordem ASC, id ASC
                    """
                    params = (root_item_id,)

            if not query:
                query = "SELECT id, parent_id, title, completed, comment, level, ordem, implantacao_id, obrigatoria, tag, responsavel, previsao_original, nova_previsao, data_conclusao, created_at, updated_at FROM checklist_items ORDER BY ordem ASC, id ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = []
            col_names = [d[0] for d in cursor.description]

            # OTIMIZAÇÃO: Buscar todos os nomes de responsáveis de uma vez (evita N+1)
            responsaveis_emails = set()
            for row in rows:
                item = row if isinstance(row, dict) else dict(zip(col_names, row, strict=False))
                resp = item.get("responsavel")
                if resp and "@" in resp:
                    responsaveis_emails.add(resp)

            # Buscar todos os nomes em uma única query
            responsaveis_map = {}
            if responsaveis_emails:
                placeholder = (
                    ",".join(["%s"] * len(responsaveis_emails))
                    if db_type == "postgres"
                    else ",".join(["?"] * len(responsaveis_emails))
                )
                resp_query = f"SELECT usuario, nome FROM perfil_usuario WHERE usuario IN ({placeholder})"
                cursor.execute(resp_query, tuple(responsaveis_emails))
                for resp_row in cursor.fetchall():
                    if isinstance(resp_row, dict):
                        responsaveis_map[resp_row["usuario"]] = resp_row["nome"]
                    else:
                        responsaveis_map[resp_row[0]] = resp_row[1]

            # OTIMIZAÇÃO: Calcular progresso de todos os itens de uma vez (evita N+1)
            progress_map = {}
            if include_progress and rows:
                # Coletar todos os IDs
                all_ids = [
                    row["id"] if isinstance(row, dict) else dict(zip(col_names, row, strict=False))["id"]
                    for row in rows
                ]

                # Calcular progresso em batch
                if db_type == "postgres":
                    progress_query = """
                        WITH RECURSIVE all_children AS (
                            SELECT parent_id, id, completed
                            FROM checklist_items
                            WHERE parent_id = ANY(%s)

                            UNION ALL

                            SELECT ci.parent_id, ci.id, ci.completed
                            FROM checklist_items ci
                            INNER JOIN all_children ac ON ci.parent_id = ac.id
                        )
                        SELECT
                            parent_id,
                            COUNT(*) as total,
                            COUNT(CASE WHEN completed = true THEN 1 END) as completed
                        FROM all_children
                        WHERE parent_id IS NOT NULL
                        GROUP BY parent_id
                    """
                    cursor.execute(progress_query, (all_ids,))
                else:
                    # SQLite: processar em lote menor ou manter lógica original
                    # Por simplicidade, vamos manter a lógica individual para SQLite
                    pass

                if db_type == "postgres":
                    for prog_row in cursor.fetchall():
                        if isinstance(prog_row, dict):
                            item_id = prog_row["parent_id"]
                            progress_map[item_id] = {
                                "total": prog_row["total"] or 0,
                                "completed": prog_row["completed"] or 0,
                                "has_children": (prog_row["total"] or 0) > 0,
                            }
                        else:
                            item_id = prog_row[0]
                            progress_map[item_id] = {
                                "total": prog_row[1] or 0,
                                "completed": prog_row[2] or 0,
                                "has_children": (prog_row[1] or 0) > 0,
                            }

            for row in rows:
                item = row if isinstance(row, dict) else dict(zip(col_names, row, strict=False))

                item_dict = {
                    "id": item["id"],
                    "parent_id": item.get("parent_id") if isinstance(item, dict) else item["parent_id"],
                    "title": item.get("title") if isinstance(item, dict) else item["title"],
                    "completed": bool(item.get("completed") if isinstance(item, dict) else item["completed"]),
                    "comment": item.get("comment") if isinstance(item, dict) else item["comment"],
                    "level": item.get("level") if isinstance(item, dict) else item["level"],
                    "ordem": item.get("ordem") if isinstance(item, dict) else item["ordem"],
                    "implantacao_id": item.get("implantacao_id") if isinstance(item, dict) else item["implantacao_id"],
                    "obrigatoria": bool(item.get("obrigatoria") if isinstance(item, dict) else item["obrigatoria"]),
                    "tag": item.get("tag") if isinstance(item, dict) else item["tag"],
                    "responsavel": item.get("responsavel") if isinstance(item, dict) else item.get("responsavel", None),
                    "previsao_original": _format_datetime(
                        (
                            item.get("previsao_original")
                            if isinstance(item, dict)
                            else item.get("previsao_original", None)
                        )
                    ),
                    "nova_previsao": _format_datetime(
                        (item.get("nova_previsao") if isinstance(item, dict) else item.get("nova_previsao", None))
                    ),
                    "data_conclusao": _format_datetime(
                        (item.get("data_conclusao") if isinstance(item, dict) else item.get("data_conclusao", None))
                    ),
                    "created_at": _format_datetime(
                        (item.get("created_at") if isinstance(item, dict) else item.get("created_at", None))
                    ),
                    "updated_at": _format_datetime(
                        (item.get("updated_at") if isinstance(item, dict) else item.get("updated_at", None))
                    ),
                }

                # Usar mapa de responsáveis (já carregado)
                resp = item_dict.get("responsavel")
                if resp and "@" in resp and resp in responsaveis_map:
                    item_dict["responsavel"] = responsaveis_map[resp]

                ref_dt = item_dict["nova_previsao"] or item_dict["previsao_original"]
                item_dict["atrasada"] = bool(
                    ref_dt and not item_dict["completed"] and ref_dt < _format_datetime(datetime.now(timezone.utc))
                )

                if include_progress:
                    # Usar mapa de progresso (já calculado) ou calcular individualmente
                    if item_dict["id"] in progress_map:
                        stats = progress_map[item_dict["id"]]
                    else:
                        # Fallback para SQLite ou itens sem filhos
                        stats = get_item_progress_stats(item_dict["id"], db_type, cursor)

                    item_dict["progress"] = {
                        "total": stats["total"],
                        "completed": stats["completed"],
                        "has_children": stats["has_children"],
                    }
                    item_dict["progress_label"] = (
                        f"{stats['completed']}/{stats['total']}" if stats["has_children"] else None
                    )

                result.append(item_dict)

            return result

        except Exception as e:
            logger.error(f"Erro ao buscar árvore do checklist: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao buscar checklist: {e}") from e


def build_nested_tree(flat_items):
    """
    Converte lista plana em árvore aninhada (JSON).
    """
    items_map = {item["id"]: {**item, "children": []} for item in flat_items}
    root_items = []

    for item in flat_items:
        item_id = item["id"]
        parent_id = item["parent_id"]

        if parent_id is None:
            root_items.append(items_map[item_id])
        else:
            if parent_id in items_map:
                items_map[parent_id]["children"].append(items_map[item_id])

    def sort_children(item):
        item["children"].sort(key=lambda x: (x.get("ordem", 0), x.get("id", 0)))
        for child in item["children"]:
            sort_children(child)

    for root in root_items:
        sort_children(root)

    root_items.sort(key=lambda x: (x.get("ordem", 0), x.get("id", 0)))

    return root_items


def get_item_progress_stats(item_id, db_type=None, cursor=None):
    """
    Calcula estatísticas de progresso para um item (total de filhos e quantos estão completos).
    """
    if cursor is None and db_type is None:
        use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False) if current_app else False
        db_type = "sqlite" if use_sqlite else "postgres"

    if db_type == "postgres":
        stats_query = """
            WITH RECURSIVE all_children AS (
                SELECT id, completed
                FROM checklist_items
                WHERE parent_id = %s

                UNION ALL

                SELECT ci.id, ci.completed
                FROM checklist_items ci
                INNER JOIN all_children ac ON ci.parent_id = ac.id
            )
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN completed = true THEN 1 END) as completed
            FROM all_children
        """
        if cursor:
            cursor.execute(stats_query, (item_id,))
            result = cursor.fetchone()
            if result:
                return {"total": result[0] or 0, "completed": result[1] or 0, "has_children": (result[0] or 0) > 0}
        else:
            result = query_db(stats_query, (item_id,), one=True)
            if result:
                return {
                    "total": result.get("total", 0) or 0,
                    "completed": result.get("completed", 0) or 0,
                    "has_children": (result.get("total", 0) or 0) > 0,
                }
    else:
        stats_query = """
            WITH RECURSIVE all_children(id, completed) AS (
                SELECT id, completed
                FROM checklist_items
                WHERE parent_id = ?

                UNION ALL

                SELECT ci.id, ci.completed
                FROM checklist_items ci
                INNER JOIN all_children ac ON ci.parent_id = ac.id
            )
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN completed = 1 THEN 1 END) as completed
            FROM all_children
        """
        if cursor:
            cursor.execute(stats_query, (item_id,))
            row = cursor.fetchone()
            if row:
                return {"total": row[0] or 0, "completed": row[1] or 0, "has_children": (row[0] or 0) > 0}
        else:
            result = query_db(stats_query, (item_id,), one=True)
            if result:
                if isinstance(result, dict):
                    return {
                        "total": result.get("total", 0) or 0,
                        "completed": result.get("completed", 0) or 0,
                        "has_children": (result.get("total", 0) or 0) > 0,
                    }
                else:
                    return {"total": result[0] or 0, "completed": result[1] or 0, "has_children": (result[0] or 0) > 0}

    return {"total": 0, "completed": 0, "has_children": False}


def obter_progresso_global_service(implantacao_id):
    """
    Calcula o progresso global de uma implantação (apenas itens folha).
    """
    use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    if use_sqlite:
        progress_query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
            FROM checklist_items ci
            WHERE ci.implantacao_id = ?
            AND NOT EXISTS (
                SELECT 1 FROM checklist_items filho
                WHERE filho.parent_id = ci.id
                AND filho.implantacao_id = ?
            )
        """
        res = query_db(progress_query, (implantacao_id, implantacao_id), one=True)
    else:
        progress_query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completed
            FROM checklist_items ci
            WHERE ci.implantacao_id = %s
            AND NOT EXISTS (
                SELECT 1 FROM checklist_items filho
                WHERE filho.parent_id = ci.id
                AND filho.implantacao_id = %s
            )
        """
        res = query_db(progress_query, (implantacao_id, implantacao_id), one=True)

    if res:
        total = int(res.get("total", 0) or 0)
        completed = int(res.get("completed", 0) or 0)
        if total > 0:
            return round((completed / total) * 100, 2)
        else:
            return 0.0
    return 0.0
