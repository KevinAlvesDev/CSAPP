"""
New function to get tags statistics by user for the management dashboard.
This provides insights into task completion patterns by tag type.
"""

from typing import Dict, List, Optional, Any
from datetime import date, datetime


def get_tags_by_user_chart_data(
    cs_email: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieves task completion statistics grouped by tag and user.
    
    Args:
        cs_email: Optional filter for specific user
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    
    Returns:
        Dictionary with chart data in Chart.js format:
        {
            'labels': ['User 1', 'User 2', ...],
            'datasets': [
                {
                    'label': 'Ação interna',
                    'data': [count_user1, count_user2, ...],
                    'backgroundColor': 'rgba(...)'
                },
                ...
            ]
        }
    """
    from flask import current_app
    from ..db import query_db
    
    is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    
    # Build the query
    query = """
        SELECT 
            u.nome as user_name,
            ci.tag as tag,
            COUNT(DISTINCT ci.id) as task_count
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        JOIN perfil_usuario u ON i.usuario_cs = u.usuario
        WHERE ci.completed = TRUE
          AND ci.data_conclusao IS NOT NULL
          AND ci.tag IS NOT NULL
          AND ci.tag != ''
    """
    
    args = []
    
    # Apply filters
    if cs_email:
        query += " AND i.usuario_cs = %s"
        args.append(cs_email)
    
    # Date filtering helper
    def date_col_expr(col: str) -> str:
        return f"date({col})" if is_sqlite else f"CAST({col} AS DATE)"
    
    def date_param_expr() -> str:
        return "date(%s)" if is_sqlite else "CAST(%s AS DATE)"
    
    if start_date:
        query += f" AND {date_col_expr('ci.data_conclusao')} >= {date_param_expr()}"
        args.append(start_date)
    
    if end_date:
        query += f" AND {date_col_expr('ci.data_conclusao')} <= {date_param_expr()}"
        args.append(end_date)
    
    query += " GROUP BY u.nome, ci.tag ORDER BY u.nome, task_count DESC"
    
    # Execute query
    rows = query_db(query, tuple(args)) or []
    
    # Process results
    users_data = {}
    all_tags = set()
    
    for row in rows:
        if not row or not isinstance(row, dict):
            continue
            
        user_name = row.get('user_name', 'Desconhecido')
        tag = row.get('tag', 'Sem tag')
        count = row.get('task_count', 0)
        
        if user_name not in users_data:
            users_data[user_name] = {}
        
        users_data[user_name][tag] = count
        all_tags.add(tag)
    
    # Ensure standard tags always appear in the table
    standard_tags = ['Ação interna', 'Reunião', 'Cliente', 'Rede', 'No Show']
    for tag in standard_tags:
        all_tags.add(tag)
    
    # Sort tags: standard tags first, then others alphabetically
    def tag_sort_key(tag):
        if tag in standard_tags:
            return (0, standard_tags.index(tag))
        else:
            return (1, tag)  # Other tags alphabetically
    
    sorted_tags = sorted(all_tags, key=tag_sort_key)
    sorted_users = sorted(users_data.keys())
    
    # Define colors for each tag type
    tag_colors = {
        'Ação interna': 'rgba(54, 162, 235, 0.7)',   # Blue
        'Reunião': 'rgba(255, 99, 132, 0.7)',        # Red
        'Cliente': 'rgba(75, 192, 192, 0.7)',        # Teal
        'Rede': 'rgba(255, 159, 64, 0.7)',           # Orange
        'No Show': 'rgba(153, 102, 255, 0.7)',       # Purple
    }
    
    # Build datasets for Chart.js
    datasets = []
    for tag in sorted_tags:
        dataset = {
            'label': tag,
            'data': [users_data.get(user, {}).get(tag, 0) for user in sorted_users],
            'backgroundColor': tag_colors.get(tag, 'rgba(153, 102, 255, 0.7)'),
            'borderColor': tag_colors.get(tag, 'rgba(153, 102, 255, 1)').replace('0.7', '1'),
            'borderWidth': 1
        }
        datasets.append(dataset)
    
    return {
        'labels': sorted_users,
        'datasets': datasets,
        'total_tasks': sum(row.get('task_count', 0) for row in rows if row),
        'total_users': len(sorted_users),
        'total_tags': len(sorted_tags)
    }
