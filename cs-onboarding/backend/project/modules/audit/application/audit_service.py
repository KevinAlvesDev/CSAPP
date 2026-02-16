"""
Serviço de Auditoria (Audit Log)
Responsável por registrar logs detalhados de ações no sistema.
"""

import json
from typing import Any

from flask import current_app, has_request_context, request

from ....db import db_connection


def _ensure_audit_logs_table(cursor, db_type: str) -> None:
    if db_type == "postgres":
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_email TEXT,
                action VARCHAR(100) NOT NULL,
                target_type VARCHAR(100) NOT NULL,
                target_id VARCHAR(255),
                changes JSONB,
                metadata JSONB,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT,
                changes TEXT,
                metadata TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def log_action(
    action: str,
    target_type: str,
    target_id: str,
    changes: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    user_email: str | None = None,
) -> bool:
    """
    Registra uma ação no log de auditoria.

    Args:
        action: Nome da ação (ex: 'UPDATE', 'CREATE', 'LOGIN')
        target_type: Tipo do objeto afetado (ex: 'implantacao', 'usuario')
        target_id: ID do objeto afetado
        changes: Dicionário com as mudanças {before: ..., after: ...}
        metadata: Dados extras sobre a ação
        user_email: Email do usuário (opcional, tenta pegar do request context se não informado)
    """
    try:
        # Tentar pegar dados do contexto da requisição se não fornecidos
        ip_address = None
        user_agent = None

        if has_request_context():
            ip_address = request.remote_addr
            user_agent = request.user_agent.string if request.user_agent else None

            # Se user_email não foi passado, tentar pegar de g.user_email
            if not user_email:
                from flask import g

                user_email = getattr(g, "user_email", None)

        # Serializar JSONs
        changes_json = json.dumps(changes, default=str) if changes else None
        metadata_json = json.dumps(metadata, default=str) if metadata else None

        # Inserir no banco
        with db_connection() as (conn, db_type):
            cursor = conn.cursor()

            try:
                if db_type == "postgres":
                    cursor.execute(
                        """
                        INSERT INTO audit_logs
                        (user_email, action, target_type, target_id, changes, metadata, ip_address, user_agent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            user_email,
                            action,
                            target_type,
                            str(target_id),
                            changes_json,
                            metadata_json,
                            ip_address,
                            user_agent,
                        ),
                    )
                else:  # SQLite
                    cursor.execute(
                        """
                        INSERT INTO audit_logs
                        (user_email, action, target_type, target_id, changes, metadata, ip_address, user_agent)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            user_email,
                            action,
                            target_type,
                            str(target_id),
                            changes_json,
                            metadata_json,
                            ip_address,
                            user_agent,
                        ),
                    )
            except Exception as insert_err:
                # Fallback para bancos legados sem migration aplicada
                msg = str(insert_err).lower()
                missing_table = "no such table" in msg or "does not exist" in msg
                if not missing_table:
                    raise
                _ensure_audit_logs_table(cursor, db_type)
                if db_type == "postgres":
                    cursor.execute(
                        """
                        INSERT INTO audit_logs
                        (user_email, action, target_type, target_id, changes, metadata, ip_address, user_agent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            user_email,
                            action,
                            target_type,
                            str(target_id),
                            changes_json,
                            metadata_json,
                            ip_address,
                            user_agent,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO audit_logs
                        (user_email, action, target_type, target_id, changes, metadata, ip_address, user_agent)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            user_email,
                            action,
                            target_type,
                            str(target_id),
                            changes_json,
                            metadata_json,
                            ip_address,
                            user_agent,
                        ),
                    )

            conn.commit()

        return True

    except Exception as e:
        # Falha no log de auditoria não deve quebrar a aplicação, mas deve ser logada no sistema de logs
        if current_app:
            current_app.logger.error(f"Falha ao registrar log de auditoria: {e}", exc_info=True)
        return False


def get_diff(old_obj: dict, new_obj: dict, ignore_keys: list | None = None) -> dict:
    """
    Gera um diff entre dois dicionários (antes e depois).
    Útil para gerar o payload de 'changes'.
    """
    if ignore_keys is None:
        ignore_keys = ["updated_at", "last_activity"]

    changes = {"before": {}, "after": {}}
    has_changes = False

    all_keys = set(old_obj.keys()) | set(new_obj.keys())

    for key in all_keys:
        if key in ignore_keys:
            continue

        val_old = old_obj.get(key)
        val_new = new_obj.get(key)

        if val_old != val_new:
            changes["before"][key] = val_old
            changes["after"][key] = val_new
            has_changes = True

    return changes if has_changes else None
