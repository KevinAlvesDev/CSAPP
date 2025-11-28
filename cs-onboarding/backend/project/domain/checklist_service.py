"""
Serviço de Checklist Hierárquico Infinito
Implementa lógica de propagação de status (cascata e bolha) usando CTEs recursivas.
"""

from flask import current_app, g
from datetime import datetime
from ..db import query_db, execute_db, db_transaction_with_lock
from ..common.validation import sanitize_string, ValidationError
from ..common.exceptions import DatabaseError
import logging

logger = logging.getLogger(__name__)


def _format_datetime(dt_value):
    """Formata datetime para string ISO, compatível com PostgreSQL e SQLite."""
    if not dt_value:
        return None
    if isinstance(dt_value, str):
        return dt_value
    if hasattr(dt_value, 'isoformat'):
        return dt_value.isoformat()
    return str(dt_value)


def toggle_item_status(item_id, new_status, usuario_email=None):
    """
    Alterna o status de um item do checklist e propaga mudanças para toda a hierarquia.
    
    Lógica:
    - Cascata (Downstream): Marca/desmarca todos os descendentes
    - Bolha (Upstream): Atualiza pais baseado no status dos filhos
    
    Args:
        item_id: ID do item a ser alterado
        new_status: Boolean - True para concluído, False para pendente
        usuario_email: Email do usuário (para logging)
    
    Returns:
        dict: {
            'ok': bool,
            'items_updated': int,  # Quantidade de itens atualizados
            'progress': float  # Progresso global (0-100)
        }
    
    Raises:
        DatabaseError: Se houver erro na transação
    """
    try:
        item_id = int(item_id)
        new_status = bool(new_status)
    except (ValueError, TypeError):
        raise ValueError(f"item_id deve ser um inteiro válido e new_status deve ser booleano")
    
    usuario_email = usuario_email or (g.user_email if hasattr(g, 'user_email') else None)
    
    with db_transaction_with_lock() as (conn, cursor, db_type):
        try:
            # Verificar se item existe e obter parent_id para propagação upstream
            if db_type == 'postgres':
                check_query = """
                    SELECT id, parent_id, title, completed, implantacao_id
                    FROM checklist_items 
                    WHERE id = %s
                    FOR UPDATE
                """
                cursor.execute(check_query, (item_id,))
                item = cursor.fetchone()
            else:  # SQLite
                check_query = """
                    SELECT id, parent_id, title, completed, implantacao_id
                    FROM checklist_items 
                    WHERE id = ?
                """
                cursor.execute(check_query, (item_id,))
                row = cursor.fetchone()
                if row:
                    item = dict(zip([desc[0] for desc in cursor.description], row))
                else:
                    item = None
            
            if not item:
                raise ValueError(f"Item {item_id} não encontrado")
            
            implantacao_id = item.get('implantacao_id')
            
            # CTE RECURSIVA para cascata downstream (marcar/desmarcar todos os descendentes)
            if db_type == 'postgres':
                # PostgreSQL: Usar CTE recursiva em uma única query
                cascade_query = """
                    WITH RECURSIVE descendants AS (
                        -- Caso base: o item inicial
                        SELECT id, parent_id, %s::boolean as new_status
                        FROM checklist_items
                        WHERE id = %s
                        
                        UNION ALL
                        
                        -- Caso recursivo: todos os filhos
                        SELECT ci.id, ci.parent_id, d.new_status
                        FROM checklist_items ci
                        INNER JOIN descendants d ON ci.parent_id = d.id
                    )
                    UPDATE checklist_items ci
                    SET completed = d.new_status,
                        updated_at = %s
                    FROM descendants d
                    WHERE ci.id = d.id
                    RETURNING ci.id
                """
                cursor.execute(cascade_query, (new_status, item_id, datetime.now()))
                updated_ids = [row[0] for row in cursor.fetchall()]
                items_updated_downstream = len(updated_ids)
            else:
                # SQLite: SQLite suporta CTE recursiva, mas sintaxe ligeiramente diferente
                cascade_query = """
                    WITH RECURSIVE descendants(id, parent_id, new_status) AS (
                        -- Caso base
                        SELECT id, parent_id, ? as new_status
                        FROM checklist_items
                        WHERE id = ?
                        
                        UNION ALL
                        
                        -- Caso recursivo
                        SELECT ci.id, ci.parent_id, d.new_status
                        FROM checklist_items ci
                        INNER JOIN descendants d ON ci.parent_id = d.id
                    )
                    UPDATE checklist_items
                    SET completed = (SELECT new_status FROM descendants WHERE descendants.id = checklist_items.id),
                        updated_at = ?
                    WHERE id IN (SELECT id FROM descendants)
                """
                cursor.execute(cascade_query, (new_status, item_id, datetime.now()))
                items_updated_downstream = cursor.rowcount
            
            # Propagação upstream (bolha): Atualizar pais baseado no status dos filhos
            # Se todos os filhos estão true, pai vira true
            # Se qualquer filho está false, pai vira false
            # Usar abordagem iterativa para garantir atualização correta de todos os níveis
            if db_type == 'postgres':
                # Primeiro, encontrar todos os ancestrais que precisam ser atualizados
                ancestors_query = """
                    WITH RECURSIVE ancestors AS (
                        -- Começar do pai do item alterado
                        SELECT id, parent_id
                        FROM checklist_items
                        WHERE id = (SELECT parent_id FROM checklist_items WHERE id = %s)
                        
                        UNION ALL
                        
                        -- Subir recursivamente para os pais superiores
                        SELECT ci.id, ci.parent_id
                        FROM checklist_items ci
                        INNER JOIN ancestors a ON ci.id = a.parent_id
                        WHERE ci.parent_id IS NOT NULL
                    )
                    SELECT DISTINCT id as ancestor_id
                    FROM ancestors
                    WHERE id IS NOT NULL
                    ORDER BY ancestor_id
                """
                cursor.execute(ancestors_query, (item_id,))
                ancestor_rows = cursor.fetchall()
                ancestor_ids = [row[0] for row in ancestor_rows] if ancestor_rows else []
                
                items_updated_upstream = 0
                # Atualizar cada ancestral: verificar se todos os filhos diretos estão completos
                for ancestor_id in ancestor_ids:
                    # Primeiro, calcular o novo status baseado nos filhos diretos
                    check_children_query = """
                        SELECT 
                            COUNT(*) as total_filhos,
                            COUNT(CASE WHEN completed = true THEN 1 END) as filhos_completos
                        FROM checklist_items
                        WHERE parent_id = %s
                    """
                    cursor.execute(check_children_query, (ancestor_id,))
                    children_result = cursor.fetchone()
                    
                    if children_result:
                        total_filhos = children_result[0] or 0
                        filhos_completos = children_result[1] or 0
                        
                        # Determinar novo status
                        if total_filhos == 0:
                            # Sem filhos, manter status atual (não atualizar)
                            continue
                        else:
                            new_parent_status = (filhos_completos == total_filhos)
                        
                        # Atualizar o pai
                        update_parent_query = """
                            UPDATE checklist_items
                            SET completed = %s,
                                updated_at = %s
                            WHERE id = %s
                            RETURNING id
                        """
                        cursor.execute(update_parent_query, (new_parent_status, datetime.now(), ancestor_id))
                        if cursor.fetchone():
                            items_updated_upstream += 1
            else:
                # SQLite: Mesma lógica mas com sintaxe adaptada
                ancestors_query = """
                    WITH RECURSIVE ancestors(id, parent_id) AS (
                        SELECT id, parent_id
                        FROM checklist_items
                        WHERE id = ?
                        
                        UNION ALL
                        
                        SELECT ci.id, ci.parent_id
                        FROM checklist_items ci
                        INNER JOIN ancestors a ON ci.id = a.parent_id
                        WHERE ci.parent_id IS NOT NULL
                    )
                    SELECT DISTINCT parent_id FROM ancestors WHERE parent_id IS NOT NULL
                """
                cursor.execute(ancestors_query, (item_id,))
                ancestor_rows = cursor.fetchall()
                ancestor_ids = [row[0] for row in ancestor_rows] if ancestor_rows else []
                
                items_updated_upstream = 0
                # Para cada ancestral, atualizar baseado nos filhos
                for ancestor_id in ancestor_ids:
                    update_parent_query = """
                        UPDATE checklist_items
                        SET completed = (
                            SELECT 
                                CASE 
                                    WHEN COUNT(*) = 0 THEN completed  -- Se não tem filhos, mantém status
                                    WHEN COUNT(*) = COUNT(CASE WHEN completed = 1 THEN 1 END) THEN 1  -- Todos completos
                                    ELSE 0  -- Qualquer incompleto
                                END
                            FROM checklist_items
                            WHERE parent_id = ?
                        ),
                        updated_at = ?
                        WHERE id = ?
                    """
                    cursor.execute(update_parent_query, (ancestor_id, datetime.now(), ancestor_id))
                    if cursor.rowcount > 0:
                        items_updated_upstream += 1
            
            # Calcular progresso global (se houver implantacao_id)
            progress = 0.0
            if implantacao_id:
                if db_type == 'postgres':
                    progress_query = """
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN completed = true THEN 1 END) as completos
                        FROM checklist_items
                        WHERE implantacao_id = %s
                    """
                    cursor.execute(progress_query, (implantacao_id,))
                    result = cursor.fetchone()
                else:
                    progress_query = """
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN completed = 1 THEN 1 END) as completos
                        FROM checklist_items
                        WHERE implantacao_id = ?
                    """
                    cursor.execute(progress_query, (implantacao_id,))
                    row = cursor.fetchone()
                    result = dict(zip([desc[0] for desc in cursor.description], row))
                
                if result:
                    total = result.get('total', 0) or 0
                    completos = result.get('completos', 0) or 0
                    if total > 0:
                        progress = round((completos / total) * 100, 2)
            
            total_items_updated = items_updated_downstream + items_updated_upstream
            
            logger.info(
                f"Toggle item {item_id}: status={new_status}, "
                f"downstream={items_updated_downstream}, upstream={items_updated_upstream}, "
                f"progress={progress}%, user={usuario_email}"
            )
            
            return {
                'ok': True,
                'items_updated': total_items_updated,
                'progress': progress,
                'downstream_updated': items_updated_downstream,
                'upstream_updated': items_updated_upstream
            }
            
        except Exception as e:
            logger.error(f"Erro ao fazer toggle do item {item_id}: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao alterar status do item: {e}")


def update_item_comment(item_id, comment_text, usuario_email=None):
    """
    Atualiza o comentário de um item específico.
    
    Args:
        item_id: ID do item
        comment_text: Texto do comentário (será sanitizado)
        usuario_email: Email do usuário (para logging)
    
    Returns:
        dict: {'ok': bool, 'item_id': int}
    """
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        raise ValueError(f"item_id deve ser um inteiro válido")
    
    # Sanitizar comentário
    try:
        comment_sanitized = sanitize_string(comment_text, max_length=8000, min_length=0, allow_empty=True)
    except ValidationError as e:
        raise ValueError(f"Comentário inválido: {e}")
    
    usuario_email = usuario_email or (g.user_email if hasattr(g, 'user_email') else None)
    
    with db_transaction_with_lock() as (conn, cursor, db_type):
        try:
            # Verificar se item existe
            if db_type == 'postgres':
                check_query = "SELECT id FROM checklist_items WHERE id = %s FOR UPDATE"
                cursor.execute(check_query, (item_id,))
            else:
                check_query = "SELECT id FROM checklist_items WHERE id = ?"
                cursor.execute(check_query, (item_id,))
            
            item = cursor.fetchone()
            if not item:
                raise ValueError(f"Item {item_id} não encontrado")
            
            # Atualizar comentário
            if db_type == 'postgres':
                update_query = """
                    UPDATE checklist_items 
                    SET comment = %s, updated_at = %s
                    WHERE id = %s
                """
                cursor.execute(update_query, (comment_sanitized, datetime.now(), item_id))
            else:
                update_query = """
                    UPDATE checklist_items 
                    SET comment = ?, updated_at = ?
                    WHERE id = ?
                """
                cursor.execute(update_query, (comment_sanitized, datetime.now(), item_id))
            
            logger.info(f"Comentário atualizado para item {item_id} por {usuario_email}")
            
            return {'ok': True, 'item_id': item_id}
            
        except Exception as e:
            logger.error(f"Erro ao atualizar comentário do item {item_id}: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao atualizar comentário: {e}")


def get_item_progress_stats(item_id, db_type=None, cursor=None):
    """
    Calcula estatísticas de progresso para um item (total de filhos e quantos estão completos).
    
    Args:
        item_id: ID do item
        db_type: 'postgres' ou 'sqlite' (se None, detecta automaticamente quando não há cursor)
        cursor: Cursor do banco (se None, faz query separada usando query_db)
    
    Returns:
        dict: {'total': int, 'completed': int, 'has_children': bool}
    """
    # Se não há cursor, detectar tipo de banco automaticamente
    if cursor is None and db_type is None:
        use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False) if current_app else False
        db_type = 'sqlite' if use_sqlite else 'postgres'
    
    if db_type == 'postgres':
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
                return {
                    'total': result[0] or 0,
                    'completed': result[1] or 0,
                    'has_children': (result[0] or 0) > 0
                }
        else:
            result = query_db(stats_query, (item_id,), one=True)
            if result:
                return {
                    'total': result.get('total', 0) or 0,
                    'completed': result.get('completed', 0) or 0,
                    'has_children': (result.get('total', 0) or 0) > 0
                }
    else:
        # SQLite
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
                return {
                    'total': row[0] or 0,
                    'completed': row[1] or 0,
                    'has_children': (row[0] or 0) > 0
                }
        else:
            result = query_db(stats_query, (item_id,), one=True)
            if result:
                # Para SQLite, query_db pode retornar dict ou tupla dependendo do driver
                if isinstance(result, dict):
                    return {
                        'total': result.get('total', 0) or 0,
                        'completed': result.get('completed', 0) or 0,
                        'has_children': (result.get('total', 0) or 0) > 0
                    }
                else:
                    # Tupla (SQLite row)
                    return {
                        'total': result[0] or 0,
                        'completed': result[1] or 0,
                        'has_children': (result[0] or 0) > 0
                    }
    
    return {'total': 0, 'completed': 0, 'has_children': False}


def get_checklist_tree(implantacao_id=None, root_item_id=None, include_progress=True):
    """
    Retorna a árvore completa do checklist.
    
    Pode ser filtrada por implantacao_id ou retornar a partir de um root_item_id.
    
    Args:
        implantacao_id: ID da implantação (opcional)
        root_item_id: ID do item raiz (opcional, se None retorna todos)
        include_progress: Se True, inclui estatísticas de progresso (X/Y) para cada item
    
    Returns:
        list: Lista plana de itens com metadados para montar árvore no frontend
              ou dict aninhado (pode configurar)
    """
    try:
        if implantacao_id:
            implantacao_id = int(implantacao_id)
        if root_item_id:
            root_item_id = int(root_item_id)
    except (ValueError, TypeError):
        raise ValueError("IDs devem ser inteiros válidos")
    
    with db_transaction_with_lock() as (conn, cursor, db_type):
        try:
            if db_type == 'postgres':
                if implantacao_id:
                    query = """
                        SELECT 
                            id, parent_id, title, completed, comment,
                            level, ordem, implantacao_id,
                            created_at, updated_at
                        FROM checklist_items
                        WHERE implantacao_id = %s
                        ORDER BY ordem ASC, id ASC
                    """
                    cursor.execute(query, (implantacao_id,))
                elif root_item_id:
                    # CTE recursiva para pegar sub-árvore a partir do root
                    query = """
                        WITH RECURSIVE subtree AS (
                            SELECT id, parent_id, title, completed, comment,
                                   level, ordem, implantacao_id,
                                   created_at, updated_at
                            FROM checklist_items
                            WHERE id = %s
                            
                            UNION ALL
                            
                            SELECT ci.id, ci.parent_id, ci.title, ci.completed, ci.comment,
                                   ci.level, ci.ordem, ci.implantacao_id,
                                   ci.created_at, ci.updated_at
                            FROM checklist_items ci
                            INNER JOIN subtree st ON ci.parent_id = st.id
                        )
                        SELECT * FROM subtree
                        ORDER BY ordem ASC, id ASC
                    """
                    cursor.execute(query, (root_item_id,))
                else:
                    query = """
                        SELECT 
                            id, parent_id, title, completed, comment,
                            level, ordem, implantacao_id,
                            created_at, updated_at
                        FROM checklist_items
                        ORDER BY ordem ASC, id ASC
                    """
                    cursor.execute(query)
                
                items = cursor.fetchall()
                # Converter para lista de dicionários
                result = []
                for item in items:
                    item_dict = {
                        'id': item['id'],
                        'parent_id': item['parent_id'],
                        'title': item['title'],
                        'completed': item['completed'],
                        'comment': item['comment'],
                        'level': item['level'],
                        'ordem': item['ordem'],
                        'implantacao_id': item['implantacao_id'],
                        'created_at': self._format_datetime(item.get('created_at')),
                        'updated_at': self._format_datetime(item.get('updated_at')),
                    }
                    
                    # Adicionar estatísticas de progresso (X/Y) se solicitado
                    if include_progress:
                        stats = get_item_progress_stats(item['id'], db_type, cursor)
                        item_dict['progress'] = {
                            'total': stats['total'],
                            'completed': stats['completed'],
                            'has_children': stats['has_children']
                        }
                        # Formato amigável para UI: "X/Y"
                        item_dict['progress_label'] = f"{stats['completed']}/{stats['total']}" if stats['has_children'] else None
                    
                    result.append(item_dict)
            else:
                # SQLite
                if implantacao_id:
                    query = """
                        SELECT 
                            id, parent_id, title, completed, comment,
                            level, ordem, implantacao_id,
                            created_at, updated_at
                        FROM checklist_items
                        WHERE implantacao_id = ?
                        ORDER BY ordem ASC, id ASC
                    """
                    cursor.execute(query, (implantacao_id,))
                elif root_item_id:
                    query = """
                        WITH RECURSIVE subtree(id, parent_id, title, completed, comment,
                                               level, ordem, implantacao_id, created_at, updated_at) AS (
                            SELECT id, parent_id, title, completed, comment,
                                   level, ordem, implantacao_id, created_at, updated_at
                            FROM checklist_items
                            WHERE id = ?
                            
                            UNION ALL
                            
                            SELECT ci.id, ci.parent_id, ci.title, ci.completed, ci.comment,
                                   ci.level, ci.ordem, ci.implantacao_id, ci.created_at, ci.updated_at
                            FROM checklist_items ci
                            INNER JOIN subtree st ON ci.parent_id = st.id
                        )
                        SELECT * FROM subtree
                        ORDER BY ordem ASC, id ASC
                    """
                    cursor.execute(query, (root_item_id,))
                else:
                    query = """
                        SELECT 
                            id, parent_id, title, completed, comment,
                            level, ordem, implantacao_id,
                            created_at, updated_at
                        FROM checklist_items
                        ORDER BY ordem ASC, id ASC
                    """
                    cursor.execute(query)
                
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    item_dict = {
                        'id': row[0],
                        'parent_id': row[1],
                        'title': row[2],
                        'completed': bool(row[3]) if row[3] is not None else False,
                        'comment': row[4],
                        'level': row[5],
                        'ordem': row[6],
                        'implantacao_id': row[7],
                        'created_at': _format_datetime(row[8]),
                        'updated_at': _format_datetime(row[9]),
                    }
                    
                    # Adicionar estatísticas de progresso (X/Y) se solicitado
                    if include_progress:
                        stats = get_item_progress_stats(row[0], db_type, cursor)
                        item_dict['progress'] = {
                            'total': stats['total'],
                            'completed': stats['completed'],
                            'has_children': stats['has_children']
                        }
                        # Formato amigável para UI: "X/Y"
                        item_dict['progress_label'] = f"{stats['completed']}/{stats['total']}" if stats['has_children'] else None
                    
                    result.append(item_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao buscar árvore do checklist: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao buscar checklist: {e}")


def build_nested_tree(flat_items):
    """
    Converte lista plana em árvore aninhada (JSON).
    
    Args:
        flat_items: Lista plana de itens com parent_id
    
    Returns:
        list: Lista de itens raiz, cada um com 'children' aninhado
    """
    # Criar mapa de items por id
    items_map = {item['id']: {**item, 'children': []} for item in flat_items}
    root_items = []
    
    # Construir árvore
    for item in flat_items:
        item_id = item['id']
        parent_id = item['parent_id']
        
        if parent_id is None:
            root_items.append(items_map[item_id])
        else:
            if parent_id in items_map:
                items_map[parent_id]['children'].append(items_map[item_id])
    
    # Ordenar recursivamente por ordem
    def sort_children(item):
        item['children'].sort(key=lambda x: (x.get('ordem', 0), x.get('id', 0)))
        for child in item['children']:
            sort_children(child)
    
    for root in root_items:
        sort_children(root)
    
    root_items.sort(key=lambda x: (x.get('ordem', 0), x.get('id', 0)))
    
    return root_items

