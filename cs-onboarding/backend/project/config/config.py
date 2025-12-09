import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# Prioridade: .env.local (desenvolvimento) > .env (produção)
try:
    root_path = Path(__file__).resolve().parents[3]
    env_local = root_path / '.env.local'
    env_prod = root_path / '.env'

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
except Exception:
    pass


class Config:
    """Configuração base da aplicação."""

    SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("Nenhuma variável de ambiente SECRET_KEY ou FLASK_SECRET_KEY foi definida.")

    DATABASE_URL = os.environ.get('DATABASE_URL')

    # --- BANCO DE DADOS EXTERNO ---
    EXTERNAL_DB_URL = os.environ.get('EXTERNAL_DB_URL')
    # ------------------------------

    USE_SQLITE_ENV = os.environ.get('USE_SQLITE_LOCALLY', '').lower() in ('true', '1', 'yes')

    # Verificar se é SQLite pela URL ou pela variável USE_SQLITE_LOCALLY
    if USE_SQLITE_ENV or (DATABASE_URL and DATABASE_URL.startswith('sqlite')):
        USE_SQLITE_LOCALLY = True
    elif DATABASE_URL:
        USE_SQLITE_LOCALLY = False
    else:
        USE_SQLITE_LOCALLY = True

    # Auth0 desabilitado automaticamente em desenvolvimento local
    USE_SQLITE_ENV = os.environ.get('USE_SQLITE_LOCALLY', '').lower() in ('true', '1', 'yes')
    if USE_SQLITE_ENV or (DATABASE_URL and DATABASE_URL.startswith('sqlite')):
        AUTH0_ENABLED = False  # Desabilitar Auth0 em desenvolvimento local
    else:
        AUTH0_ENABLED = os.environ.get('AUTH0_ENABLED', 'true').lower() in ('true', '1', 'yes')

    AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
    AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')

    R2_ENDPOINT_URL = os.environ.get('CLOUDFLARE_ENDPOINT_URL')
    R2_ACCESS_KEY_ID = os.environ.get('CLOUDFLARE_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = os.environ.get('CLOUDFLARE_SECRET_ACCESS_KEY')

    CLOUDFLARE_BUCKET_NAME = os.environ.get('CLOUDFLARE_BUCKET_NAME')
    CLOUDFLARE_PUBLIC_URL = os.environ.get('CLOUDFLARE_PUBLIC_URL')

    R2_CONFIGURADO = all([
        R2_ENDPOINT_URL,
        R2_ACCESS_KEY_ID,
        R2_SECRET_ACCESS_KEY,
        CLOUDFLARE_BUCKET_NAME,
        CLOUDFLARE_PUBLIC_URL
    ])


    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7

    # Ajuste para Localhost (HTTP) vs Produção (HTTPS)
    # Em localhost, SECURE deve ser False para o cookie ser enviado
    # SAMESITE='Lax' é recomendado para fluxos OAuth
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true' if not USE_SQLITE_LOCALLY else False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PREFERRED_URL_SCHEME = 'http'
    # SERVER_NAME não será forçado para evitar inconsistências; use o host atual da requisição

    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')
    GOOGLE_OAUTH_ENABLED = all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI])

    GOOGLE_OAUTH_SCOPES = os.environ.get(
        'GOOGLE_OAUTH_SCOPES',
        'openid email profile https://www.googleapis.com/auth/calendar'
    )

    EMAIL_DRIVER = os.environ.get('EMAIL_DRIVER', 'smtp').lower()

    SMTP_HOST = os.environ.get('SMTP_HOST')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_FROM = os.environ.get('SMTP_FROM') or os.environ.get('SMTP_USER')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
    SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'false').lower() in ('1', 'true', 'yes')

    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

    if EMAIL_DRIVER == 'smtp':
        EMAIL_CONFIGURADO = all([SMTP_HOST, SMTP_PORT, SMTP_FROM])
    elif EMAIL_DRIVER == 'sendgrid':
        EMAIL_CONFIGURADO = bool(SENDGRID_API_KEY)
    else:
        EMAIL_CONFIGURADO = False

    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '')
