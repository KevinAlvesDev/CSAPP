"""
Tags analytics for the management dashboard.

This module aggregates comment tags (`comentarios_h.tag`) by user.
"""

from datetime import date, datetime
from typing import Any

from ....common.context_profiles import resolve_context


def get_tags_by_user_chart_data(
    cs_email: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    context: str | None = None,
) -> dict[str, Any]:
    """
    Returns comment-tag statistics grouped by user.
    Only comments with a non-empty tag are counted.
    """
    from flask import current_app

    from ....db import query_db

    is_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    def parse_date(date_str: str | date | datetime | None) -> str | None:
        if not date_str:
            return None
        if isinstance(date_str, (date, datetime)):
            return date_str.strftime("%Y-%m-%d")
        if "/" in date_str:
            parts = date_str.split("/")
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return date_str

    start_date = parse_date(start_date)
    end_date = parse_date(end_date)
    ctx = resolve_context(context)

    def date_col_expr(col: str) -> str:
        return f"date({col})" if is_sqlite else f"CAST({col} AS DATE)"

    query = """
        SELECT
            COALESCE(p.nome, ch.usuario_cs) AS user_name,
            TRIM(ch.tag) AS tag,
            COUNT(*) AS comment_count
        FROM comentarios_h ch
        LEFT JOIN perfil_usuario p ON ch.usuario_cs = p.usuario
        LEFT JOIN checklist_items ci ON ch.checklist_item_id = ci.id
        JOIN implantacoes i ON ci.implantacao_id = i.id
        LEFT JOIN perfil_usuario_contexto puc ON ch.usuario_cs = puc.usuario AND puc.contexto = COALESCE(i.contexto, 'onboarding')
        WHERE ch.usuario_cs IS NOT NULL
          AND ch.tag IS NOT NULL
          AND TRIM(ch.tag) <> ''
    """
    args: list[Any] = []

    if cs_email:
        query += " AND ch.usuario_cs = %s"
        args.append(cs_email)

    if start_date:
        query += f" AND {date_col_expr('ch.data_criacao')} >= %s"
        args.append(start_date)

    if end_date:
        query += f" AND {date_col_expr('ch.data_criacao')} <= %s"
        args.append(end_date)

    if ctx == "onboarding":
        query += " AND (i.contexto IS NULL OR i.contexto = 'onboarding') "
    else:
        query += " AND i.contexto = %s "
        args.append(ctx)

    query += """
        GROUP BY COALESCE(p.nome, ch.usuario_cs), TRIM(ch.tag)
        ORDER BY user_name, tag
    """

    rows = query_db(query, tuple(args)) or []

    users_data: dict[str, dict[str, int]] = {}
    tags_seen: set[str] = set()

    for row in rows:
        if not row or not isinstance(row, dict):
            continue

        user_name = row.get("user_name", "Desconhecido")
        tag = row.get("tag")
        if not tag:
            continue
        count = int(row.get("comment_count", 0) or 0)

        tags_seen.add(tag)
        users_data.setdefault(user_name, {})
        users_data[user_name][tag] = users_data[user_name].get(tag, 0) + count

    # Prefer configured comment tags order, then append any custom tags found.
    tags_config_rows = query_db(
        """
        SELECT nome
        FROM tags_sistema
        WHERE tipo IN ('comentario', 'ambos')
        ORDER BY ordem ASC, nome ASC
        """,
        (),
    ) or []
    configured_tags = [str(r.get("nome")) for r in tags_config_rows if isinstance(r, dict) and r.get("nome")]

    ordered_tags: list[str] = []
    for tag_name in configured_tags:
        if tag_name in tags_seen:
            ordered_tags.append(tag_name)

    for tag_name in sorted(tags_seen):
        if tag_name not in ordered_tags:
            ordered_tags.append(tag_name)

    sorted_users = sorted(users_data.keys())

    datasets = []
    for tag in ordered_tags:
        datasets.append(
            {
                "label": tag,
                "data": [users_data.get(user, {}).get(tag, 0) for user in sorted_users],
            }
        )

    total_tags_count = 0
    for user in sorted_users:
        total_tags_count += sum(users_data.get(user, {}).values())

    return {
        "labels": sorted_users,
        "datasets": datasets,
        "total_tasks": total_tags_count,
        "total_users": len(sorted_users),
        "total_tags": len(ordered_tags),
    }
