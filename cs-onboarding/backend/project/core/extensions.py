from authlib.integrations.flask_client import OAuth
import boto3
from botocore.client import Config as BotocoreConfig
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from cachetools import TTLCache

oauth = OAuth()

r2_client = None
limiter = None

gamification_rules_cache = TTLCache(maxsize=10, ttl=3600)

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
        print("Extensão Limiter inicializada (limite global: 100 req/min).")
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao inicializar a extensão Limiter: {e}")
        limiter = None

def init_r2(app):
    """Inicializa o cliente Boto3 R2 dentro do contexto do app."""
    global r2_client
    
    try:

        if app.config.get('R2_CONFIGURADO', False):

            r2_client = boto3.client(
                's3',
                endpoint_url=app.config['R2_ENDPOINT_URL'],
                aws_access_key_id=app.config['R2_ACCESS_KEY_ID'],
                aws_secret_access_key=app.config['R2_SECRET_ACCESS_KEY'],
                config=BotocoreConfig(
                    signature_version='s3v4',
                    s3={'addressing_style': 'virtual'}\
                ),
                region_name='auto'\
            )
            print("Extensão R2 (boto3 client) inicializada.")
        else:
            print("Extensão R2: Configurações ausentes, cliente não inicializado.")
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao inicializar a extensão R2 (boto3): {e}")

        pass
