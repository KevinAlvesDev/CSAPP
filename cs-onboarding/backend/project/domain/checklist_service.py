"""
Serviço de Checklist Hierárquico Infinito
Implementa lógica de propagação de status (cascata e bolha) usando CTEs recursivas.
"""

from flask import current_app, g
from datetime import datetime
from ..db import query_db, db_transaction_with_lock
from ..common.validation import sanitize_string, ValidationError
from ..common.exceptions import DatabaseError
import logging

logger = logging.getLogger(__name__)


def _invalidar_cache_progresso_local(impl_id):
    """
    Invalida o cache de progresso de uma implantação.
    Versão local para evitar importação circular.
    """
    try:
        from ..config.cache_config import cache
        if cache:
            cache_key = f'progresso_impl_{impl_id}'
            cache.delete(cache_key)
    except Exception as e:
        logger.warning(f"Erro ao invalidar cache de progresso para impl_id {impl_id}: {e}")


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

            if db_type == 'postgres':
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
                cascade_query = """
                    WITH RECURSIVE descendants(id, parent_id, new_status) AS (
                        SELECT id, parent_id, ? as new_status
                        FROM checklist_items
                        WHERE id = ?

                        UNION ALL

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

            if db_type == 'postgres':
                ancestors_query = """
                    WITH RECURSIVE ancestors AS (
                        SELECT id, parent_id
                        FROM checklist_items
                        WHERE id = (SELECT parent_id FROM checklist_items WHERE id = %s)

                        UNION ALL

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
                for ancestor_id in ancestor_ids:
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

                        if total_filhos == 0:
                            continue
                        else:
                            new_parent_status = (filhos_completos == total_filhos)

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
                for ancestor_id in ancestor_ids:
                    update_parent_query = """
                        UPDATE checklist_items
                        SET completed = (
                            SELECT
                                CASE
                                    WHEN COUNT(*) = 0 THEN completed
                                    WHEN COUNT(*) = COUNT(CASE WHEN completed = 1 THEN 1 END) THEN 1
                                    ELSE 0
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

            progress = 0.0
            total = 0
            completos = 0
            if implantacao_id:
                if db_type == 'postgres':
                    progress_query = """
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completos
                        FROM checklist_items ci
                        WHERE ci.implantacao_id = %s
                        AND NOT EXISTS (
                            SELECT 1 FROM checklist_items filho 
                            WHERE filho.parent_id = ci.id
                            AND filho.implantacao_id = %s
                        )
                    """
                    cursor.execute(progress_query, (implantacao_id, implantacao_id))
                    result = cursor.fetchone()
                    if result:
                        total = result[0] or 0
                        completos = result[1] or 0
                else:
                    progress_query = """
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completos
                        FROM checklist_items ci
                        WHERE ci.implantacao_id = ?
                        AND NOT EXISTS (
                            SELECT 1 FROM checklist_items filho 
                            WHERE filho.parent_id = ci.id
                            AND filho.implantacao_id = ?
                        )
                    """
                    cursor.execute(progress_query, (implantacao_id, implantacao_id))
                    row = cursor.fetchone()
                    if row:
                        total = row[0] or 0
                        completos = row[1] or 0

                if total > 0:
                    progress = round((completos / total) * 100, 2)
                else:
                    progress = 100.0

            total_items_updated = items_updated_downstream + items_updated_upstream

            if implantacao_id:
                _invalidar_cache_progresso_local(implantacao_id)

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

    try:
        comment_sanitized = sanitize_string(comment_text, max_length=8000, min_length=0, allow_empty=True)
    except ValidationError as e:
        raise ValueError(f"Comentário inválido: {e}")

    usuario_email = usuario_email or (g.user_email if hasattr(g, 'user_email') else None)

    with db_transaction_with_lock() as (conn, cursor, db_type):
        try:
            if db_type == 'postgres':
                check_query = "SELECT id FROM checklist_items WHERE id = %s FOR UPDATE"
                cursor.execute(check_query, (item_id,))
            else:
                check_query = "SELECT id FROM checklist_items WHERE id = ?"
                cursor.execute(check_query, (item_id,))

            item = cursor.fetchone()
            if not item:
                raise ValueError(f"Item {item_id} não encontrado")

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


def delete_checklist_item(item_id, usuario_email=None):
    """
    Exclui um item do checklist e toda a sua hierarquia de descendentes.
    Recalcula o status do pai (se houver) e o progresso da implantação.

    Args:
        item_id: ID do item a ser excluído
        usuario_email: Email do usuário (para logging)

    Returns:
        dict: {
            'ok': bool,
            'progress': float,  # Novo progresso global
            'items_deleted': int
        }
    """
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        raise ValueError(f"item_id deve ser um inteiro válido")

    usuario_email = usuario_email or (g.user_email if hasattr(g, 'user_email') else None)

    with db_transaction_with_lock() as (conn, cursor, db_type):
        try:
            # 1. Buscar informações do item antes de excluir
            if db_type == 'postgres':
                query_info = "SELECT id, parent_id, implantacao_id, title FROM checklist_items WHERE id = %s FOR UPDATE"
                cursor.execute(query_info, (item_id,))
            else:
                query_info = "SELECT id, parent_id, implantacao_id, title FROM checklist_items WHERE id = ?"
                cursor.execute(query_info, (item_id,))
            
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Item {item_id} não encontrado")
            
            if db_type == 'sqlite':
                item = dict(zip([desc[0] for desc in cursor.description], row))
            else:
                item = {'id': row[0], 'parent_id': row[1], 'implantacao_id': row[2], 'title': row[3]}

            parent_id = item['parent_id']
            implantacao_id = item['implantacao_id']
            item_title = item['title']

            # 2. Identificar todos os descendentes para exclusão (incluindo o próprio item)
            if db_type == 'postgres':
                delete_query = """
                    WITH RECURSIVE descendants AS (
                        SELECT id FROM checklist_items WHERE id = %s
                        UNION ALL
                        SELECT ci.id FROM checklist_items ci
                        INNER JOIN descendants d ON ci.parent_id = d.id
                    )
                    DELETE FROM checklist_items
                    WHERE id IN (SELECT id FROM descendants)
                """
                cursor.execute(delete_query, (item_id,))
                items_deleted = cursor.rowcount
            else:
                # SQLite: Buscar IDs primeiro, depois deletar
                ids_query = """
                    WITH RECURSIVE descendants(id) AS (
                        SELECT id FROM checklist_items WHERE id = ?
                        UNION ALL
                        SELECT ci.id FROM checklist_items ci
                        INNER JOIN descendants d ON ci.parent_id = d.id
                    )
                    SELECT id FROM descendants
                """
                cursor.execute(ids_query, (item_id,))
                ids_to_delete = [r[0] for r in cursor.fetchall()]
                
                if ids_to_delete:
                    placeholders = ','.join(['?'] * len(ids_to_delete))
                    cursor.execute(f"DELETE FROM checklist_items WHERE id IN ({placeholders})", ids_to_delete)
                    items_deleted = cursor.rowcount
                else:
                    items_deleted = 0

            # 3. Atualizar status do pai (se houver), pois a exclusão de um filho pode mudar o status do pai
            # Ex: Pai tinha 2 filhos, 1 completo e 1 pendente. Se apagar o pendente, o pai vira completo.
            if parent_id:
                if db_type == 'postgres':
                    check_parent_query = """
                        SELECT
                            COUNT(*) as total_filhos,
                            COUNT(CASE WHEN completed = true THEN 1 END) as filhos_completos
                        FROM checklist_items
                        WHERE parent_id = %s
                    """
                    cursor.execute(check_parent_query, (parent_id,))
                    res = cursor.fetchone()
                    total = res[0] or 0
                    completos = res[1] or 0
                    
                    # Se não tem mais filhos, o status depende da regra de negócio. 
                    # Geralmente se torna uma folha. Se estava marcado como incompleto, continua?
                    # Aqui vamos assumir: se não tem filhos, mantém o status atual ou vira incompleto?
                    # Melhor manter a lógica do toggle:
                    if total > 0:
                        new_status = (total == completos)
                        cursor.execute("UPDATE checklist_items SET completed = %s, updated_at = %s WHERE id = %s", 
                                     (new_status, datetime.now(), parent_id))
                else:
                    # SQLite logic similar
                    check_parent_query = """
                        SELECT
                            COUNT(*) as total_filhos,
                            COUNT(CASE WHEN completed = 1 THEN 1 END) as filhos_completos
                        FROM checklist_items
                        WHERE parent_id = ?
                    """
                    cursor.execute(check_parent_query, (parent_id,))
                    res = cursor.fetchone()
                    total = res[0] or 0
                    completos = res[1] or 0
                    
                    if total > 0:
                        new_status = (total == completos)
                        cursor.execute("UPDATE checklist_items SET completed = ?, updated_at = ? WHERE id = ?", 
                                     (new_status, datetime.now(), parent_id))

                # Nota: Se quiséssemos propagar para cima recursivamente (avós), precisaríamos chamar a lógica de bubble up aqui.
                # Por simplificação, vamos assumir que o toggle já faz isso bem, mas aqui seria ideal replicar.
                # Vamos fazer um loop simples para subir a árvore atualizando pais
                curr_parent = parent_id
                while curr_parent:
                    # Verificar status deste pai baseado nos filhos
                    if db_type == 'postgres':
                        cursor.execute("""
                            SELECT parent_id, 
                                   (SELECT COUNT(*) FROM checklist_items WHERE parent_id = ci.id) as total,
                                   (SELECT COUNT(*) FROM checklist_items WHERE parent_id = ci.id AND completed = true) as compl
                            FROM checklist_items ci WHERE id = %s
                        """, (curr_parent,))
                    else:
                        cursor.execute("""
                            SELECT parent_id, 
                                   (SELECT COUNT(*) FROM checklist_items WHERE parent_id = ci.id) as total,
                                   (SELECT COUNT(*) FROM checklist_items WHERE parent_id = ci.id AND completed = 1) as compl
                            FROM checklist_items ci WHERE id = ?
                        """, (curr_parent,))
                    
                    p_row = cursor.fetchone()
                    if not p_row:
                        break
                        
                    next_parent = p_row[0]
                    total_f = p_row[1]
                    compl_f = p_row[2]
                    
                    if total_f > 0:
                        new_st = (total_f == compl_f)
                        if db_type == 'postgres':
                            cursor.execute("UPDATE checklist_items SET completed = %s, updated_at = %s WHERE id = %s", 
                                         (new_st, datetime.now(), curr_parent))
                        else:
                            cursor.execute("UPDATE checklist_items SET completed = ?, updated_at = ? WHERE id = ?", 
                                         (new_st, datetime.now(), curr_parent))
                    
                    curr_parent = next_parent

            # 4. Recalcular progresso global
            progress = 0.0
            if implantacao_id:
                if db_type == 'postgres':
                    progress_query = """
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completos
                        FROM checklist_items ci
                        WHERE ci.implantacao_id = %s
                        AND NOT EXISTS (
                            SELECT 1 FROM checklist_items filho 
                            WHERE filho.parent_id = ci.id
                            AND filho.implantacao_id = %s
                        )
                    """
                    cursor.execute(progress_query, (implantacao_id, implantacao_id))
                    result = cursor.fetchone()
                    if result:
                        total = result[0] or 0
                        completos = result[1] or 0
                else:
                    progress_query = """
                        SELECT
                            COUNT(*) as total,
                            SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completos
                        FROM checklist_items ci
                        WHERE ci.implantacao_id = ?
                        AND NOT EXISTS (
                            SELECT 1 FROM checklist_items filho 
                            WHERE filho.parent_id = ci.id
                            AND filho.implantacao_id = ?
                        )
                    """
                    cursor.execute(progress_query, (implantacao_id, implantacao_id))
                    row = cursor.fetchone()
                    if row:
                        total = row[0] or 0
                        completos = row[1] or 0

                if total > 0:
                    progress = round((completos / total) * 100, 2)
                else:
                    progress = 100.0 if items_deleted > 0 else 0.0 # Se apagou tudo, ou se não tem nada...

                _invalidar_cache_progresso_local(implantacao_id)

            logger.info(f"Item {item_id} ('{item_title}') excluído por {usuario_email}. Items removidos: {items_deleted}. Novo progresso: {progress}%")

            return {
                'ok': True,
                'progress': progress,
                'items_deleted': items_deleted
            }

        except Exception as e:
            logger.error(f"Erro ao excluir item {item_id}: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao excluir item: {e}")


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
                if isinstance(result, dict):
                    return {
                        'total': result.get('total', 0) or 0,
                        'completed': result.get('completed', 0) or 0,
                        'has_children': (result.get('total', 0) or 0) > 0
                    }
                else:
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
                            level, ordem, implantacao_id, obrigatoria,
                            created_at, updated_at
                        FROM checklist_items
                        WHERE implantacao_id = %s
                        ORDER BY ordem ASC, id ASC
                    """
                    cursor.execute(query, (implantacao_id,))
                elif root_item_id:
                    query = """
                        WITH RECURSIVE subtree AS (
                            SELECT id, parent_id, title, completed, comment,
                                   level, ordem, implantacao_id, obrigatoria,
                                   created_at, updated_at
                            FROM checklist_items
                            WHERE id = %s

                            UNION ALL

                            SELECT ci.id, ci.parent_id, ci.title, ci.completed, ci.comment,
                                   ci.level, ci.ordem, ci.implantacao_id, ci.obrigatoria,
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
                        'obrigatoria': item.get('obrigatoria', False),
                        'created_at': _format_datetime(item.get('created_at')),
                        'updated_at': _format_datetime(item.get('updated_at')),
                    }

                    if include_progress:
                        stats = get_item_progress_stats(item['id'], db_type, cursor)
                        item_dict['progress'] = {
                            'total': stats['total'],
                            'completed': stats['completed'],
                            'has_children': stats['has_children']
                        }
                        item_dict['progress_label'] = f"{stats['completed']}/{stats['total']}" if stats['has_children'] else None

                    result.append(item_dict)
            else:
                if implantacao_id:
                    query = """
                        SELECT
                            id, parent_id, title, completed, comment,
                            level, ordem, implantacao_id, obrigatoria,
                            created_at, updated_at
                        FROM checklist_items
                        WHERE implantacao_id = ?
                        ORDER BY ordem ASC, id ASC
                    """
                    cursor.execute(query, (implantacao_id,))
                elif root_item_id:
                    query = """
                        WITH RECURSIVE subtree(id, parent_id, title, completed, comment,
                                               level, ordem, implantacao_id, obrigatoria, created_at, updated_at) AS (
                            SELECT id, parent_id, title, completed, comment,
                                   level, ordem, implantacao_id, obrigatoria, created_at, updated_at
                            FROM checklist_items
                            WHERE id = ?

                            UNION ALL

                            SELECT ci.id, ci.parent_id, ci.title, ci.completed, ci.comment,
                                   ci.level, ci.ordem, ci.implantacao_id, ci.obrigatoria, ci.created_at, ci.updated_at
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
                        'obrigatoria': bool(row[8]) if row[8] is not None else False,
                        'created_at': _format_datetime(row[9]),
                        'updated_at': _format_datetime(row[10]),
                    }

                    if include_progress:
                        stats = get_item_progress_stats(row[0], db_type, cursor)
                        item_dict['progress'] = {
                            'total': stats['total'],
                            'completed': stats['completed'],
                            'has_children': stats['has_children']
                        }
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
    items_map = {item['id']: {**item, 'children': []} for item in flat_items}
    root_items = []

    for item in flat_items:
        item_id = item['id']
        parent_id = item['parent_id']

        if parent_id is None:
            root_items.append(items_map[item_id])
        else:
            if parent_id in items_map:
                items_map[parent_id]['children'].append(items_map[item_id])

    def sort_children(item):
        item['children'].sort(key=lambda x: (x.get('ordem', 0), x.get('id', 0)))
        for child in item['children']:
            sort_children(child)

    for root in root_items:
        sort_children(root)

    root_items.sort(key=lambda x: (x.get('ordem', 0), x.get('id', 0)))

    return root_items
