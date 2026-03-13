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
    from ....db import query_db

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
        return f"CAST({col} AS DATE)"

    query = """
        WITH base AS (
            SELECT
                COALESCE(p.nome, ch.usuario_cs) AS user_name,
                BTRIM(ch.tag, E' \\t\\n\\r') AS tag,
                LOWER(BTRIM(ch.visibilidade, E' \\t\\n\\r')) AS visibilidade,
                ch.usuario_cs,
                ch.data_criacao,
                i.contexto
            FROM comentarios_h ch
            LEFT JOIN perfil_usuario p ON ch.usuario_cs = p.usuario
            LEFT JOIN checklist_items ci ON ch.checklist_item_id = ci.id
            JOIN implantacoes i ON i.id = COALESCE(ci.implantacao_id, ch.implantacao_id)
            LEFT JOIN perfil_usuario_contexto puc ON ch.usuario_cs = puc.usuario AND puc.contexto = COALESCE(i.contexto, 'onboarding')
            WHERE ch.usuario_cs IS NOT NULL
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
        )
        SELECT
            user_name,
            tag_label AS tag,
            COUNT(*) AS comment_count
        FROM (
            SELECT user_name, tag AS tag_label
            FROM base
            WHERE tag IS NOT NULL AND tag <> ''
            UNION ALL
            SELECT user_name,
                   CASE
                       WHEN visibilidade = 'interno' THEN 'Interno'
                       WHEN visibilidade = 'externo' THEN 'Externo'
                       ELSE NULL
                   END AS tag_label
            FROM base
            WHERE visibilidade IN ('interno', 'externo')
        ) t
        WHERE tag_label IS NOT NULL AND tag_label <> ''
        GROUP BY user_name, tag_label
        ORDER BY user_name, tag_label
    """

    rows = query_db(query, tuple(args)) or []

    # Base users list for zero-filled visualization
    users_base: list[str] = []
    if cs_email:
        user_row = query_db(
            "SELECT nome FROM perfil_usuario WHERE usuario = %s",
            (cs_email,),
            one=True,
        )
        if user_row and isinstance(user_row, dict) and user_row.get("nome"):
            users_base = [str(user_row.get("nome"))]
        else:
            users_base = [cs_email]
    else:
        users_rows = query_db(
            """
            SELECT COALESCE(puc.perfil_acesso, 'Sem Acesso') as perfil, u.nome, u.usuario
            FROM perfil_usuario u
            LEFT JOIN perfil_usuario_contexto puc ON u.usuario = puc.usuario AND puc.contexto = %s
            WHERE COALESCE(puc.perfil_acesso, 'Sem Acesso') IS NOT NULL
              AND COALESCE(puc.perfil_acesso, 'Sem Acesso') != ''
            ORDER BY u.nome
            """,
            (ctx,),
        ) or []
        for row in users_rows:
            if not row or not isinstance(row, dict):
                continue
            users_base.append(str(row.get("nome") or row.get("email") or "").strip())
        users_base = [u for u in users_base if u]

    users_data: dict[str, dict[str, int]] = {}
    tags_seen: set[str] = set()

    def normalize_tag(tag_value: Any) -> str | None:
        if tag_value is None:
            return None
        tag_str = str(tag_value).replace("\u00a0", " ").strip()
        if not tag_str:
            return None
        # Normalize case/aliases for known tags so " INTERNO", "interno", etc. match.
        tag_key = tag_str.casefold()
        canonical_map = {
            "interno": "Interno",
            "externo": "Externo",
            "ação interna": "Ação interna",
            "acao interna": "Ação interna",
            "reunião": "Reunião",
            "reuniao": "Reunião",
            "no show": "No Show",
            "simples registro": "Simples registro",
            "visita": "Visita",
            "live": "Live",
        }
        return canonical_map.get(tag_key, tag_str)

    for row in rows:
        if not row or not isinstance(row, dict):
            continue

        user_name = row.get("user_name", "Desconhecido")
        tag = normalize_tag(row.get("tag"))
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
    configured_tags: list[str] = []
    for r in tags_config_rows:
        if not isinstance(r, dict):
            continue
        tag_name = normalize_tag(r.get("nome"))
        if tag_name:
            configured_tags.append(tag_name)
    # Include all valid comment tags, even if no data yet
    try:
        from ....blueprints.checklist_api import _VALID_COMMENT_TAGS  # noqa: WPS450
        valid_comment_tags = [t for t in (normalize_tag(t) for t in _VALID_COMMENT_TAGS) if t]
    except Exception:
        valid_comment_tags = ["Ação interna", "Reunião", "No Show", "Simples registro", "Visita", "Live"]
        valid_comment_tags = [t for t in (normalize_tag(t) for t in valid_comment_tags) if t]

    for base_tag in ["Interno", "Externo"]:
        if base_tag not in configured_tags:
            configured_tags.append(base_tag)

    ordered_tags: list[str] = []
    for tag_name in configured_tags:
        if tag_name not in ordered_tags:
            ordered_tags.append(tag_name)

    for tag_name in valid_comment_tags:
        if tag_name not in ordered_tags:
            ordered_tags.append(tag_name)

    for tag_name in sorted(tags_seen):
        if tag_name not in ordered_tags:
            ordered_tags.append(tag_name)

    sorted_users = sorted({*users_base, *users_data.keys()})

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
