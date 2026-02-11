from functools import wraps
from urllib.parse import urlparse

from flask import current_app, jsonify, request


def validate_api_origin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if current_app.config.get("DEBUG", False) or current_app.config.get("USE_SQLITE_LOCALLY", False):
                return f(*args, **kwargs)
        except Exception:
            pass

        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")

        if not origin and not referer:
            try:
                if request.host_url:
                    return f(*args, **kwargs)
            except Exception:
                pass
            current_app.logger.warning(
                f"API request without Origin/Referer: {request.method} {request.path} from {request.remote_addr}"
            )
            return jsonify({"ok": False, "error": "Origin ou Referer header obrigatório"}), 403

        allowed_origins = _get_allowed_origins()

        if origin:
            if not _is_origin_allowed(origin, allowed_origins):
                current_app.logger.warning(
                    f"API request from unauthorized origin: {origin} for {request.method} {request.path}"
                )
                return jsonify({"ok": False, "error": "Origin não autorizado"}), 403
        elif referer:
            referer_origin = _extract_origin_from_referer(referer)
            if not _is_origin_allowed(referer_origin, allowed_origins):
                current_app.logger.warning(
                    f"API request from unauthorized referer: {referer} for {request.method} {request.path}"
                )
                return jsonify({"ok": False, "error": "Referer não autorizado"}), 403

        return f(*args, **kwargs)

    return decorated_function


def _get_allowed_origins():
    allowed = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    if request.host_url:
        allowed.append(request.host_url.rstrip("/"))
    custom_origins = current_app.config.get("CORS_ALLOWED_ORIGINS", "")
    if isinstance(custom_origins, str) and custom_origins:
        for origin in custom_origins.split(","):
            origin = origin.strip()
            if origin:
                allowed.append(origin)
    elif isinstance(custom_origins, list):
        for origin in custom_origins:
            if origin:
                allowed.append(origin)
    return allowed


def _is_origin_allowed(origin, allowed_origins):
    if not origin:
        return False
    origin = origin.rstrip("/")
    return any(origin == allowed.rstrip("/") for allowed in allowed_origins)


def _extract_origin_from_referer(referer):
    if not referer:
        return None
    try:
        parsed = urlparse(referer)
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return None
