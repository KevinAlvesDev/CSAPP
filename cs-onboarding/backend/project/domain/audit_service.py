"""
Serviço de Auditoria (Audit Log)
Responsável por registrar logs detalhados de ações no sistema.
"""

import json
from typing import Any

from flask import current_app, has_request_context, request

from ..db import db_connection


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
