"""
Módulo de Operações em Itens do Checklist
Toggle status, delete, responsável e prazo.
Princípio SOLID: Single Responsibility
"""

import logging
from datetime import datetime

from flask import g

from ...common.exceptions import DatabaseError
from ...db import db_transaction_with_lock
from .utils import _format_datetime, _invalidar_cache_progresso_local

logger = logging.getLogger(__name__)


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
        raise ValueError("item_id deve ser um inteiro válido e new_status deve ser booleano") from None

    usuario_email = usuario_email or (g.user_email if hasattr(g, "user_email") else None)

    # Valores normalizados para atualização
    status_str = "Concluída" if new_status else "Pendente"
    data_conclusao = datetime.now() if new_status else None
    now = datetime.now()

    with db_transaction_with_lock() as (conn, cursor, db_type):
        # Determinar valor de completed baseado no tipo do banco
        completed_val = new_status if db_type == "postgres" else (1 if new_status else 0)

        # 1. Verificar existência e pegar dados básicos
        check_query = "SELECT id, implantacao_id, title, status FROM checklist_items WHERE id = %s"
        if db_type == "sqlite":
            check_query = check_query.replace("%s", "?")

        cursor.execute(check_query, (item_id,))
        item = cursor.fetchone()

        if not item:
            raise ValueError(f"Item {item_id} não encontrado")

        # Handle result access (sqlite row vs tuple vs dict)
        if hasattr(item, "keys"):
            implantacao_id = item["implantacao_id"]
            item_title = item["title"]
        elif hasattr(cursor, "description"):
            cols = [d[0] for d in cursor.description]
            item_dict = dict(zip(cols, item, strict=False))
            implantacao_id = item_dict["implantacao_id"]
            item_title = item_dict["title"]
        else:
            implantacao_id = item[1]
            item_title = item[2]

        # 2. Identificar Descendentes (Downstream)
        if db_type == "postgres":
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
            placeholders = ",".join(["%s" if db_type == "postgres" else "?"] * len(descendant_ids))

            # Primeiro, pegar status atuais para histórico
            status_query = f"SELECT id, status FROM checklist_items WHERE id IN ({placeholders})"
            cursor.execute(status_query, descendant_ids)
            current_statuses = {row[0]: row[1] for row in cursor.fetchall()}

            # Atualizar status e completed
            update_sql = f"""
                UPDATE checklist_items
                SET status = {"%s" if db_type == "postgres" else "?"},
                    completed = {"%s" if db_type == "postgres" else "?"},
                    data_conclusao = {"%s" if db_type == "postgres" else "?"}
                WHERE id IN ({placeholders})
            """
            params = [status_str, completed_val, data_conclusao, *descendant_ids]
            cursor.execute(update_sql, params)
            items_updated_downstream = cursor.rowcount

            # Preparar entradas de histórico
            for did in descendant_ids:
                old_status = current_statuses.get(did, "Pendente")
                if old_status != status_str:
                    history_entries.append((did, old_status, status_str, usuario_email, now))

            # Tentar inserir histórico
            if history_entries:
                try:
                    if db_type == "postgres":
                        cursor.execute("SAVEPOINT history_insert")

                    insert_history_sql = """
                        INSERT INTO checklist_status_history
                        (checklist_item_id, old_status, new_status, changed_by, changed_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    if db_type == "sqlite":
                        insert_history_sql = insert_history_sql.replace("%s", "?")

                    cursor.executemany(insert_history_sql, history_entries)
                except Exception as e:
                    logger.warning(f"Falha ao inserir histórico de status: {e}")
                    if db_type == "postgres":
                        cursor.execute("ROLLBACK TO SAVEPOINT history_insert")

        # 4. Atualizar Ancestrais (Upstream - Bolha)
        items_updated_upstream = 0

        if db_type == "postgres":
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
            if db_type == "sqlite":
                check_children_query = check_children_query.replace("%s", "?")

            cursor.execute(check_children_query, (ancestor_id,))
            stats = cursor.fetchone()
            total = stats[0]
            completed_count = stats[1] or 0

            should_be_complete = total > 0 and total == completed_count
            new_anc_status_str = "Concluída" if should_be_complete else "Pendente"
            new_anc_completed = should_be_complete if db_type == "postgres" else (1 if should_be_complete else 0)

            # Verificar estado atual do ancestral
            get_ancestor_query = "SELECT status FROM checklist_items WHERE id = %s"
            if db_type == "sqlite":
                get_ancestor_query = get_ancestor_query.replace("%s", "?")
            cursor.execute(get_ancestor_query, (ancestor_id,))
            curr_anc_row = cursor.fetchone()
            curr_anc_status = curr_anc_row[0] if curr_anc_row else "Pendente"

            if curr_anc_status != new_anc_status_str:
                new_anc_date = now if should_be_complete else None

                update_anc_sql = (
                    "UPDATE checklist_items SET status = %s, completed = %s, data_conclusao = %s WHERE id = %s"
                )
                if db_type == "sqlite":
                    update_anc_sql = update_anc_sql.replace("%s", "?")

                cursor.execute(update_anc_sql, (new_anc_status_str, new_anc_completed, new_anc_date, ancestor_id))
                items_updated_upstream += 1

                # Log history
                try:
                    hist_sql = "INSERT INTO checklist_status_history (checklist_item_id, old_status, new_status, changed_by, changed_at) VALUES (%s, %s, %s, %s, %s)"
                    if db_type == "sqlite":
                        hist_sql = hist_sql.replace("%s", "?")
                    cursor.execute(hist_sql, (ancestor_id, curr_anc_status, new_anc_status_str, usuario_email, now))
                except Exception:
                    pass

        conn.commit()

        try:
            detalhe = f"Status: {status_str} — {item_title}"
            log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == "sqlite":
                log_sql = log_sql.replace("%s", "?")
            cursor.execute(log_sql, (implantacao_id, usuario_email, "tarefa_alterada", detalhe, now))
            conn.commit()
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
            if db_type == "sqlite":
                prog_sql = prog_sql.replace("%s", "?")

            cursor.execute(prog_sql, (implantacao_id,))
            p_res = cursor.fetchone()
            p_total = p_res[0] or 0
            p_compl = p_res[1] or 0

            progress = round(p_compl / p_total * 100, 2) if p_total > 0 else 0.0

        logger.info(
            f"Toggle item {item_id}: status={new_status}, "
            f"downstream={items_updated_downstream}, upstream={items_updated_upstream}, "
            f"progress={progress}%, user={usuario_email}"
        )

        # Emitir evento quando item é concluído
        if new_status:
            try:
                from ...core.events import ChecklistItemConcluido, event_bus

                event_bus.emit(ChecklistItemConcluido(
                    item_id=item_id,
                    implantacao_id=implantacao_id,
                    usuario=usuario_email or "",
                    progresso_atual=progress,
                ))
            except Exception:
                pass

        return {
            "ok": True,
            "items_updated": items_updated_downstream + items_updated_upstream,
            "progress": progress,
            "downstream_updated": items_updated_downstream,
            "upstream_updated": items_updated_upstream,
        }


def update_item_responsavel(item_id, novo_responsavel, usuario_email=None):
    """
    Atualiza o responsável de um item e registra histórico.
    """
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        raise ValueError("item_id deve ser um inteiro válido") from None

    novo_responsavel = (novo_responsavel or "").strip()
    if not novo_responsavel:
        raise ValueError("Responsável é obrigatório")

    usuario_email = usuario_email or (g.user_email if hasattr(g, "user_email") else None)

    with db_transaction_with_lock() as (conn, cursor, db_type):
        q = "SELECT responsavel, title, implantacao_id FROM checklist_items WHERE id = %s"
        if db_type == "sqlite":
            q = q.replace("%s", "?")
        cursor.execute(q, (item_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError("Item não encontrado")

        # Handle row access
        if hasattr(row, "keys"):
            old_resp = row["responsavel"]
            item_title = row["title"]
            impl_id = row["implantacao_id"]
        else:
            old_resp = row[0]
            item_title = row[1]
            impl_id = row[2]

        now = datetime.now()

        # Update
        uq = "UPDATE checklist_items SET responsavel = %s, updated_at = %s WHERE id = %s"
        if db_type == "sqlite":
            uq = uq.replace("%s", "?")
        cursor.execute(uq, (novo_responsavel, now, item_id))

        # History
        try:
            ih = "INSERT INTO checklist_responsavel_history (checklist_item_id, old_responsavel, new_responsavel, changed_by, changed_at) VALUES (%s, %s, %s, %s, %s)"
            if db_type == "sqlite":
                ih = ih.replace("%s", "?")
            cursor.execute(ih, (item_id, old_resp, novo_responsavel, usuario_email, now))
        except Exception:
            pass

        # Timeline
        try:
            detalhe = f"Responsável: {(old_resp or '')} → {novo_responsavel} — {item_title}"
            log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == "sqlite":
                log_sql = log_sql.replace("%s", "?")
            cursor.execute(log_sql, (impl_id, usuario_email, "responsavel_alterado", detalhe, now))
        except Exception:
            pass

        conn.commit()

        return {"ok": True, "item_id": item_id, "responsavel": novo_responsavel}


def delete_checklist_item(item_id, usuario_email=None, is_manager=False):
    """
    Exclui um item do checklist e toda a sua hierarquia de descendentes.
    Recalcula o status do pai (se houver) e o progresso da implantação.
    """
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        raise ValueError("item_id deve ser um inteiro válido") from None

    usuario_email = usuario_email or (g.user_email if hasattr(g, "user_email") else None)

    with db_transaction_with_lock() as (_conn, cursor, db_type):
        try:
            # 1. Buscar informações do item antes de excluir
            if db_type == "postgres":
                query_info = "SELECT id, parent_id, implantacao_id, title FROM checklist_items WHERE id = %s FOR UPDATE"
                cursor.execute(query_info, (item_id,))
            else:
                query_info = "SELECT id, parent_id, implantacao_id, title FROM checklist_items WHERE id = ?"
                cursor.execute(query_info, (item_id,))

            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Item {item_id} não encontrado")

            if db_type == "sqlite":
                item = dict(zip([desc[0] for desc in cursor.description], row, strict=False))
            else:
                item = {"id": row[0], "parent_id": row[1], "implantacao_id": row[2], "title": row[3]}

            parent_id = item["parent_id"]
            implantacao_id = item["implantacao_id"]
            item_title = item["title"]

            # 2. VERIFICAÇÃO DE PERMISSÃO
            if not is_manager:
                owner_query = "SELECT usuario_cs FROM implantacoes WHERE id = %s"
                if db_type == "sqlite":
                    owner_query = owner_query.replace("%s", "?")
                cursor.execute(owner_query, (implantacao_id,))
                owner_row = cursor.fetchone()

                if owner_row:
                    owner_email = owner_row[0] if not hasattr(owner_row, "keys") else owner_row.get("usuario_cs")
                    if owner_email != usuario_email:
                        raise ValueError(
                            "Permissão negada. Apenas o responsável pela implantação ou gestores podem excluir itens."
                        )
                else:
                    raise ValueError("Implantação não encontrada")

            # 3. Identificar todos os descendentes para exclusão
            if db_type == "postgres":
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
                    # Validar que todos os IDs são inteiros (segurança contra SQL injection)
                    try:
                        ids_to_delete = [int(id_val) for id_val in ids_to_delete]
                    except (ValueError, TypeError) as e:
                        raise ValueError(f"IDs inválidos detectados: {e}") from e

                    # Construir query com placeholders validados
                    placeholders = ",".join(["?"] * len(ids_to_delete))
                    cursor.execute(f"DELETE FROM checklist_items WHERE id IN ({placeholders})", ids_to_delete)
                    items_deleted = cursor.rowcount
                else:
                    items_deleted = 0

            # 4. Atualizar status do pai (se houver)
            if parent_id:
                if db_type == "postgres":
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
                        new_status = total == completos
                        cursor.execute(
                            "UPDATE checklist_items SET completed = %s, updated_at = %s WHERE id = %s",
                            (new_status, datetime.now(), parent_id),
                        )
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
                        new_status = total == completos
                        cursor.execute(
                            "UPDATE checklist_items SET completed = ?, updated_at = ? WHERE id = ?",
                            (new_status, datetime.now(), parent_id),
                        )

                # Bubble up recursively to ancestors
                curr_parent = parent_id
                while curr_parent:
                    if db_type == "postgres":
                        cursor.execute(
                            """
                            SELECT parent_id,
                                   (SELECT COUNT(*) FROM checklist_items WHERE parent_id = ci.id) as total,
                                   (SELECT COUNT(*) FROM checklist_items WHERE parent_id = ci.id AND completed = true) as compl
                            FROM checklist_items ci WHERE id = %s
                        """,
                            (curr_parent,),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT parent_id,
                                   (SELECT COUNT(*) FROM checklist_items WHERE parent_id = ci.id) as total,
                                   (SELECT COUNT(*) FROM checklist_items WHERE parent_id = ci.id AND completed = 1) as compl
                            FROM checklist_items ci WHERE id = ?
                        """,
                            (curr_parent,),
                        )

                    p_row = cursor.fetchone()
                    if not p_row:
                        break

                    next_parent = p_row[0]
                    total_f = p_row[1]
                    compl_f = p_row[2]

                    if total_f > 0:
                        new_st = total_f == compl_f
                        if db_type == "postgres":
                            cursor.execute(
                                "UPDATE checklist_items SET completed = %s, updated_at = %s WHERE id = %s",
                                (new_st, datetime.now(), curr_parent),
                            )
                        else:
                            cursor.execute(
                                "UPDATE checklist_items SET completed = ?, updated_at = ? WHERE id = ?",
                                (new_st, datetime.now(), curr_parent),
                            )

                    curr_parent = next_parent

            # 5. Recalcular progresso global
            progress = 0.0
            if implantacao_id:
                if db_type == "postgres":
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

                progress = round(completos / total * 100, 2) if total > 0 else 0.0

                _invalidar_cache_progresso_local(implantacao_id)

            logger.info(
                f"Item {item_id} ('{item_title}') excluído por {usuario_email}. Items removidos: {items_deleted}. Novo progresso: {progress}%"
            )

            return {"ok": True, "progress": progress, "items_deleted": items_deleted}

        except Exception as e:
            logger.error(f"Erro ao excluir item {item_id}: {e}", exc_info=True)
            raise DatabaseError(f"Erro ao excluir item: {e}") from e


def atualizar_prazo_item(item_id, nova_data_iso, usuario_email):
    """
    Atualiza o prazo de um item de checklist.
    """
    if isinstance(nova_data_iso, str):
        try:
            if nova_data_iso.endswith("Z"):
                nova_data_iso = nova_data_iso[:-1]
            nova_dt = datetime.fromisoformat(nova_data_iso)
        except Exception:
            raise ValueError("Formato de data inválido") from None
    else:
        nova_dt = nova_data_iso

    with db_transaction_with_lock() as (conn, cursor, db_type):
        q = "SELECT implantacao_id, previsao_original, title FROM checklist_items WHERE id = %s"
        if db_type == "sqlite":
            q = q.replace("%s", "?")
        cursor.execute(q, (item_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError("Item não encontrado")

        # Access logic
        if hasattr(row, "keys"):
            impl_id = row["implantacao_id"]
            prev_orig = row["previsao_original"]
            title = row["title"]
        else:
            impl_id = row[0]
            prev_orig = row[1]
            title = row[2]

        now = datetime.now()
        uq = "UPDATE checklist_items SET nova_previsao = %s, updated_at = %s WHERE id = %s"
        if db_type == "sqlite":
            uq = uq.replace("%s", "?")

        cursor.execute(uq, (nova_dt, now, item_id))

        try:
            detalhe = f"Nova previsão: {_format_datetime(nova_dt)} — {title}"
            log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == "sqlite":
                log_sql = log_sql.replace("%s", "?")
            cursor.execute(log_sql, (impl_id, usuario_email, "prazo_alterado", detalhe, now))
        except Exception:
            pass

        conn.commit()

        return {
            "item_id": item_id,
            "nova_previsao": _format_datetime(nova_dt, only_date=True),
            "previsao_original": _format_datetime(prev_orig, only_date=True),
        }


def move_item(item_id, new_parent_id=None, new_order=None, usuario_email=None):
    """
    Move um item do checklist para uma nova posição.
    Pode alterar o parent_id e/ou a ordem do item.

    Args:
        item_id: ID do item a mover
        new_parent_id: Novo ID do pai (None para mover para raiz, -1 para manter atual)
        new_order: Nova ordem/posição (0-based index entre irmãos)
        usuario_email: Email do usuário que está movendo

    Returns:
        dict com resultado da operação
    """
    try:
        item_id = int(item_id)
    except (ValueError, TypeError):
        raise ValueError("item_id deve ser um inteiro válido") from None

    if new_parent_id is not None and new_parent_id != -1:
        try:
            new_parent_id = int(new_parent_id)
        except (ValueError, TypeError):
            raise ValueError("new_parent_id deve ser um inteiro válido") from None

    if new_order is not None:
        try:
            new_order = int(new_order)
            if new_order < 0:
                new_order = 0
        except (ValueError, TypeError):
            raise ValueError("new_order deve ser um inteiro válido") from None

    usuario_email = usuario_email or (g.user_email if hasattr(g, "user_email") else None)

    with db_transaction_with_lock() as (conn, cursor, db_type):
        # 1. Verificar existência do item
        check_query = "SELECT id, implantacao_id, parent_id, ordem, title FROM checklist_items WHERE id = %s"
        if db_type == "sqlite":
            check_query = check_query.replace("%s", "?")

        cursor.execute(check_query, (item_id,))
        item = cursor.fetchone()

        if not item:
            raise ValueError(f"Item {item_id} não encontrado")

        # Handle row access
        if hasattr(item, "keys"):
            implantacao_id = item["implantacao_id"]
            current_parent_id = item["parent_id"]
            current_order = item["ordem"] or 0
            item_title = item["title"]
        else:
            implantacao_id = item[1]
            current_parent_id = item[2]
            current_order = item[3] or 0
            item_title = item[4]

        # Determinar novo parent_id (-1 significa manter atual)
        if new_parent_id == -1:
            new_parent_id = current_parent_id
        elif new_parent_id == 0:
            new_parent_id = None  # Mover para raiz

        # 2. Verificar se não está tentando mover para dentro de si mesmo
        if new_parent_id is not None:
            # Verificar se o novo pai existe
            check_parent_query = "SELECT id FROM checklist_items WHERE id = %s"
            if db_type == "sqlite":
                check_parent_query = check_parent_query.replace("%s", "?")
            cursor.execute(check_parent_query, (new_parent_id,))
            if not cursor.fetchone():
                raise ValueError(f"Pai {new_parent_id} não encontrado")

            # Verificar se o novo pai não é descendente do item
            if db_type == "postgres":
                descendants_query = """
                    WITH RECURSIVE descendants AS (
                        SELECT id FROM checklist_items WHERE id = %s
                        UNION ALL
                        SELECT ci.id FROM checklist_items ci
                        INNER JOIN descendants d ON ci.parent_id = d.id
                    )
                    SELECT id FROM descendants WHERE id = %s
                """
                cursor.execute(descendants_query, (item_id, new_parent_id))
            else:
                descendants_query = """
                    WITH RECURSIVE descendants(id) AS (
                        SELECT id FROM checklist_items WHERE id = ?
                        UNION ALL
                        SELECT ci.id FROM checklist_items ci
                        INNER JOIN descendants d ON ci.parent_id = d.id
                    )
                    SELECT id FROM descendants WHERE id = ?
                """
                cursor.execute(descendants_query, (item_id, new_parent_id))

            if cursor.fetchone():
                raise ValueError("Não é possível mover um item para dentro de si mesmo ou de seus descendentes")

        # 3. Calcular nova ordem se não especificada
        if new_order is None:
            # Manter ordem atual se mudando apenas parent
            if new_parent_id != current_parent_id:
                # Buscar última ordem no novo grupo de irmãos
                order_query = "SELECT MAX(ordem) FROM checklist_items WHERE implantacao_id = %s AND "
                if new_parent_id is None:
                    order_query += "parent_id IS NULL"
                    order_params = (implantacao_id,)
                else:
                    order_query += "parent_id = %s"
                    order_params = (implantacao_id, new_parent_id)

                if db_type == "sqlite":
                    order_query = order_query.replace("%s", "?")

                cursor.execute(order_query, order_params)
                max_order = cursor.fetchone()[0]
                new_order = (max_order or 0) + 1
            else:
                new_order = current_order

        # 4. Reordenar irmãos no grupo destino
        # Primeiro, remover espaço no grupo atual
        if current_parent_id is not None:
            shift_down_query = """
                UPDATE checklist_items
                SET ordem = ordem - 1
                WHERE implantacao_id = %s AND parent_id = %s AND ordem > %s
            """
        else:
            shift_down_query = """
                UPDATE checklist_items
                SET ordem = ordem - 1
                WHERE implantacao_id = %s AND parent_id IS NULL AND ordem > %s
            """

        if db_type == "sqlite":
            shift_down_query = shift_down_query.replace("%s", "?")

        if current_parent_id is not None:
            cursor.execute(shift_down_query, (implantacao_id, current_parent_id, current_order))
        else:
            cursor.execute(shift_down_query, (implantacao_id, current_order))

        # Abrir espaço no grupo destino
        if new_parent_id is not None:
            shift_up_query = """
                UPDATE checklist_items
                SET ordem = ordem + 1
                WHERE implantacao_id = %s AND parent_id = %s AND ordem >= %s AND id != %s
            """
        else:
            shift_up_query = """
                UPDATE checklist_items
                SET ordem = ordem + 1
                WHERE implantacao_id = %s AND parent_id IS NULL AND ordem >= %s AND id != %s
            """

        if db_type == "sqlite":
            shift_up_query = shift_up_query.replace("%s", "?")

        if new_parent_id is not None:
            cursor.execute(shift_up_query, (implantacao_id, new_parent_id, new_order, item_id))
        else:
            cursor.execute(shift_up_query, (implantacao_id, new_order, item_id))

        # 5. Atualizar o item com nova posição
        now = datetime.now()
        if new_parent_id is not None:
            update_query = """
                UPDATE checklist_items
                SET parent_id = %s, ordem = %s, updated_at = %s
                WHERE id = %s
            """
            update_params = (new_parent_id, new_order, now, item_id)
        else:
            update_query = """
                UPDATE checklist_items
                SET parent_id = NULL, ordem = %s, updated_at = %s
                WHERE id = %s
            """
            update_params = (new_order, now, item_id)

        if db_type == "sqlite":
            update_query = update_query.replace("%s", "?")

        cursor.execute(update_query, update_params)

        # 6. Recalcular levels para o item e seus descendentes
        # Calcular novo level
        if new_parent_id is None:
            new_level = 0
        else:
            level_query = "SELECT level FROM checklist_items WHERE id = %s"
            if db_type == "sqlite":
                level_query = level_query.replace("%s", "?")
            cursor.execute(level_query, (new_parent_id,))
            parent_level_row = cursor.fetchone()
            new_level = (parent_level_row[0] or 0) + 1 if parent_level_row else 0

        # Atualizar level do item
        level_update = "UPDATE checklist_items SET level = %s WHERE id = %s"
        if db_type == "sqlite":
            level_update = level_update.replace("%s", "?")
        cursor.execute(level_update, (new_level, item_id))

        # Atualizar levels dos descendentes recursivamente
        if db_type == "postgres":
            update_levels_query = """
                WITH RECURSIVE descendants AS (
                    SELECT id, %s as base_level, 1 as depth FROM checklist_items WHERE parent_id = %s
                    UNION ALL
                    SELECT ci.id, d.base_level, d.depth + 1 FROM checklist_items ci
                    INNER JOIN descendants d ON ci.parent_id = d.id
                )
                UPDATE checklist_items ci
                SET level = d.base_level + d.depth
                FROM descendants d
                WHERE ci.id = d.id
            """
            cursor.execute(update_levels_query, (new_level, item_id))
        else:
            # Para SQLite, fazer iterativamente
            def update_children_levels(parent_id, parent_level):
                find_children = "SELECT id FROM checklist_items WHERE parent_id = ?"
                cursor.execute(find_children, (parent_id,))
                children = cursor.fetchall()
                for child in children:
                    child_id = child[0]
                    child_level = parent_level + 1
                    cursor.execute("UPDATE checklist_items SET level = ? WHERE id = ?", (child_level, child_id))
                    update_children_levels(child_id, child_level)

            update_children_levels(item_id, new_level)

        # 7. Log na timeline
        try:
            parent_info = ""
            if new_parent_id is not None and new_parent_id != current_parent_id:
                parent_title_query = "SELECT title FROM checklist_items WHERE id = %s"
                if db_type == "sqlite":
                    parent_title_query = parent_title_query.replace("%s", "?")
                cursor.execute(parent_title_query, (new_parent_id,))
                parent_row = cursor.fetchone()
                if parent_row:
                    parent_info = f" para dentro de '{parent_row[0]}'"
            elif new_parent_id is None and current_parent_id is not None:
                parent_info = " para o nível raiz"

            detalhe = f"Item movido: '{item_title}'{parent_info}"
            log_sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
            if db_type == "sqlite":
                log_sql = log_sql.replace("%s", "?")
            cursor.execute(log_sql, (implantacao_id, usuario_email, "item_movido", detalhe, now))
        except Exception as e:
            logger.warning(f"Erro ao logar timeline: {e}")

        conn.commit()

        logger.info(
            f"Item {item_id} movido: parent_id={current_parent_id}->{new_parent_id}, ordem={current_order}->{new_order}"
        )

        return {
            "ok": True,
            "item_id": item_id,
            "new_parent_id": new_parent_id,
            "new_order": new_order,
            "old_parent_id": current_parent_id,
            "old_order": current_order,
        }
