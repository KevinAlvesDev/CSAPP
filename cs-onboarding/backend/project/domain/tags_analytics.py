"""
New function to get tags statistics by user for the management dashboard.
This provides insights into comment tag patterns by user.
"""

from datetime import date, datetime
from typing import Any, Dict, Optional


def get_tags_by_user_chart_data(
    cs_email: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves comment tag statistics grouped by user.
    Tags are stored in comentarios_h table:
    - visibilidade: 'interno' or 'externo'
    - tag: 'Ação interna', 'Reunião', 'No Show', etc.

    Args:
        cs_email: Optional filter for specific user
        start_date: Optional start date filter (YYYY-MM-DD or DD/MM/YYYY)
        end_date: Optional end date filter (YYYY-MM-DD or DD/MM/YYYY)

    Returns:
        Dictionary with chart data in Chart.js format
    """
    from flask import current_app

    from ..db import query_db

    is_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    # Helper to parse date
    def parse_date(date_str):
        if not date_str:
            return None
        if isinstance(date_str, (date, datetime)):
            return date_str.strftime("%Y-%m-%d")
        # Try DD/MM/YYYY format (Brazilian)
        if "/" in date_str:
            parts = date_str.split("/")
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return date_str

    start_date = parse_date(start_date)
    end_date = parse_date(end_date)

    # Build the query - now from comentarios_h
    query = """
        SELECT
        COALESCE(p.nome, ch.usuario_cs) as user_name,
        ch.visibilidade as visibilidade,
        ch.tag as tag,
        COUNT(*) as comment_count
        FROM comentarios_h ch
        LEFT JOIN perfil_usuario p ON ch.usuario_cs = p.usuario
        WHERE ch.usuario_cs IS NOT NULL
    """

    args = []

    # Apply filters
    if cs_email:
        query += " AND ch.usuario_cs = %s"
        args.append(cs_email)

    # Date filtering
    def date_col_expr(col: str) -> str:
        return f"date({col})" if is_sqlite else f"CAST({col} AS DATE)"

    def date_param_expr() -> str:
        return "%s"

    if start_date:
        query += f" AND {date_col_expr('ch.data_criacao')} >= {date_param_expr()}"
        args.append(start_date)

    if end_date:
        query += f" AND {date_col_expr('ch.data_criacao')} <= {date_param_expr()}"
        args.append(end_date)

    query += " GROUP BY COALESCE(p.nome, ch.usuario_cs), ch.visibilidade, ch.tag ORDER BY user_name"

    # Execute query
    rows = query_db(query, tuple(args)) or []

    # Process results
    users_data = {}

    for row in rows:
        if not row or not isinstance(row, dict):
            continue

        user_name = row.get("user_name", "Desconhecido")
        visibilidade = row.get("visibilidade") or "interno"
        tag = row.get("tag") or "Sem tag"
        count = row.get("comment_count", 0)

        if user_name not in users_data:
            users_data[user_name] = {
                "Interno": 0,
                "Externo": 0,
                "Ação interna": 0,
                "Reunião": 0,
                "No Show": 0,
                "Simples registro": 0,
                "Sem tag": 0,
            }

        # Count by visibility
        if visibilidade == "interno":
            users_data[user_name]["Interno"] += count
        elif visibilidade == "externo":
            users_data[user_name]["Externo"] += count

        # Count by tag type
        if tag in users_data[user_name]:
            users_data[user_name][tag] += count
        else:
            users_data[user_name]["Sem tag"] += count

    sorted_users = sorted(users_data.keys())

    # Define columns/tags to show
    display_tags = ["Interno", "Externo", "Ação interna", "Reunião", "No Show", "Simples registro"]

    # Define colors for each tag type
    tag_colors = {
        "Interno": "rgba(108, 117, 125, 0.7)",  # Gray
        "Externo": "rgba(23, 162, 184, 0.7)",  # Cyan
        "Ação interna": "rgba(54, 162, 235, 0.7)",  # Blue
        "Reunião": "rgba(40, 167, 69, 0.7)",  # Green
        "No Show": "rgba(220, 53, 69, 0.7)",  # Red
        "Simples registro": "rgba(153, 102, 255, 0.7)",  # Purple
    }

    # Build datasets for Chart.js
    datasets = []
    for tag in display_tags:
        dataset = {
            "label": tag,
            "data": [users_data.get(user, {}).get(tag, 0) for user in sorted_users],
            "backgroundColor": tag_colors.get(tag, "rgba(153, 102, 255, 0.7)"),
            "borderColor": tag_colors.get(tag, "rgba(153, 102, 255, 1)").replace("0.7", "1"),
            "borderWidth": 1,
        }
        datasets.append(dataset)

    # Calculate total
    total_comments = sum(
        users_data.get(user, {}).get("Interno", 0) + users_data.get(user, {}).get("Externo", 0) for user in sorted_users
    )

    return {
        "labels": sorted_users,
        "datasets": datasets,
        "total_tasks": total_comments,
        "total_users": len(sorted_users),
        "total_tags": len(display_tags),
    }
