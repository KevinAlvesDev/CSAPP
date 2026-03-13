import logging
import os
from pathlib import Path
logger = logging.getLogger(__name__)

from dotenv import find_dotenv, load_dotenv

_logger = logging.getLogger(__name__)

# Prioridade: .env.local (desenvolvimento) > .env (produção)
try:
    root_path = Path(__file__).resolve().parents[3]
    env_local = root_path / ".env.local"
    env_prod = root_path / ".env"

    if env_local.exists():
        load_dotenv(str(env_local), override=True)
    elif env_prod.exists():
        load_dotenv(str(env_prod), override=True)
    else:
        _dotenv_path = find_dotenv()
        if _dotenv_path:
            load_dotenv(_dotenv_path, override=True)
        else:
            load_dotenv(override=True)
except Exception as e:
    _logger.warning(f"Falha ao carregar variáveis de ambiente do arquivo .env: {e}", exc_info=True)


class Config:
    """Configuração base da aplicação."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("Nenhuma variável de ambiente SECRET_KEY foi definida.")

    DATABASE_URL = os.environ.get("DATABASE_URL")

    # --- BANCO DE DADOS EXTERNO ---
    # Removido em favor do acesso direto ao OAMD via DATABASE_URL
    # ------------------------------

    # Imagem de fundo da tela de login (arquivo em 'frontend/static')
    LOGIN_BG_FILE = os.environ.get("LOGIN_BG_FILE", "imagens/Meet_TimesSquare.png")

    # Endpoints de diagnóstico devem ficar desativados por padrão em produção.
    ENABLE_DIAGNOSTIC_SMTP = os.environ.get("ENABLE_DIAGNOSTIC_SMTP", "false").lower() in ("1", "true", "yes")
    CSP_STRICT_NONCE = os.environ.get("CSP_STRICT_NONCE", "false").lower() in ("1", "true", "yes")


    R2_ENDPOINT_URL = os.environ.get("CLOUDFLARE_ENDPOINT_URL")
    R2_ACCESS_KEY_ID = os.environ.get("CLOUDFLARE_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY = os.environ.get("CLOUDFLARE_SECRET_ACCESS_KEY")

    CLOUDFLARE_BUCKET_NAME = os.environ.get("CLOUDFLARE_BUCKET_NAME")
    CLOUDFLARE_PUBLIC_URL = os.environ.get("CLOUDFLARE_PUBLIC_URL")

    R2_CONFIGURADO = all(
        [R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, CLOUDFLARE_BUCKET_NAME, CLOUDFLARE_PUBLIC_URL]
    )

    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7

    # Ajuste para Localhost (HTTP) vs Produção (HTTPS)
    # Em localhost, SECURE deve ser False para o cookie ser enviado
    # SAMESITE='Lax' é recomendado para fluxos OAuth
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "True").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Em produção, forçar HTTPS para evitar redirect_uri_mismatch
    PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "https")
    # SERVER_NAME não será forçado para evitar inconsistências; use o host atual da requisição

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
    GOOGLE_OAUTH_ENABLED = all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI])

    # Escopos básicos para login (sempre solicitados)
    GOOGLE_OAUTH_SCOPES_BASIC = "openid email profile"

    # Escopos adicionais disponíveis (solicitados incrementalmente)
    GOOGLE_OAUTH_SCOPES_CALENDAR = "https://www.googleapis.com/auth/calendar"
    GOOGLE_OAUTH_SCOPES_DRIVE_FILE = "https://www.googleapis.com/auth/drive.file"
    GOOGLE_OAUTH_SCOPES_DRIVE_READONLY = "https://www.googleapis.com/auth/drive.readonly"

    # Escopos padrão (para compatibilidade com código existente)
    GOOGLE_OAUTH_SCOPES = os.environ.get(
        "GOOGLE_OAUTH_SCOPES",
        GOOGLE_OAUTH_SCOPES_BASIC,  # Apenas escopos básicos no login inicial
    )

    # ============================================
    # Feature Toggles (Otimizações)
    # ============================================
    USE_OPTIMIZED_DASHBOARD = os.environ.get("USE_OPTIMIZED_DASHBOARD", "false")

    EMAIL_DRIVER = os.environ.get("EMAIL_DRIVER", "smtp").lower()

    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    SMTP_FROM = os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER")
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes")

    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

    if EMAIL_DRIVER == "smtp":
        EMAIL_CONFIGURADO = all([SMTP_HOST, SMTP_PORT, SMTP_FROM])
    elif EMAIL_DRIVER == "sendgrid":
        EMAIL_CONFIGURADO = bool(SENDGRID_API_KEY)
    else:
        EMAIL_CONFIGURADO = False

    CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "")

    # Perfis de acesso disponíveis no sistema
    # Importar aqui para evitar dependência circular
    try:
        from ..constants import PERFIS_ACESSO_LIST

        PERFIS_DE_ACESSO = PERFIS_ACESSO_LIST
    except ImportError:
        # Fallback caso a importação falhe
        PERFIS_DE_ACESSO = ["Administrador", "Gerente", "Coordenador", "Implantador"]

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = "http"


class TestingConfig(Config):
    TESTING = True
    SESSION_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = "http"


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config() -> type[Config]:
    """Retorna a classe de config correta para o ambiente atual."""
    env = os.getenv("FLASK_ENV", "production")
    env_local = Path(__file__).resolve().parents[3] / ".env.local"
    if env_local.exists() and env == "production":
        env = "development"
    return _CONFIG_MAP.get(env, ProductionConfig)
