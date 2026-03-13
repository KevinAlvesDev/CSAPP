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
MAX_FILE_UPLOAD_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_BASE64_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
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


def _get_storage_config():
    """Valida e retorna (bucket_name, public_url_base, None) ou (None, None, error_response)."""
    if not r2_client:
        return None, None, (jsonify({"ok": False, "error": "Sistema de upload nao configurado"}), 503)
    # Config oficial usa prefixo CLOUDFLARE_*; mantemos fallback R2_* por compatibilidade.
    bucket_name = current_app.config.get("CLOUDFLARE_BUCKET_NAME") or current_app.config.get("R2_BUCKET_NAME")
    public_url_base = current_app.config.get("CLOUDFLARE_PUBLIC_URL") or current_app.config.get("R2_PUBLIC_URL")
    if not bucket_name or not public_url_base:
        return None, None, (jsonify({"ok": False, "error": "Configuracao de storage incompleta"}), 503)
    return bucket_name, public_url_base, None


def _parse_multipart_upload():
    """Lê e valida arquivo de formulário multipart. Retorna (binary_data, filename, None) ou (None, None, error)."""
    file = request.files.get("file") or request.files.get("image")
    if not file or not file.filename:
        return None, None, (jsonify({"ok": False, "error": "Nenhum arquivo selecionado"}), 400)

    filename_str = str(file.filename)
    ext = filename_str.rsplit(".", 1)[1].lower() if "." in filename_str else ""
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        return None, None, (jsonify({"ok": False, "error": "Formato nao suportado. Use imagem, PDF ou Word (.doc/.docx)."}), 400)

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > MAX_FILE_UPLOAD_BYTES:
        return None, None, (jsonify({"ok": False, "error": "Arquivo muito grande. Maximo 10MB"}), 400)

    return file.read(), secure_filename(filename_str), None


def _parse_base64_upload():
    """Decodifica imagem base64 do JSON. Retorna (binary_data, filename, None) ou (None, None, error)."""
    data = request.get_json() or {}
    base64_data = data.get("image_base64")
    if not base64_data:
        return None, None, (jsonify({"ok": False, "error": "Dados da imagem nao fornecidos"}), 400)

    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]

    try:
        binary_data = base64.b64decode(base64_data)
    except Exception as exc:
        api_logger.error(f"Erro ao decodificar base64 do upload: {exc}", exc_info=True)
        return None, None, (jsonify({"ok": False, "error": "Dados base64 invalidos"}), 400)

    if len(binary_data) > MAX_BASE64_UPLOAD_BYTES:
        return None, None, (jsonify({"ok": False, "error": "Imagem muito grande. Maximo 5MB"}), 400)

    return binary_data, f"pasted-image-{uuid.uuid4().hex[:8]}.png", None


def _upload_comment_attachment_impl():
    """
    Faz upload de anexo para comentario.
    Aceita multipart/form-data (file/image) ou base64 (apenas imagem colada).
    """
    bucket_name, public_url_base, err = _get_storage_config()
    if err:
        return err

    if "file" in request.files or "image" in request.files:
        binary_data, filename, err = _parse_multipart_upload()
    elif request.is_json:
        binary_data, filename, err = _parse_base64_upload()
    else:
        return jsonify({"ok": False, "error": "Formato de requisicao invalido"}), 400

    if err:
        return err

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
    return jsonify({
        "ok": True,
        "attachment_url": attachment_url,
        "image_url": attachment_url,  # compat legado
        "filename": filename,
        "content_type": content_type,
        "is_image": content_type.startswith("image/"),
    })


@upload_bp.route("/comment-attachment", methods=["POST"])
@login_required
@validate_api_origin
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address() or "unknown")
def upload_comment_attachment():
    try:
        return _upload_comment_attachment_impl()
    except Exception as e:
        api_logger.error(f"Erro ao processar upload de anexo: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro interno ao processar arquivo"}), 500


@upload_bp.route("/comment-image", methods=["POST"])
@login_required
@validate_api_origin
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address() or "unknown")
def upload_comment_image():
    """
    Compatibilidade retroativa: endpoint antigo de upload.
    """
    try:
        return _upload_comment_attachment_impl()
    except Exception as e:
        api_logger.error(f"Erro ao processar upload de imagem: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro interno ao processar imagem"}), 500
