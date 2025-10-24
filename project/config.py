import os
from dotenv import load_dotenv

load_dotenv() # Carrega variáveis do .env

class Config:
    """Armazena as configurações da aplicação"""
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY não definida.")

    # Configuração da Pasta de Upload LOCAL (Fallback)
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Configuração do Cloudflare R2
    CLOUDFLARE_ENDPOINT_URL = os.environ.get('CLOUDFLARE_ENDPOINT_URL')
    CLOUDFLARE_ACCESS_KEY_ID = os.environ.get('CLOUDFLARE_ACCESS_KEY_ID')
    CLOUDFLARE_SECRET_ACCESS_KEY = os.environ.get('CLOUDFLARE_SECRET_ACCESS_KEY')
    CLOUDFLARE_BUCKET_NAME = os.environ.get('CLOUDFLARE_BUCKET_NAME')
    CLOUDFLARE_PUBLIC_URL = os.environ.get('CLOUDFLARE_PUBLIC_URL', '').rstrip('/')
    AWS_REGION = os.environ.get('AWS_REGION', 'auto')

    R2_CONFIGURED = all([
        CLOUDFLARE_ENDPOINT_URL,
        CLOUDFLARE_ACCESS_KEY_ID,
        CLOUDFLARE_SECRET_ACCESS_KEY,
        CLOUDFLARE_BUCKET_NAME
    ])

    # Configuração Auth0
    AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN")
    AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID")
    AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET")
    AUTH0_CONFIGURED = all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET])
    if not AUTH0_CONFIGURED:
         raise ValueError("Credenciais Auth0 não definidas.")

    # Configuração Banco de Dados
    DATABASE_URL = os.environ.get('DATABASE_URL')
    USE_SQLITE_LOCALLY = not DATABASE_URL
    LOCAL_SQLITE_DB = 'dashboard_simples.db'