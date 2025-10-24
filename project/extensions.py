import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from authlib.integrations.flask_client import OAuth
from flask import current_app

# Cria instâncias vazias
oauth = OAuth()
r2_client = None

def init_extensions(app):
    """Inicializa as extensões com a config da app"""
    global r2_client
    
    # --- Inicializa Auth0 (OAuth) ---
    oauth.init_app(app)
    oauth.register(
        'auth0',
        client_id=app.config['AUTH0_CLIENT_ID'],
        client_secret=app.config['AUTH0_CLIENT_SECRET'],
        client_kwargs={'scope': 'openid profile email'},
        server_metadata_url=f'https://{app.config["AUTH0_DOMAIN"]}/.well-known/openid-configuration'
    )
    print("Extensão OAuth (Auth0) inicializada.")

    # --- Inicializa Boto3 (Cloudflare R2) ---
    if app.config['R2_CONFIGURED']:
        try:
            r2_client = boto3.client(
                's3',
                endpoint_url=app.config['CLOUDFLARE_ENDPOINT_URL'],
                aws_access_key_id=app.config['CLOUDFLARE_ACCESS_KEY_ID'],
                aws_secret_access_key=app.config['CLOUDFLARE_SECRET_ACCESS_KEY'],
                region_name=app.config['AWS_REGION']
            )
            
            # --- INÍCIO DA CORREÇÃO ---
            # Verifica a conexão testando o bucket específico, não listando todos
            bucket_name = app.config['CLOUDFLARE_BUCKET_NAME']
            r2_client.head_bucket(Bucket=bucket_name)
            print(f"Cliente Boto3 R2 inicializado e conectado ao bucket '{bucket_name}'.")
            # --- FIM DA CORREÇÃO ---

            if not app.config['CLOUDFLARE_PUBLIC_URL']:
                print("AVISO: CLOUDFLARE_PUBLIC_URL não definida. URLs de imagem podem não funcionar.")
        except (ClientError, NoCredentialsError) as e:
            # Esta mensagem de erro agora pegará 'AccessDenied' se as chaves estiverem erradas
            print(f"ERRO CRÍTICO ao inicializar Boto3 R2: {e}. Uploads desativados.")
            r2_client = None
        except Exception as e:
            print(f"ERRO INESPERADO ao inicializar Boto3 R2: {e}. Uploads desativados.")
            r2_client = None
    else:
        print("AVISO: Configuração R2 incompleta. Uploads desativados.")
        r2_client = None
