from __future__ import annotations

import json
import time

from flask import Blueprint, Response, g, jsonify, request, stream_with_context

from ....blueprints.auth import login_required
from ....modules.perfis.application.perfis_service import verificar_permissao_por_contexto
from ..application.chat_service import (
    create_or_get_direct_conversation,
    delete_message,
    edit_message,
    get_stream_state,
    list_conversations,
    list_messages,
    mark_conversation_read,
    search_users,
    send_message,
)

chat_api_bp = Blueprint("chat_api", __name__, url_prefix="/chat/api")


def _forbidden_response(permission_code: str):
    return (
        jsonify(
            {
                "ok": False,
                "error": "Sem permissao para usar o chat",
                "required_permission": permission_code,
            }
        ),
        403,
    )


@chat_api_bp.get("/conversations")
@login_required
def get_conversations():
    if not verificar_permissao_por_contexto(g.perfil, "chat.view"):
        return _forbidden_response("chat.view")

    conversations = list_conversations(g.user_email, getattr(g, "modulo_atual", "onboarding"))
    return jsonify({"ok": True, "items": conversations})


@chat_api_bp.post("/conversations")
@login_required
def create_conversation():
    if not verificar_permissao_por_contexto(g.perfil, "chat.send"):
        return _forbidden_response("chat.send")

    data = request.get_json(silent=True) or {}
    other_user_email = (data.get("other_user_email") or "").strip().lower()
    if not other_user_email:
        return jsonify({"ok": False, "error": "Usuario de destino e obrigatorio"}), 400

    try:
        conversation_id = create_or_get_direct_conversation(
            g.user_email,
            other_user_email,
            getattr(g, "modulo_atual", "onboarding"),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({"ok": True, "conversation_id": conversation_id})


@chat_api_bp.get("/messages")
@login_required
def get_messages():
    if not verificar_permissao_por_contexto(g.perfil, "chat.view"):
        return _forbidden_response("chat.view")

    conversation_id = request.args.get("conversation_id", type=int)
    before_id = request.args.get("before", type=int)

    if not conversation_id:
        return jsonify({"ok": False, "error": "conversation_id e obrigatorio"}), 400

    try:
        messages = list_messages(conversation_id, g.user_email, before_id=before_id)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404

    return jsonify({"ok": True, "items": messages})


@chat_api_bp.post("/messages")
@login_required
def post_message():
    if not verificar_permissao_por_contexto(g.perfil, "chat.send"):
        return _forbidden_response("chat.send")

    data = request.get_json(silent=True) or {}
    conversation_id = data.get("conversation_id")
    content = data.get("content")
    attachment = {
        "attachment_url": data.get("attachment_url"),
        "attachment_name": data.get("attachment_name"),
        "attachment_content_type": data.get("attachment_content_type"),
    }

    try:
        conversation_id = int(conversation_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "conversation_id invalido"}), 400

    try:
        message = send_message(conversation_id, g.user_email, content, attachment=attachment)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({"ok": True, "item": message})


@chat_api_bp.put("/messages/<int:message_id>")
@login_required
def put_message(message_id: int):
    if not verificar_permissao_por_contexto(g.perfil, "chat.send"):
        return _forbidden_response("chat.send")

    data = request.get_json(silent=True) or {}
    content = data.get("content")

    try:
        item = edit_message(message_id, g.user_email, content)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({"ok": True, "item": item})


@chat_api_bp.delete("/messages/<int:message_id>")
@login_required
def remove_message(message_id: int):
    if not verificar_permissao_por_contexto(g.perfil, "chat.send"):
        return _forbidden_response("chat.send")

    try:
        item = delete_message(message_id, g.user_email)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({"ok": True, "item": item})


@chat_api_bp.post("/conversations/<int:conversation_id>/read")
@login_required
def mark_read(conversation_id: int):
    if not verificar_permissao_por_contexto(g.perfil, "chat.view"):
        return _forbidden_response("chat.view")

    try:
        mark_conversation_read(conversation_id, g.user_email)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404

    return jsonify({"ok": True})


@chat_api_bp.get("/users")
@login_required
def users_search():
    if not verificar_permissao_por_contexto(g.perfil, "chat.send"):
        return _forbidden_response("chat.send")

    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"ok": True, "items": []})

    items = search_users(query, g.user_email, limit=10)
    return jsonify({"ok": True, "items": items})


@chat_api_bp.get("/stream")
@login_required
def stream_events():
    if not verificar_permissao_por_contexto(g.perfil, "chat.view"):
        return _forbidden_response("chat.view")

    user_email = g.user_email

    def event_stream():
        last_payload = ""
        try:
            while True:
                state = get_stream_state(user_email)
                payload = json.dumps(state, ensure_ascii=False)

                if payload != last_payload:
                    yield f"event: sync\ndata: {payload}\n\n"
                    last_payload = payload
                else:
                    yield "event: ping\ndata: {}\n\n"

                time.sleep(1.5)
        except (GeneratorExit, ConnectionResetError, BrokenPipeError):
            # Cliente fechou/renovou a conexão SSE. Encerramento esperado.
            return

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
