# app2/CSAPP/project/config.py
import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

# Carrega variáveis do arquivo .env de forma robusta
# Procura o .env desde o diretório atual até os diretórios pais
_dotenv_path = find_dotenv()
if _dotenv_path:
    load_dotenv(_dotenv_path, override=True)
else:
    load_dotenv(override=True)

# Fallback explícito: tenta carregar .env na raiz do workspace
try:
    root_env = Path(__file__).resolve().parents[3] / '.env'
    if root_env.exists():
        load_dotenv(str(root_env), override=True)
        print(f"[Startup] .env carregado explicitamente de: {root_env}")
except Exception as e:
    print(f"[Startup] Aviso: falha ao carregar .env explícito: {e}")

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

    # Permite desativar Auth0 em desenvolvimento para evitar chamadas externas
    DISABLE_AUTH0 = os.environ.get('DISABLE_AUTH0', '').lower() in ('1', 'true', 'yes')
    AUTH0_ENABLED = not DISABLE_AUTH0

    if AUTH0_ENABLED and not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET]):
        raise ValueError("Uma ou mais variáveis de ambiente do Auth0 (DOMAIN, CLIENT_ID, CLIENT_SECRET) não estão definidas.")
    if not AUTH0_ENABLED:
        print("Config: Auth0 desativado (DESENVOLVIMENTO). Rotas de login usarão dev_login.")

    # --- Configuração do R2 (Cloudflare) (CORRIGIDO para bater com o .env) ---
    # O .env usa 'CLOUDFLARE_...'
    R2_ENDPOINT_URL = os.environ.get('CLOUDFLARE_ENDPOINT_URL')
    R2_ACCESS_KEY_ID = os.environ.get('CLOUDFLARE_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = os.environ.get('CLOUDFLARE_SECRET_ACCESS_KEY')
    
    # --- INÍCIO DA CORREÇÃO ---
    # O nome da variável no config deve ser o mesmo que o código usa.
    CLOUDFLARE_BUCKET_NAME = os.environ.get('CLOUDFLARE_BUCKET_NAME')
    CLOUDFLARE_PUBLIC_URL = os.environ.get('CLOUDFLARE_PUBLIC_URL')
    # --- FIM DA CORREÇÃO ---

    # Verifica se todas as variáveis R2 necessárias estão presentes
    R2_CONFIGURADO = all([
        R2_ENDPOINT_URL,
        R2_ACCESS_KEY_ID, 
        R2_SECRET_ACCESS_KEY, 
        CLOUDFLARE_BUCKET_NAME, # <-- Corrigido aqui
        CLOUDFLARE_PUBLIC_URL
    ])
    
    if not R2_CONFIGURADO:
        print("AVISO DE CONFIGURAÇÃO: Uma ou mais variáveis Cloudflare R2 não estão definidas. O upload de imagens está desativado.")
    else:
         print("Config: R2 (Cloudflare) configurado.")
         
    # --- Configuração da Sessão (CORRIGIDA) ---
    # Define o tempo de vida da sessão (ex: 7 dias)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 dias em segundos
    # SESSION_PERMANENT = True <-- REMOVIDO (será definido no login)
    # SESSION_TYPE = 'filesystem' <-- REMOVIDO (usará cookie padrão)
    SESSION_COOKIE_SECURE = not USE_SQLITE_LOCALLY # Em produção, usar cookies seguros
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # --- Configuração do Google OAuth (Agenda) ---
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    # Para ambientes locais, use algo como: http://127.0.0.1:5000/agenda/callback
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')
    GOOGLE_OAUTH_ENABLED = all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI])
    if not GOOGLE_OAUTH_ENABLED:
        print("Config: Google OAuth desativado (variáveis ausentes). Define GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI.")

    # Escopos do Google OAuth (configuráveis via .env)
    # Por padrão, evita escopos restritos (ex.: gmail.send) que exigem verificação/publicação
    GOOGLE_OAUTH_SCOPES = os.environ.get(
        'GOOGLE_OAUTH_SCOPES',
        'openid email profile https://www.googleapis.com/auth/calendar'
    )

    # --- Configuração de SMTP (E-mail para comentários externos) ---
    SMTP_HOST = os.environ.get('SMTP_HOST')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_FROM = os.environ.get('SMTP_FROM') or os.environ.get('SMTP_USER')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() in ('1','true','yes')
    SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'false').lower() in ('1','true','yes')
    EMAIL_CONFIGURADO = all([SMTP_HOST, SMTP_PORT, SMTP_FROM])
    if not EMAIL_CONFIGURADO:
        print("AVISO: SMTP não configurado (comentários externos não enviarão e-mails).")