import os
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {
    'png': ['image/png'],
    'jpg': ['image/jpeg'],
    'jpeg': ['image/jpeg'],
    'gif': ['image/gif'],
    'webp': ['image/webp'],
    'pdf': ['application/pdf'],
    'doc': ['application/msword'],
    'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'xls': ['application/vnd.ms-excel'],
    'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    'ppt': ['application/vnd.ms-powerpoint'],
    'pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
    'txt': ['text/plain'],
    'csv': ['text/csv', 'text/plain'],
    'zip': ['application/zip'],
    'rar': ['application/x-rar-compressed'],
}

MAX_FILE_SIZE = 10 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_extension(filename):
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return None

def validate_file_content(file_stream, filename):
    try:
        extension = get_file_extension(filename)
        if not extension:
            return False, "Arquivo sem extensão", None
        if extension not in ALLOWED_EXTENSIONS:
            return False, f"Extensão .{extension} não permitida", None
        if not MAGIC_AVAILABLE:
            return True, None, None
        file_stream.seek(0)
        file_header = file_stream.read(2048)
        file_stream.seek(0)
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(file_header)
        allowed_mimes = ALLOWED_EXTENSIONS[extension]
        if detected_mime not in allowed_mimes:
            current_app.logger.warning(
                f"MIME type mismatch: file '{filename}' has extension .{extension} "
                f"but MIME type is {detected_mime} (expected: {allowed_mimes})"
            )
            return False, f"Conteúdo do arquivo não corresponde à extensão .{extension}", detected_mime
        return True, None, detected_mime
    except Exception as e:
        current_app.logger.error(f"Error validating file content: {e}")
        return False, f"Erro ao validar arquivo: {str(e)}", None

def validate_file_size(file_stream, max_size=MAX_FILE_SIZE):
    try:
        file_stream.seek(0, os.SEEK_END)
        file_size = file_stream.tell()
        file_stream.seek(0)
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            return False, f"Arquivo muito grande ({file_size_mb:.2f} MB). Máximo: {max_size_mb:.0f} MB", file_size
        if file_size == 0:
            return False, "Arquivo vazio", file_size
        return True, None, file_size
    except Exception as e:
        current_app.logger.error(f"Error validating file size: {e}")
        return False, f"Erro ao validar tamanho: {str(e)}", 0

def validate_uploaded_file(file, filename=None):
    if not file:
        return False, "Nenhum arquivo enviado", None
    filename = filename or file.filename
    if not filename or filename == '':
        return False, "Nome de arquivo inválido", None
    safe_filename = secure_filename(filename)
    if not allowed_file(filename):
        extension = get_file_extension(filename)
        return False, f"Tipo de arquivo não permitido: .{extension}", None
    size_valid, size_error, file_size = validate_file_size(file.stream)
    if not size_valid:
        return False, size_error, None
    content_valid, content_error, mime_type = validate_file_content(file.stream, filename)
    if not content_valid:
        return False, content_error, None
    metadata = {
        'original_filename': filename,
        'safe_filename': safe_filename,
        'extension': get_file_extension(filename),
        'mime_type': mime_type,
        'size_bytes': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2)
    }
    return True, None, metadata
