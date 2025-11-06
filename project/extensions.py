from authlib.integrations.flask_client import OAuth
import boto3
from botocore.client import Config as BotocoreConfig
# 'current_app' não é mais necessário aqui no import time

oauth = OAuth()

# --- INÍCIO DA CORREÇÃO (Mover para init_app) ---

# Define o placeholder no escopo global
r2_client = None

def init_r2(app):
    """Inicializa o cliente Boto3 R2 dentro do contexto do app."""
    global r2_client
    
    try:
        # A configuração é lida de app.config (passado pelo create_app)
        if app.config.get('R2_CONFIGURADO', False):
            # Usamos os nomes de variáveis do config.py (que lê do .env)
            r2_client = boto3.client(
                's3',
                endpoint_url=app.config['R2_ENDPOINT_URL'],
                aws_access_key_id=app.config['R2_ACCESS_KEY_ID'],
                aws_secret_access_key=app.config['R2_SECRET_ACCESS_KEY'],
                config=BotocoreConfig(
                    signature_version='s3v4',
                    s3={'addressing_style': 'virtual'} # Necessário para R2
                ),
                region_name='auto' # R2 geralmente usa 'auto'
            )
            print("Extensão R2 (boto3 client) inicializada.")
        else:
            print("Extensão R2: Configurações ausentes, cliente não inicializado.")
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao inicializar a extensão R2 (boto3): {e}")
        # Se falhar, r2_client permanece None
        pass
# --- FIM DA CORREÇÃO ---