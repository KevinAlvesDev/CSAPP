"""
Serviço de Auditoria (Audit Log)
Responsável por registrar logs detalhados de ações no sistema.
A tabela `public.audit_logs` já existe no OAMD.
"""

import json
from typing import Any

from flask import current_app, has_request_context, request

from ....db import db_connection

__all__ = [
    "log_action",
    "get_diff",
]


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
        action:      Ação realizada (ex: 'UPDATE', 'CREATE', 'DELETE')
        target_type: Tipo do objeto afetado (ex: 'implantacao', 'usuario') — mapeado para `tabela`
        target_id:   ID do objeto afetado — mapeado para `registro_id`
        changes:     Dicionário {before: ..., after: ...} — mapeado para `dados_anteriores`/`dados_novos`
        metadata:    Dados extras (sem coluna correspondente nesta versão)
        user_email:  Email do usuário — mapeado para `usuario`
    """
    try:
        ip_address = None

        if has_request_context():
            ip_address = request.remote_addr
            if not user_email:
                from flask import g
                user_email = getattr(g, "user_email", None)

        changes_json = json.dumps(changes, default=str) if changes else None
        metadata_json = json.dumps(metadata, default=str) if metadata else None

        with db_connection() as (conn, db_type):
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO audit_logs
                    (user_email, action, target_type, target_id, changes, metadata, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_email,
                    action,
                    target_type,
                    str(target_id),
                    changes_json,
                    metadata_json,
                    ip_address,
                ),
            )

            conn.commit()

        return True

    except Exception as e:
        if current_app:
            current_app.logger.error(f"Falha ao registrar log de auditoria: {e}", exc_info=True)
        return False


def get_diff(old_obj: dict, new_obj: dict, ignore_keys: list | None = None) -> dict | None:
    """
    Gera um diff entre dois dicionários (antes e depois).
    Útil para gerar o payload de 'changes'.
    """
    if ignore_keys is None:
        ignore_keys = ["updated_at", "last_activity"]

    from typing import Any
    changes: dict[str, dict[str, Any]] = {"before": {}, "after": {}}
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
