from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

from ....db import db_connection, query_db

_schema_ready = False
_schema_lock = Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_chat_schema_once() -> None:
    global _schema_ready
    if _schema_ready:
        return

    with _schema_lock:
        if _schema_ready:
            return

        with db_connection() as (conn, db_type):
            if db_type != "postgres":
                _schema_ready = True
                return

            cursor = conn.cursor()
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP")
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP")
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS attachment_url TEXT")
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS attachment_name TEXT")
            cursor.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS attachment_content_type TEXT")
            conn.commit()

        _schema_ready = True


def _resolve_other_participant(conversation_id: int, user_email: str) -> dict[str, Any] | None:
    return query_db(
        """
        SELECT
            p.user_email,
            COALESCE(u.nome, p.user_email) AS nome,
            u.foto_url
        FROM chat_participants p
        LEFT JOIN perfil_usuario u ON u.usuario = p.user_email
        WHERE p.conversation_id = %s AND p.user_email <> %s
        LIMIT 1
        """,
        (conversation_id, user_email),
        one=True,
    )


def list_conversations(user_email: str, context: str) -> list[dict[str, Any]]:
    _ensure_chat_schema_once()

    rows = query_db(
        """
        SELECT
            c.id,
            c.contexto,
            c.updated_at,
            cp.unread_count,
            (
                SELECT CASE
                    WHEN m.deleted_at IS NOT NULL THEN 'Mensagem excluida'
                    WHEN COALESCE(NULLIF(TRIM(m.content), ''), '') <> '' THEN m.content
                    WHEN COALESCE(NULLIF(TRIM(m.attachment_name), ''), '') <> '' THEN CONCAT('📎 ', m.attachment_name)
                    ELSE 'Anexo'
                END
                FROM chat_messages m
                WHERE m.conversation_id = c.id
                ORDER BY m.created_at DESC, m.id DESC
                LIMIT 1
            ) AS last_message,
            (
                SELECT m.created_at
                FROM chat_messages m
                WHERE m.conversation_id = c.id
                ORDER BY m.created_at DESC, m.id DESC
                LIMIT 1
            ) AS last_message_at
        FROM chat_conversations c
        JOIN chat_participants cp
            ON cp.conversation_id = c.id
           AND cp.user_email = %s
        WHERE c.contexto = %s
          AND c.kind = 'direct'
        ORDER BY COALESCE(
            (
                SELECT m.created_at
                FROM chat_messages m
                WHERE m.conversation_id = c.id
                ORDER BY m.created_at DESC, m.id DESC
                LIMIT 1
            ),
            c.updated_at
        ) DESC
        """,
        (user_email, context),
    ) or []

    for row in rows:
        other = _resolve_other_participant(int(row["id"]), user_email)
        row["other_user_email"] = other.get("user_email") if other else None
        row["other_user_name"] = other.get("nome") if other else "Sem participante"
        row["other_user_photo_url"] = other.get("foto_url") if other else None

    return rows


def search_users(query: str, current_user_email: str, limit: int = 10) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    return query_db(
        """
        SELECT
            u.usuario AS email,
            COALESCE(u.nome, u.usuario) AS nome
        FROM perfil_usuario u
        WHERE u.usuario <> %s
          AND (
            LOWER(u.usuario) LIKE LOWER(%s)
            OR LOWER(COALESCE(u.nome, '')) LIKE LOWER(%s)
          )
        ORDER BY LOWER(COALESCE(u.nome, u.usuario))
        LIMIT %s
        """,
        (current_user_email, f"%{query}%", f"%{query}%", limit),
    ) or []


def _ensure_participant(conversation_id: int, user_email: str) -> bool:
    found = query_db(
        """
        SELECT 1
        FROM chat_participants
        WHERE conversation_id = %s AND user_email = %s
        """,
        (conversation_id, user_email),
        one=True,
    )
    return found is not None


def _existing_direct_conversation(user_email: str, other_user_email: str, context: str) -> int | None:
    row = query_db(
        """
        SELECT c.id
        FROM chat_conversations c
        JOIN chat_participants p1
            ON p1.conversation_id = c.id
           AND p1.user_email = %s
        JOIN chat_participants p2
            ON p2.conversation_id = c.id
           AND p2.user_email = %s
        WHERE c.contexto = %s
          AND c.kind = 'direct'
        LIMIT 1
        """,
        (user_email, other_user_email, context),
        one=True,
    )
    return int(row["id"]) if row else None


def create_or_get_direct_conversation(user_email: str, other_user_email: str, context: str) -> int:
    _ensure_chat_schema_once()

    if other_user_email.strip().lower() == user_email.strip().lower():
        raise ValueError("Nao e permitido iniciar conversa consigo mesmo")

    other_exists = query_db(
        "SELECT 1 FROM perfil_usuario WHERE usuario = %s",
        (other_user_email,),
        one=True,
    )
    if not other_exists:
        raise ValueError("Usuario de destino nao encontrado")

    existing_id = _existing_direct_conversation(user_email, other_user_email, context)
    if existing_id is not None:
        return existing_id

    now = _now()
    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"

        cursor.execute(
            f"""
            INSERT INTO chat_conversations (contexto, kind, created_at, updated_at)
            VALUES ({ph}, 'direct', {ph}, {ph})
            """,
            (context, now, now),
        )

        if db_type == "postgres":
            cursor.execute("SELECT lastval()")
            conversation_id = int(cursor.fetchone()[0])
        else:
            conversation_id = int(cursor.lastrowid)

        cursor.execute(
            f"""
            INSERT INTO chat_participants (conversation_id, user_email, unread_count, last_read_at)
            VALUES ({ph}, {ph}, 0, {ph})
            """,
            (conversation_id, user_email, now),
        )
        cursor.execute(
            f"""
            INSERT INTO chat_participants (conversation_id, user_email, unread_count, last_read_at)
            VALUES ({ph}, {ph}, 0, NULL)
            """,
            (conversation_id, other_user_email),
        )

        conn.commit()

    return conversation_id


def list_messages(conversation_id: int, user_email: str, before_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    _ensure_chat_schema_once()

    if not _ensure_participant(conversation_id, user_email):
        raise ValueError("Conversa nao encontrada")

    sql = """
        SELECT
            m.id,
            m.conversation_id,
            m.sender_email,
            COALESCE(u.nome, m.sender_email) AS sender_name,
            u.foto_url AS sender_photo_url,
            CASE
                WHEN m.deleted_at IS NOT NULL THEN 'Mensagem excluida'
                ELSE m.content
            END AS content,
            m.attachment_url,
            m.attachment_name,
            m.attachment_content_type,
            m.created_at,
            m.edited_at,
            m.deleted_at,
            CASE
                WHEN m.sender_email = %s
                     AND r.other_last_read_at IS NOT NULL
                     AND r.other_last_read_at >= m.created_at
                THEN TRUE
                ELSE FALSE
            END AS read_by_recipient
        FROM chat_messages m
        LEFT JOIN perfil_usuario u ON u.usuario = m.sender_email
        LEFT JOIN (
            SELECT p.conversation_id, MAX(p.last_read_at) AS other_last_read_at
            FROM chat_participants p
            WHERE p.user_email <> %s
            GROUP BY p.conversation_id
        ) r ON r.conversation_id = m.conversation_id
        WHERE m.conversation_id = %s
    """
    params: list[Any] = [user_email, user_email, conversation_id]

    if before_id is not None:
        sql += " AND m.id < %s"
        params.append(before_id)

    sql += " ORDER BY m.created_at DESC, m.id DESC LIMIT %s"
    params.append(limit)

    return query_db(sql, tuple(params)) or []


def send_message(conversation_id: int, sender_email: str, content: str, attachment: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_chat_schema_once()

    clean_content = (content or "").strip()
    attachment = attachment or {}
    attachment_url = (attachment.get("attachment_url") or "").strip()
    attachment_name = (attachment.get("attachment_name") or "").strip()
    attachment_content_type = (attachment.get("attachment_content_type") or "").strip()

    has_attachment = bool(attachment_url)
    if not clean_content and not has_attachment:
        raise ValueError("Mensagem vazia")
    if len(clean_content) > 2000:
        raise ValueError("Mensagem excede o limite de 2000 caracteres")

    if not _ensure_participant(conversation_id, sender_email):
        raise ValueError("Conversa nao encontrada")

    now = _now()

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"

        cursor.execute(
            f"""
            INSERT INTO chat_messages (
                conversation_id,
                sender_email,
                content,
                attachment_url,
                attachment_name,
                attachment_content_type,
                created_at
            )
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                conversation_id,
                sender_email,
                clean_content,
                attachment_url or None,
                attachment_name or None,
                attachment_content_type or None,
                now,
            ),
        )

        if db_type == "postgres":
            cursor.execute("SELECT lastval()")
            message_id = int(cursor.fetchone()[0])
        else:
            message_id = int(cursor.lastrowid)

        cursor.execute(
            f"""
            UPDATE chat_conversations
            SET updated_at = {ph}
            WHERE id = {ph}
            """,
            (now, conversation_id),
        )

        cursor.execute(
            f"""
            UPDATE chat_participants
            SET unread_count = unread_count + 1
            WHERE conversation_id = {ph}
              AND user_email <> {ph}
            """,
            (conversation_id, sender_email),
        )

        cursor.execute(
            f"""
            UPDATE chat_participants
            SET unread_count = 0,
                last_read_at = {ph}
            WHERE conversation_id = {ph}
              AND user_email = {ph}
            """,
            (now, conversation_id, sender_email),
        )

        conn.commit()

    return {
        "id": message_id,
        "conversation_id": conversation_id,
        "sender_email": sender_email,
        "content": clean_content,
        "attachment_url": attachment_url or None,
        "attachment_name": attachment_name or None,
        "attachment_content_type": attachment_content_type or None,
        "created_at": now,
    }


def edit_message(message_id: int, sender_email: str, content: str) -> dict[str, Any]:
    _ensure_chat_schema_once()

    clean_content = (content or "").strip()
    if not clean_content:
        raise ValueError("Mensagem vazia")
    if len(clean_content) > 2000:
        raise ValueError("Mensagem excede o limite de 2000 caracteres")

    row = query_db(
        """
        SELECT id, conversation_id, sender_email, deleted_at
        FROM chat_messages
        WHERE id = %s
        """,
        (message_id,),
        one=True,
    )
    if not row:
        raise ValueError("Mensagem nao encontrada")
    if str(row.get("sender_email", "")).lower() != sender_email.lower():
        raise ValueError("Sem permissao para editar esta mensagem")
    if row.get("deleted_at") is not None:
        raise ValueError("Mensagem excluida nao pode ser editada")

    now = _now()
    conversation_id = int(row["conversation_id"])

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"

        cursor.execute(
            f"""
            UPDATE chat_messages
            SET content = {ph},
                edited_at = {ph}
            WHERE id = {ph}
            """,
            (clean_content, now, message_id),
        )

        cursor.execute(
            f"""
            UPDATE chat_conversations
            SET updated_at = {ph}
            WHERE id = {ph}
            """,
            (now, conversation_id),
        )

        conn.commit()

    return {
        "id": message_id,
        "conversation_id": conversation_id,
        "content": clean_content,
        "edited_at": now,
    }


def delete_message(message_id: int, sender_email: str) -> dict[str, Any]:
    _ensure_chat_schema_once()

    row = query_db(
        """
        SELECT id, conversation_id, sender_email, deleted_at
        FROM chat_messages
        WHERE id = %s
        """,
        (message_id,),
        one=True,
    )
    if not row:
        raise ValueError("Mensagem nao encontrada")
    if str(row.get("sender_email", "")).lower() != sender_email.lower():
        raise ValueError("Sem permissao para excluir esta mensagem")
    if row.get("deleted_at") is not None:
        return {
            "id": message_id,
            "conversation_id": int(row["conversation_id"]),
            "deleted_at": row.get("deleted_at"),
        }

    now = _now()
    conversation_id = int(row["conversation_id"])

    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"

        cursor.execute(
            f"""
            UPDATE chat_messages
            SET content = {ph},
                deleted_at = {ph}
            WHERE id = {ph}
            """,
            ("", now, message_id),
        )

        cursor.execute(
            f"""
            UPDATE chat_conversations
            SET updated_at = {ph}
            WHERE id = {ph}
            """,
            (now, conversation_id),
        )

        conn.commit()

    return {
        "id": message_id,
        "conversation_id": conversation_id,
        "deleted_at": now,
    }


def mark_conversation_read(conversation_id: int, user_email: str) -> None:
    _ensure_chat_schema_once()

    if not _ensure_participant(conversation_id, user_email):
        raise ValueError("Conversa nao encontrada")

    now = _now()
    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        ph = "%s" if db_type == "postgres" else "?"

        cursor.execute(
            f"""
            UPDATE chat_participants
            SET unread_count = 0,
                last_read_at = {ph}
            WHERE conversation_id = {ph}
              AND user_email = {ph}
              AND (
                  unread_count <> 0
                  OR last_read_at IS NULL
              )
            """,
            (now, conversation_id, user_email),
        )
        conn.commit()


def get_stream_state(user_email: str) -> dict[str, Any]:
    _ensure_chat_schema_once()

    row = query_db(
        """
        SELECT
            (
                SELECT COALESCE(MAX(m.id), 0)
                FROM chat_messages m
                JOIN chat_participants cp ON cp.conversation_id = m.conversation_id
                WHERE cp.user_email = %s
            ) AS last_message_id,
            (
                SELECT COALESCE(SUM(cp.unread_count), 0)
                FROM chat_participants cp
                WHERE cp.user_email = %s
            ) AS unread_total,
            (
                SELECT MAX(c.updated_at)
                FROM chat_conversations c
                JOIN chat_participants cp ON cp.conversation_id = c.id
                WHERE cp.user_email = %s
            ) AS last_conversation_update,
            (
                SELECT MAX(cp_other.last_read_at)
                FROM chat_participants cp_self
                JOIN chat_participants cp_other
                  ON cp_other.conversation_id = cp_self.conversation_id
                 AND cp_other.user_email <> cp_self.user_email
                WHERE cp_self.user_email = %s
            ) AS last_read_update
        """,
        (user_email, user_email, user_email, user_email),
        one=True,
    ) or {}

    return {
        "last_message_id": int(row.get("last_message_id") or 0),
        "unread_total": int(row.get("unread_total") or 0),
        "last_conversation_update": str(row.get("last_conversation_update") or ""),
        "last_read_update": str(row.get("last_read_update") or ""),
    }
