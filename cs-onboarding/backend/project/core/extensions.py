import logging
logger = logging.getLogger(__name__)

import boto3
from authlib.integrations.flask_client import OAuth
from botocore.client import Config as BotocoreConfig
from cachetools import TTLCache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

_logger = logging.getLogger(__name__)

oauth = OAuth()

r2_client = None

# Type hint para satisfazer mypy
from typing import cast
from typing import Any

limiter: Limiter = cast(Limiter, None) 

# Cache para regras de gamificação (100 itens, 10 min TTL)
gamification_rules_cache: TTLCache[str, Any] = TTLCache(maxsize=100, ttl=600)


def init_limiter(app):
    """
    Inicializa o Flask-Limiter com limites globais moderados.

    SEGURANÇA: Limite global de 100 requisições/minuto por IP para prevenir abuso.
    Rotas críticas (login, registro) têm limites mais restritivos.
    """
    global limiter

    try:
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["100 per minute"],
            storage_uri="memory://",
            strategy="fixed-window",
            headers_enabled=True,
            default_limits_exempt_when=lambda: False,
        )

        limiter.init_app(app)
    except Exception as e:
        _logger.error(f"Falha ao inicializar Flask-Limiter: {e}", exc_info=True)


def init_r2(app):
    """Inicializa o cliente Boto3 R2 dentro do contexto do app."""
    global r2_client

    try:
        if app.config.get("R2_CONFIGURADO", False):
            r2_client = boto3.client(
                "s3",
                endpoint_url=app.config["R2_ENDPOINT_URL"],
                aws_access_key_id=app.config["R2_ACCESS_KEY_ID"],
                aws_secret_access_key=app.config["R2_SECRET_ACCESS_KEY"],
                config=BotocoreConfig(signature_version="s3v4", s3={"addressing_style": "virtual"}),
                region_name="auto",
            )
    except Exception as e:
        _logger.error(f"Falha ao inicializar cliente R2: {e}", exc_info=True)
        r2_client = None