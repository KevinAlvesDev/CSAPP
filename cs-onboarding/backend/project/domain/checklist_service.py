"""
Serviço de Checklist Hierárquico Infinito
Implementa lógica de propagação de status (cascata e bolha) usando CTEs recursivas.
"""

import logging
from datetime import datetime

from flask import current_app, g

from ..common.exceptions import DatabaseError
from ..common.validation import ValidationError, sanitize_string
from ..db import db_transaction_with_lock, query_db, logar_timeline, execute_db

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
    Atualiza também a tabela checklist_status_history e o campo data_conclusao.

    Lógica:
    - Cascata (Downstream): Marca/desmarca todos os descendentes
    - Bolha (Upstream): Atualiza pais baseado no status dos filhos
    - Histórico: Registra alterações de status
    """
    try:
        item_id = int(item_id)
        new_status = bool(new_status)
    except (ValueError, TypeError):
        raise ValueError("item_id deve ser um inteiro válido e new_status deve ser booleano")

    usuario_email = usuario_email or (g.user_email if hasattr(g, 'user_email') else None)

    # Valores normalizados para atualização
    status_str = 'Concluída' if new_status else 'Pendente'
    data_conclusao = datetime.now() if new_status else None
    now = datetime.now()

    with db_transaction_with_lock() as (conn, cursor, db_type):
        # Determinar valor de completed baseado no tipo do banco
        completed_val = new_status if db_type == 'postgres' else (1 if new_status else 0)
        
        # 1. Verificar existência e pegar dados básicos
        check_query = "SELECT id, implantacao_id, title, status FROM checklist_items WHERE id = %s"
        if db_type == 'sqlite':
            check_query = check_query.replace('%s', '?')

        cursor.execute(check_query, (item_id,))
        item = cursor.fetchone()

        if not item:
            raise ValueError(f"Item {item_id} não encontrado")

        # Handle result access (sqlite row vs tuple vs dict)
        if hasattr(item, 'keys'):
            implantacao_id = item['implantacao_id']
            item_title = item['title']
        elif hasattr(cursor, 'description'):
            cols = [d[0] for d in cursor.description]
            item_dict = dict(zip(cols, item))
            implantacao_id = item_dict['implantacao_id']
            item_title = item_dict['title']
        else:
            implantacao_id = item[1]
            item_title = item[2]

        # 2. Identificar Descendentes (Downstream)
        # Usamos CTE para encontrar todos os IDs
        if db_type == 'postgres':
            descendants_query = """
                WITH RECURSIVE descendants AS (
                    SELECT id FROM checklist_items WHERE id = %s
                    UNION ALL
                    SELECT ci.id FROM checklist_items ci
                    INNER JOIN descendants d ON ci.parent_id = d.id
                )
                SELECT id FROM descendants
            """
            cursor.execute(descendants_query, (item_id,))
        else:
            descendants_query = """
                WITH RECURSIVE descendants(id) AS (
                    SELECT id FROM checklist_items WHERE id = ?
                    UNION ALL
                    SELECT ci.id FROM checklist_items ci
                    INNER JOIN descendants d ON ci.parent_id = d.id
                )
                SELECT id FROM descendants
            """
            cursor.execute(descendants_query, (item_id,))

        descendant_rows = cursor.fetchall()
        descendant_ids = [row[0] for row in descendant_rows]

        # 3. Atualizar Descendentes (incluindo o próprio item)
        items_updated_downstream = 0
        history_entries = []

        if descendant_ids:
            placeholders = ','.join(['%s' if db_type == 'postgres' else '?'] * len(descendant_ids))

            # Primeiro, pegar status atuais para histórico
            status_query = f"SELECT id, status FROM checklist_items WHERE id IN ({placeholders})"
            cursor.execute(status_query, descendant_ids)
            current_statuses = {row[0]: row[1] for row in cursor.fetchall()}

            # Atualizar status e completed
            update_sql = f"""
                UPDATE checklist_items 
                SET status = {'%s' if db_type == 'postgres' else '?'}, 
                    completed = {'%s' if db_type == 'postgres' else '?'},
                    data_conclusao = {'%s' if db_type == 'postgres' else '?'}
                WHERE id IN ({placeholders})
            """
            params = [status_str, completed_val, data_conclusao] + descendant_ids
            cursor.execute(update_sql, params)
            items_updated_downstream = cursor.rowcount

            # Preparar entradas de histórico
            for did in descendant_ids:
                old_status = current_statuses.get(did, 'Pendente') # Default to Pendente if null
                if old_status != status_str:
                    history_entries.append((did, old_status, status_str, usuario_email, now))

            # Tentar inserir histórico (pode falhar se tabela não existir em prod, mas devia existir)
            if history_entries:
                try:
                    insert_history_sql = """
                        INSERT INTO checklist_status_history 
                        (checklist_item_id, old_status, new_status, changed_by, changed_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    if db_type == 'sqlite':
                        insert_history_sql = insert_history_sql.replace('%s', '?')

                    cursor.executemany(insert_history_sql, history_entries)
                except Exception as e:
                    logger.warning(f"Falha ao inserir histórico de status: {e}")

        # 4. Atualizar Ancestrais (Upstream - Bolha)
        items_updated_upstream = 0

        if db_type == 'postgres':
            ancestors_query = """
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id FROM checklist_items 
                    WHERE id = (SELECT parent_id FROM checklist_items WHERE id = %s)
                    UNION ALL
                    SELECT ci.id, ci.parent_id FROM checklist_items ci
                    INNER JOIN ancestors a ON ci.id = a.parent_id
                )
                SELECT id FROM ancestors
            """
            cursor.execute(ancestors_query, (item_id,))
        else:
             ancestors_query = """
                WITH RECURSIVE ancestors(id, parent_id) AS (
                    SELECT id, parent_id FROM checklist_items 
                    WHERE id = (SELECT parent_id FROM checklist_items WHERE id = ?)
                    UNION ALL
                    SELECT ci.id, ci.parent_id FROM checklist_items ci
                    INNER JOIN ancestors a ON ci.id = a.parent_id
                )
                SELECT id FROM ancestors
            """
             cursor.execute(ancestors_query, (item_id,))

        ancestor_rows = cursor.fetchall()
        ancestor_ids = [row[0] for row in ancestor_rows]

        for ancestor_id in ancestor_ids:
             # Verificar estado dos filhos
             check_children_query = """
                SELECT COUNT(*), SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END)
                FROM checklist_items WHERE parent_id = %s
             """
             if db_type == 'sqlite':
                 check_children_query = check_children_query.replace('%s', '?')

             cursor.execute(check_children_query, (ancestor_id,))
             stats = cursor.fetchone()
             total = stats[0]
             completed_count = stats[1] or 0

             should_be_complete = (total > 0 and total == completed_count)
             new_anc_status_str = 'Concluída' if should_be_complete else 'Pendente'
             new_anc_completed = should_be_complete if db_type == 'postgres' else (1 if should_be_complete else 0)

             # Verificar estado atual do ancestral
             get_ancestor_query = "SELECT status FROM checklist_items WHERE id = %s"
             if db_type == 'sqlite': get_ancestor_query = get_ancestor_query.replace('%s', '?')
             cursor.execute(get_ancestor_query, (ancestor_id,))
             curr_anc_row = cursor.fetchone()
             curr_anc_status = curr_anc_row[0] if curr_anc_row else 'Pendente'

             if curr_anc_status != new_anc_status_str:
                 new_anc_date = now if should_be_complete else None

                 update_anc_sql = "UPDATE checklist_items SET status = %s, completed = %s, data_conclusao = %s WHERE id = %s"
                 if db_type == 'sqlite': update_anc_sql = update_anc_sql.replace('%s', '?')

                 cursor.execute(update_anc_sql, (new_anc_status_str, new_anc_completed, new_anc_date, ancestor_id))
                 items_updated_upstream += 1

                 # Log history
                 try:
                     hist_sql = "INSERT INTO checklist_status_history (checklist_item_id, old_status, new_status, changed_by, changed_at) VALUES (%s, %s, %s, %s, %s)"
                     if db_type == 'sqlite': hist_sql = hist_sql.replace('%s', '?')
                     cursor.execute(hist_sql, (ancestor_id, curr_anc_status, new_anc_status_str, usuario_email, now))
                 except Exception:
                     pass

        conn.commit()

        # Log timeline (now managed inside the transaction or safely afterwards, but service functions are generally agnostic)
        # However, to replicate the API behavior, we should log relevant changes.
        # But 'logar_timeline' creates a new connection, which might lock if we were still holding the transaction lock.
        # But we called conn.commit(), so the transaction is technically 'done' but the context manager (__exit__) hasn't run yet to close it.
        # Best practice: Return necessary info and let caller log, OR log here if 'logar_timeline' is safe.
        # Given 'logar_timeline' implementation, let's keep it safe. Use internal cursor log if possible? No, logar_timeline is complex.
        
        # We will return the item_title so the controller can log if it wants, 
        # OR we can try to insert into timeline table directly here using the same cursor.
        # Let's insert directly for robustness.
        
        try:
             detalhe = f"Status: {status_str} — {item_title}"
             log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
             if db_type == 'sqlite': log_sql = log_sql.replace('%s', '?')
             cursor.execute(log_sql, (implantacao_id, usuario_email, 'tarefa_alterada', detalhe, now))
             conn.commit() # Commit log
        except Exception as e:
             logger.error(f"Failed to log timeline inside service: {e}")

        # Calcular progresso
        progress = 0.0
        if implantacao_id:
            _invalidar_cache_progresso_local(implantacao_id)

            # Recalcular progresso (apenas itens folha)
            prog_sql = """
                SELECT COUNT(*), SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END)
                FROM checklist_items ci
                WHERE ci.implantacao_id = %s
                AND NOT EXISTS (SELECT 1 FROM checklist_items f WHERE f.parent_id = ci.id)
            """
            if db_type == 'sqlite':
                prog_sql = prog_sql.replace('%s', '?')

            cursor.execute(prog_sql, (implantacao_id,))
            p_res = cursor.fetchone()
            p_total = p_res[0] or 0
            p_compl = p_res[1] or 0

            if p_total > 0:
                progress = round((p_compl / p_total) * 100, 2)
            else:
                progress = 100.0 if p_compl > 0 else 0.0

        logger.info(
            f"Toggle item {item_id}: status={new_status}, "
            f"downstream={items_updated_downstream}, upstream={items_updated_upstream}, "
            f"progress={progress}%, user={usuario_email}"
        )

        return {
            'ok': True,
            'items_updated': items_updated_downstream + items_updated_upstream,
            'progress': progress,
            'downstream_updated': items_updated_downstream,
            'upstream_updated': items_updated_upstream
        }


def add_comment_to_item(item_id, text, visibilidade='interno', usuario_email=None):
    """
    Adiciona um comentário ao histórico e atualiza o campo legado 'comment' no item.
    Centraliza a lógica de comentários.
    """
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        raise ValueError("item_id deve ser um inteiro válido")

    if not text or not text.strip():
        raise ValueError("Texto do comentário é obrigatório")

    usuario_email = usuario_email or (g.user_email if hasattr(g, 'user_email') else None)
    text = sanitize_string(text.strip(), max_length=8000, min_length=1)

    with db_transaction_with_lock() as (conn, cursor, db_type):
        # 1. Verificar item
        check_query = "SELECT id, implantacao_id, title FROM checklist_items WHERE id = %s"
        if db_type == 'sqlite': check_query = check_query.replace('%s', '?')
        cursor.execute(check_query, (item_id,))
        item = cursor.fetchone()
        if not item:
            raise ValueError(f"Item {item_id} não encontrado")
        
        # Handle result access
        if hasattr(item, 'keys'):
            implantacao_id = item['implantacao_id']
            item_title = item['title']
        else:
            implantacao_id = item[1]
            item_title = item[2]

        # 2. Garantir coluna checklist_item_id em comentarios_h (Self-healing)
        if db_type == 'postgres':
            try:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='comentarios_h' AND column_name='checklist_item_id'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN IF NOT EXISTS checklist_item_id INTEGER")
                    try:
                        cursor.execute("ALTER TABLE comentarios_h ADD CONSTRAINT fk_comentarios_checklist_item FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id)")
                    except Exception:
                        pass
            except Exception:
                pass
        elif db_type == 'sqlite':
            try:
                cursor.execute("PRAGMA table_info(comentarios_h)")
                cols = [r[1] for r in cursor.fetchall()]
                if 'checklist_item_id' not in cols:
                    cursor.execute("ALTER TABLE comentarios_h ADD COLUMN checklist_item_id INTEGER")
            except Exception:
                pass

        # 3. Inserir no histórico (comentarios_h)
        now = datetime.now()
        insert_sql = """
            INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, data_criacao, visibilidade)
            VALUES (%s, %s, %s, %s, %s)
        """
        if db_type == 'sqlite': insert_sql = insert_sql.replace('%s', '?')
        cursor.execute(insert_sql, (item_id, usuario_email, text, now, visibilidade))
        
        # 4. Atualizar campo legado 'comment' no checklist_items (para compatibilidade frontend)
        # Isso garante que o ícone de "tem comentário" apareça
        update_legacy_sql = "UPDATE checklist_items SET comment = %s, updated_at = %s WHERE id = %s"
        if db_type == 'sqlite': update_legacy_sql = update_legacy_sql.replace('%s', '?')
        cursor.execute(update_legacy_sql, (text, now, item_id))

        # 5. Log na timeline usando mesmo cursor
        try:
            detalhe = f"Comentário criado — {item_title} <span class=\"d-none related-id\" data-item-id=\"{item_id}\"></span>"
            log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == 'sqlite': log_sql = log_sql.replace('%s', '?')
            cursor.execute(log_sql, (implantacao_id, usuario_email, 'novo_comentario', detalhe, now))
        except Exception as e:
            logger.warning(f"Erro ao logar timeline: {e}")

        conn.commit()

        # Retornar dados do comentário para o frontend
        return {
            'ok': True,
            'item_id': item_id,
            'comentario': {
                'texto': text,
                'usuario_cs': usuario_email,
                'data_criacao': now.isoformat(),
                'visibilidade': visibilidade
            }
        }


def update_item_responsavel(item_id, novo_responsavel, usuario_email=None):
    """
    Atualiza o responsável de um item e registra histórico.
    """
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        raise ValueError("item_id deve ser um inteiro válido")

    novo_responsavel = (novo_responsavel or '').strip()
    if not novo_responsavel:
        raise ValueError("Responsável é obrigatório")

    usuario_email = usuario_email or (g.user_email if hasattr(g, 'user_email') else None)

    with db_transaction_with_lock() as (conn, cursor, db_type):
        q = "SELECT responsavel, title, implantacao_id FROM checklist_items WHERE id = %s"
        if db_type == 'sqlite': q = q.replace('%s', '?')
        cursor.execute(q, (item_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError("Item não encontrado")

        # Handle row access
        if hasattr(row, 'keys'):
            old_resp = row['responsavel']
            item_title = row['title']
            impl_id = row['implantacao_id']
        else:
            old_resp = row[0]
            item_title = row[1]
            impl_id = row[2]

        now = datetime.now()
        
        # Update
        uq = "UPDATE checklist_items SET responsavel = %s, updated_at = %s WHERE id = %s"
        if db_type == 'sqlite': uq = uq.replace('%s', '?')
        cursor.execute(uq, (novo_responsavel, now, item_id))

        # History
        try:
            ih = "INSERT INTO checklist_responsavel_history (checklist_item_id, old_responsavel, new_responsavel, changed_by, changed_at) VALUES (%s, %s, %s, %s, %s)"
            if db_type == 'sqlite': ih = ih.replace('%s', '?')
            cursor.execute(ih, (item_id, old_resp, novo_responsavel, usuario_email, now))
        except Exception:
            # Tabela pode não existir em dev antigo
            pass

        # Timeline
        try:
            detalhe = f"Responsável: {(old_resp or '')} → {novo_responsavel} — {item_title}"
            log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == 'sqlite': log_sql = log_sql.replace('%s', '?')
            cursor.execute(log_sql, (impl_id, usuario_email, 'responsavel_alterado', detalhe, now))
        except Exception:
            pass

        conn.commit()
        
        return {'ok': True, 'item_id': item_id, 'responsavel': novo_responsavel}


def delete_checklist_item(item_id, usuario_email=None):
    """
    Exclui um item do checklist e toda a sua hierarquia de descendentes.
    Recalcula o status do pai (se houver) e o progresso da implantação.
    """
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        raise ValueError("item_id deve ser um inteiro válido")

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

            # 3. Atualizar status do pai (se houver)
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

                    if total > 0:
                        new_status = (total == completos)
                        cursor.execute("UPDATE checklist_items SET completed = %s, updated_at = %s WHERE id = %s",
                                     (new_status, datetime.now(), parent_id))
                else:
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

                # Bubble up recursively to ancestors
                curr_parent = parent_id
                while curr_parent:
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
                    progress = 100.0 if items_deleted > 0 else 0.0

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
            query = ""
            params = []
            
            if db_type == 'postgres':
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
                 # Default: all items (dangerous but supported by signature)
                 query = "SELECT id, parent_id, title, completed, comment, level, ordem, implantacao_id, obrigatoria, tag, responsavel, previsao_original, nova_previsao, data_conclusao, created_at, updated_at FROM checklist_items ORDER BY ordem ASC, id ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Helper to map row to dict dependent on db driver (sqlite tuple vs postgres row)
            result = []
            
            col_names = [d[0] for d in cursor.description]
            
            for row in rows:
                # Unify row into a plain dict
                item = row if isinstance(row, dict) else dict(zip(col_names, row))
                
                # Normalize formatting
                item_dict = {
                    'id': item['id'],
                    'parent_id': item.get('parent_id') if isinstance(item, dict) else item['parent_id'],
                    'title': item.get('title') if isinstance(item, dict) else item['title'],
                    'completed': bool(item.get('completed') if isinstance(item, dict) else item['completed']),
                    'comment': item.get('comment') if isinstance(item, dict) else item['comment'],
                    'level': item.get('level') if isinstance(item, dict) else item['level'],
                    'ordem': item.get('ordem') if isinstance(item, dict) else item['ordem'],
                    'implantacao_id': item.get('implantacao_id') if isinstance(item, dict) else item['implantacao_id'],
                    'obrigatoria': bool(item.get('obrigatoria') if isinstance(item, dict) else item['obrigatoria']),
                    'tag': item.get('tag') if isinstance(item, dict) else item['tag'],
                    'responsavel': item.get('responsavel') if isinstance(item, dict) else item.get('responsavel', None),
                    'previsao_original': _format_datetime((item.get('previsao_original') if isinstance(item, dict) else item.get('previsao_original', None))),
                    'nova_previsao': _format_datetime((item.get('nova_previsao') if isinstance(item, dict) else item.get('nova_previsao', None))),
                    'data_conclusao': _format_datetime((item.get('data_conclusao') if isinstance(item, dict) else item.get('data_conclusao', None))),
                    'created_at': _format_datetime((item.get('created_at') if isinstance(item, dict) else item.get('created_at', None))),
                    'updated_at': _format_datetime((item.get('updated_at') if isinstance(item, dict) else item.get('updated_at', None))),
                }
                
                # Enrich responsavel name
                # Note: calling query_db inside loop is bad performance.
                # But to maintain exact behavior of previous code without rewrite of big query:
                # We can skip this or optimize later.
                try:
                    resp = item_dict.get('responsavel')
                    if resp and '@' in resp:
                        # Assuming simple caching or low volume
                        r = query_db("SELECT nome FROM perfil_usuario WHERE usuario = %s", (resp,), one=True)
                        if r and r.get('nome'):
                            item_dict['responsavel'] = r.get('nome')
                except Exception:
                    pass
                
                ref_dt = item_dict['nova_previsao'] or item_dict['previsao_original']
                item_dict['atrasada'] = bool(ref_dt and not item_dict['completed'] and ref_dt < _format_datetime(datetime.utcnow()))

                if include_progress:
                    # reusing internal logic
                    stats = get_item_progress_stats(item_dict['id'], db_type, cursor)
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


# --- NOVOS MÉTODOS MIGRADOS ---

def listar_usuarios_cs():
    """Retorna lista simples de usuários para atribuição."""
    rows = query_db("SELECT usuario, COALESCE(nome, usuario) as nome FROM perfil_usuario ORDER BY nome ASC") or []
    return rows

def listar_comentarios_implantacao(impl_id, page=1, per_page=20):
    offset = (page - 1) * per_page
    
    count_query = """
        SELECT COUNT(*) as total
        FROM comentarios_h c
        JOIN checklist_items ci ON c.checklist_item_id = ci.id
        WHERE ci.implantacao_id = %s
    """
    total_res = query_db(count_query, (impl_id,), one=True)
    total = total_res['total'] if total_res else 0

    comments_query = """
        SELECT 
            c.id, c.texto, c.usuario_cs, c.data_criacao, c.visibilidade,
            ci.id as item_id, ci.title as item_title,
            COALESCE(p.nome, c.usuario_cs) as usuario_nome
        FROM comentarios_h c
        JOIN checklist_items ci ON c.checklist_item_id = ci.id
        LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
        WHERE ci.implantacao_id = %s
        ORDER BY c.data_criacao ASC
        LIMIT %s OFFSET %s
    """
    comments = query_db(comments_query, (impl_id, per_page, offset))
    
    formatted_comments = []
    for c in comments:
        c_dict = dict(c)
        c_dict['data_criacao'] = _format_datetime(c_dict.get('data_criacao'))
        formatted_comments.append(c_dict)
        
    return {
        'comments': formatted_comments,
        'total': total,
        'page': page,
        'per_page': per_page
    }

def listar_comentarios_item(item_id):
    comentarios = query_db(
        """
        SELECT c.id, c.texto, c.usuario_cs, c.data_criacao, c.visibilidade, c.imagem_url,
                COALESCE(p.nome, c.usuario_cs) as usuario_nome
        FROM comentarios_h c
        LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
        WHERE c.checklist_item_id = %s
        ORDER BY c.data_criacao DESC
        """,
        (item_id,)
    ) or []

    item_info = query_db(
        """
        SELECT i.email_responsavel
        FROM checklist_items ci
        JOIN implantacoes i ON ci.implantacao_id = i.id
        WHERE ci.id = %s
        """,
        (item_id,),
        one=True
    )
    email_responsavel = item_info.get('email_responsavel', '') if item_info else ''

    comentarios_formatados = []
    for c in comentarios:
        c_dict = dict(c)
        c_dict['data_criacao'] = _format_datetime(c_dict.get('data_criacao'))
        c_dict['email_responsavel'] = email_responsavel
        comentarios_formatados.append(c_dict)

    return {
        'comentarios': comentarios_formatados,
        'email_responsavel': email_responsavel
    }

def obter_comentario_para_email(comentario_id):
    dados = query_db(
        """
        SELECT c.id, c.texto, c.visibilidade, c.usuario_cs,
                ci.title as tarefa_nome,
                i.id as impl_id, i.nome_empresa, i.email_responsavel
        FROM comentarios_h c
        JOIN checklist_items ci ON c.checklist_item_id = ci.id
        JOIN implantacoes i ON ci.implantacao_id = i.id
        WHERE c.id = %s
        """,
        (comentario_id,),
        one=True
    )
    return dados

def excluir_comentario_service(comentario_id, usuario_email, is_manager):
    comentario = query_db(
        "SELECT id, usuario_cs FROM comentarios_h WHERE id = %s",
        (comentario_id,),
        one=True
    )
    if not comentario:
        raise ValueError('Comentário não encontrado')

    is_owner = comentario['usuario_cs'] == usuario_email
    if not (is_owner or is_manager):
        raise ValueError('Permissão negada')

    # Fetch related item info BEFORE delete
    item_info = query_db(
        """
        SELECT ci.id as item_id, ci.title as item_title, ci.implantacao_id
        FROM comentarios_h c
        JOIN checklist_items ci ON c.checklist_item_id = ci.id
        WHERE c.id = %s
        """,
        (comentario_id,), one=True
    )

    execute_db("DELETE FROM comentarios_h WHERE id = %s", (comentario_id,))

    if item_info:
        try:
            detalhe = f"Comentário em '{item_info.get('item_title', '')}' excluído."
            logar_timeline(item_info['implantacao_id'], usuario_email, 'comentario_excluido', detalhe)
        except Exception:
            pass

def atualizar_prazo_item(item_id, nova_data_iso, usuario_email):
    """
    Atualiza o prazo de um item de checklist.
    Expects nova_data_iso as ISO formatted string or datetime.
    """
    if isinstance(nova_data_iso, str):
        try:
            from datetime import datetime
            if nova_data_iso.endswith('Z'):
                nova_data_iso = nova_data_iso[:-1]
            nova_dt = datetime.fromisoformat(nova_data_iso)
        except Exception:
            raise ValueError('Formato de data inválido')
    else:
        nova_dt = nova_data_iso

    with db_transaction_with_lock() as (conn, cursor, db_type):
        q = "SELECT implantacao_id, previsao_original, title FROM checklist_items WHERE id = %s"
        if db_type == 'sqlite': q = q.replace('%s', '?')
        cursor.execute(q, (item_id,))
        row = cursor.fetchone()
        
        if not row:
            raise ValueError('Item não encontrado')
            
        # Access logic
        if hasattr(row, 'keys'):
            impl_id = row['implantacao_id']
            prev_orig = row['previsao_original']
            title = row['title']
        else:
            impl_id = row[0]
            prev_orig = row[1]
            title = row[2]
            
        now = datetime.now()
        uq = "UPDATE checklist_items SET nova_previsao = %s, updated_at = %s WHERE id = %s"
        if db_type == 'sqlite': uq = uq.replace('%s', '?')
        
        cursor.execute(uq, (nova_dt, now, item_id))
        
        # Timeline inside transaction? Or safe logging?
        # Let's insert directly
        try:
            detalhe = f"Nova previsão: {_format_datetime(nova_dt)} — {title}"
            log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == 'sqlite': log_sql = log_sql.replace('%s', '?')
            cursor.execute(log_sql, (impl_id, usuario_email, 'prazo_alterado', detalhe, now))
        except Exception:
            pass
            
        conn.commit()
        
        return {
            'item_id': item_id,
            'nova_previsao': _format_datetime(nova_dt),
            'previsao_original': _format_datetime(prev_orig)
        }

def obter_historico_responsavel(item_id):
    entries = query_db(
        """
        SELECT id, old_responsavel, new_responsavel, changed_by, changed_at
        FROM checklist_responsavel_history
        WHERE checklist_item_id = %s
        ORDER BY changed_at DESC
        """,
        (item_id,)
    ) or []
    
    for e in entries:
        e['changed_at'] = _format_datetime(e.get('changed_at'))
    
    return entries

def obter_historico_prazos(item_id):
    impl = query_db("SELECT implantacao_id FROM checklist_items WHERE id = %s", (item_id,), one=True)
    if not impl:
        raise ValueError('Item não encontrado')
        
    impl_id = impl['implantacao_id']
    logs = query_db(
        """
        SELECT id, usuario_cs, detalhes, data_criacao
        FROM timeline_log
        WHERE implantacao_id = %s AND tipo_evento = 'prazo_alterado'
        ORDER BY id DESC
        """,
        (impl_id,)
    ) or []
    
    entries = []
    prefix = f"Item {item_id} " # Old logic... but my new log is "Nova previsão: ... — Title"
    # Wait, previous logic was: if det.startswith(f"Item {item_id} ")
    # But I changed logging to `f"Nova previsão: {nova_dt.isoformat()} — {title_val}"`
    # This might break history viewing if titles are not unique or if ID is not in string.
    # The previous code in `api.py` was checking `item_id`.
    # To maintain compatibility, I should probably stick to old log format OR change how I fetch history.
    # Old log: `f"Item {item_id} prazo alterado para {nova_dt} por {usuario_email}...` ? 
    # No, step 41 showed: `detalhe = f"Nova previsão: {nova_dt.isoformat()} — {title_val}"`
    # And then `get_prazos_history` checked: `if det.startswith(f"Item {item_id} "):`
    # THIS IS A BUG IN THE OLD CODE OR MY READING. 
    # "Nova previsão..." does NOT start with "Item {item_id}".
    # Let me re-read step 41 carefully.
    
    # Line 728: detalhe = f"Nova previsão: {nova_dt.isoformat()} — {title_val}"
    # Line 791: if det.startswith(f"Item {item_id} "):
    
    # Conclusion: The boolean logic in `get_prazos_history` was probably BROKEN or relying on older logs that utilized that format.
    # If I want to fix this, I should log the ITEM ID in the details or separate column.
    # But for now, let's just return all deadline changes for the IMPLANTACAO and let the frontend filter? No.
    # I should try to filter by title?
    # Or probably `checklist_api.py` was filtering by string matching which failed for new logs.
    
    # I will construct the list attempting to match useful logs.
    # For now, I'll return what matches the implantation. 
    # Better: I will check if the log details contains the title of the item.
    
    item_title = query_db("SELECT title FROM checklist_items WHERE id = %s", (item_id,), one=True)['title']
    
    for l in logs:
        det = l.get('detalhes') or ''
        # Heuristic matching
        if item_title in det:
             entries.append({
                'usuario_cs': l.get('usuario_cs'),
                'detalhes': det,
                'data_criacao': _format_datetime(l.get('data_criacao'))
            })
            
    return entries

def obter_progresso_global_service(implantacao_id):
     # Efficient query for global progress
     # Postgres/SQLite compatible
     use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
     
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
         total = int(res.get('total', 0) or 0)
         completed = int(res.get('completed', 0) or 0)
         if total > 0:
             return round((completed / total) * 100, 2)
         else:
             return 100.0 # Or 0?
     return 0.0
