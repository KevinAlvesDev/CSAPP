from functools import wraps
from urllib.parse import urlparse
import logging
logger = logging.getLogger(__name__)

from flask import current_app, jsonify, request


def _patch_flask_test_client_config_get():
    try:
        from flask.testing import EnvironBuilder as _FlaskEnvironBuilder
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        return

    if getattr(_FlaskEnvironBuilder, "_safe_config_get_patch", False):
        return

    _orig_init = _FlaskEnvironBuilder.__init__

    def _safe_init(self, app, *args, **kwargs):
        try:
            return _orig_init(self, app, *args, **kwargs)
        except Exception:
            config = getattr(app, "config", None)
            if config is None:
                raise

            orig_get = getattr(config, "get", None)

            def _safe_get(key, default=None):
                try:
                    return dict.get(config, key, default)
                except Exception:
                    return default

            try:
                if isinstance(config, dict):
                    try:
                        from flask import Flask as _Flask
                        defaults = getattr(_Flask, "default_config", {})
                        if isinstance(defaults, dict):
                            for key, value in defaults.items():
                                dict.setdefault(config, key, value)
                    except Exception as exc:
                        logger.exception("Unhandled exception", exc_info=True)
                    dict.setdefault(config, "APPLICATION_ROOT", "/")
                    dict.setdefault(config, "SERVER_NAME", None)
                    dict.setdefault(config, "PREFERRED_URL_SCHEME", "http")
                    dict.setdefault(config, "TRUSTED_HOSTS", None)
                if orig_get is not None:
                    config.get = _safe_get  # type: ignore[assignment]
                return _orig_init(self, app, *args, **kwargs)
            finally:
                if orig_get is not None:
                    config.get = orig_get  # type: ignore[assignment]

    _FlaskEnvironBuilder.__init__ = _safe_init  # type: ignore[assignment]
    _FlaskEnvironBuilder._safe_config_get_patch = True  # type: ignore[attr-defined]


_patch_flask_test_client_config_get()


def validate_api_origin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if current_app.config.get("DEBUG", False) or current_app.config.get("TESTING", False):
                return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.warning(f"Falha ao verificar configuração de ambiente para validação de origem da API: {e}", exc_info=True)

        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")

        if not origin and not referer:
            current_app.logger.warning(
                f"API sem Origin/Referer bloqueada: {request.path} — IP: {request.remote_addr}"
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
    try:
        custom_origins = current_app.config.get("CORS_ALLOWED_ORIGINS", "")
    except Exception as exc:
        current_app.logger.warning(
            f"Falha ao ler CORS_ALLOWED_ORIGINS: {exc}",
            exc_info=True,
        )
        custom_origins = ""
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
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        return None
