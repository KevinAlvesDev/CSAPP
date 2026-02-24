"""
Endpoint de upload de anexos para comentarios.
"""

import base64
import os
import uuid
from io import BytesIO

from flask import Blueprint, current_app, g, jsonify, request
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from ..blueprints.auth import login_required
from ..config.logging_config import api_logger
from ..core.extensions import limiter, r2_client
from ..security.api_security import validate_api_origin

upload_bp = Blueprint("upload", __name__, url_prefix="/api/upload")

ALLOWED_ATTACHMENT_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "doc", "docx"}
ALLOWED_ATTACHMENT_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _upload_comment_attachment_impl():
    """
    Faz upload de anexo para comentario.
    Aceita multipart/form-data (file/image) ou base64 (apenas imagem colada).
    """
    # Verificar se R2 esta configurado
    if not r2_client:
        return jsonify({"ok": False, "error": "Sistema de upload nao configurado"}), 503

    # Config oficial do projeto usa prefixo CLOUDFLARE_*.
    # Mantemos fallback para R2_* por compatibilidade.
    bucket_name = current_app.config.get("CLOUDFLARE_BUCKET_NAME") or current_app.config.get("R2_BUCKET_NAME")
    public_url_base = current_app.config.get("CLOUDFLARE_PUBLIC_URL") or current_app.config.get("R2_PUBLIC_URL")

    if not bucket_name or not public_url_base:
        return jsonify({"ok": False, "error": "Configuracao de storage incompleta"}), 503

    binary_data = None
    filename = None

    # Upload de arquivo
    if "file" in request.files or "image" in request.files:
        file = request.files.get("file") or request.files.get("image")
        if not file or file.filename == "":
            return jsonify({"ok": False, "error": "Nenhum arquivo selecionado"}), 400

        ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            return jsonify(
                {"ok": False, "error": "Formato nao suportado. Use imagem, PDF ou Word (.doc/.docx)."}
            ), 400

        # Max 10MB
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 10 * 1024 * 1024:
            return jsonify({"ok": False, "error": "Arquivo muito grande. Maximo 10MB"}), 400

        binary_data = file.read()
        filename = secure_filename(file.filename)

    # Base64 (cola de imagem)
    elif request.is_json:
        data = request.get_json() or {}
        base64_data = data.get("image_base64")
        if not base64_data:
            return jsonify({"ok": False, "error": "Dados da imagem nao fornecidos"}), 400

        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]

        try:
            binary_data = base64.b64decode(base64_data)
        except Exception:
            return jsonify({"ok": False, "error": "Dados base64 invalidos"}), 400

        if len(binary_data) > 5 * 1024 * 1024:
            return jsonify({"ok": False, "error": "Imagem muito grande. Maximo 5MB"}), 400

        filename = f"pasted-image-{uuid.uuid4().hex[:8]}.png"

    else:
        return jsonify({"ok": False, "error": "Formato de requisicao invalido"}), 400

    unique_filename = f"comentarios/{uuid.uuid4().hex}-{filename}"
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    content_type = ALLOWED_ATTACHMENT_MIME.get(ext, "application/octet-stream")

    try:
        r2_client.upload_fileobj(
            BytesIO(binary_data),
            bucket_name,
            unique_filename,
            ExtraArgs={"ContentType": content_type},
        )
    except Exception as e:
        api_logger.error(f"Erro ao fazer upload para R2: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao fazer upload do arquivo"}), 500

    attachment_url = f"{public_url_base}/{unique_filename}"

    return jsonify(
        {
            "ok": True,
            "attachment_url": attachment_url,
            "image_url": attachment_url,  # compat legado
            "filename": filename,
            "content_type": content_type,
            "is_image": content_type.startswith("image/"),
        }
    )


@upload_bp.route("/comment-attachment", methods=["POST"])
@login_required
@validate_api_origin
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def upload_comment_attachment():
    try:
        return _upload_comment_attachment_impl()
    except Exception as e:
        api_logger.error(f"Erro ao processar upload de anexo: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro interno ao processar arquivo"}), 500


@upload_bp.route("/comment-image", methods=["POST"])
@login_required
@validate_api_origin
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def upload_comment_image():
    """
    Compatibilidade retroativa: endpoint antigo de upload.
    """
    try:
        return _upload_comment_attachment_impl()
    except Exception as e:
        api_logger.error(f"Erro ao processar upload de imagem: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro interno ao processar imagem"}), 500
