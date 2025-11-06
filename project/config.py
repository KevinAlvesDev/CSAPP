import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env (para desenvolvimento local)
# Isso NÃO vai sobrescrever variáveis de ambiente existentes (como as do Railway)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

class Config:
    """Configuração base da aplicação."""
    
    # --- Chave Secreta (CORRIGIDO) ---
    # Tenta 'SECRET_KEY' (padrão de produção, ex: Railway)
    # Se não achar, tenta 'FLASK_SECRET_KEY' (do .env local)
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("Nenhuma variável de ambiente SECRET_KEY ou FLASK_SECRET_KEY foi definida.")

    # --- Configuração do Banco de Dados (CORRIGIDO) ---
    # Pega a DATABASE_URL diretamente do ambiente (fornecida pelo Railway)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # A decisão de usar SQLite agora é explícita:
    # Só usa SQLite se DATABASE_URL NÃO estiver definida.
    if DATABASE_URL:
        USE_SQLITE_LOCALLY = False
        print("Config: DATABASE_URL encontrada. Usando PostgreSQL.")
    else:
        USE_SQLITE_LOCALLY = True
        print("Config: DATABASE_URL não encontrada. Usando SQLite local.")
        
    # --- Configuração do Auth0 ---
    AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
    AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
    
    if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET]):
        raise ValueError("Uma ou mais variáveis de ambiente do Auth0 (DOMAIN, CLIENT_ID, CLIENT_SECRET) não estão definidas.")

    # --- Configuração do R2 (Cloudflare) (CORRIGIDO para bater com o .env) ---
    # O .env usa 'CLOUDFLARE_...'
    R2_ENDPOINT_URL = os.environ.get('CLOUDFLARE_ENDPOINT_URL')
    R2_ACCESS_KEY_ID = os.environ.get('CLOUDFLARE_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = os.environ.get('CLOUDFLARE_SECRET_ACCESS_KEY')
    R2_BUCKET_NAME = os.environ.get('CLOUDFLARE_BUCKET_NAME')
    R2_PUBLIC_URL_BASE = os.environ.get('CLOUDFLARE_PUBLIC_URL') # .env usa PUBLIC_URL
    
    # Verifica se todas as variáveis R2 necessárias estão presentes
    R2_CONFIGURADO = all([
        R2_ENDPOINT_URL,
        R2_ACCESS_KEY_ID, 
        R2_SECRET_ACCESS_KEY, 
        R2_BUCKET_NAME, 
        R2_PUBLIC_URL_BASE
    ])
    
    if not R2_CONFIGURADO:
        print("AVISO DE CONFIGURAÇÃO: Uma ou mais variáveis Cloudflare R2 não estão definidas. O upload de imagens está desativado.")
    else:
         print("Config: R2 (Cloudflare) configurado.")
         
    # --- Configuração da Sessão ---
    # Define o tempo de vida da sessão (ex: 7 dias)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 dias em segundos
    SESSION_PERMANENT = True
    SESSION_TYPE = 'filesystem' 
    SESSION_COOKIE_SECURE = not USE_SQLITE_LOCALLY # Em produção, usar cookies seguros
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'