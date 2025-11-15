# app2/CSAPP/project/__init__.py
import os
from dotenv import load_dotenv, find_dotenv
from flask import Flask, session, g, render_template, request, flash, redirect, url_for, current_app, jsonify
# from flask_session import Session <-- REMOVIDO
from werkzeug.middleware.proxy_fix import ProxyFix # Para o HTTPS do Railway
from .extensions import oauth, init_r2, init_limiter, limiter
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .logging_config import setup_logging
import click

csrf = CSRFProtect()

# --- CORREÇÃO ---
# TODAS as importações de módulos do projeto (db, utils, domain, constants)
# foram REMOVIDAS do topo para evitar a importação circular.
# Elas serão importadas DENTRO de create_app().
# --- FIM DA CORREÇÃO ---


def create_app():
    app = Flask(__name__,
                static_folder='../../frontend/static', 
                template_folder='../../frontend/templates')

    # Adiciona o ProxyFix para o HTTPS do Railway
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1
    )
    
    # 0. Garante carregamento do .env ANTES de importar Config
    try:
        _dotenv_path = find_dotenv()
        if _dotenv_path:
            load_dotenv(_dotenv_path, override=True)
        else:
            load_dotenv(override=True)
        # Fallback explícito: tenta carregar .env na raiz do workspace
        from pathlib import Path
        root_env = Path(__file__).resolve().parents[3] / '.env'
        if root_env.exists():
            load_dotenv(str(root_env), override=True)
            print(f"[Startup] .env carregado explicitamente de: {root_env}")
    except Exception as e:
        print(f"[Startup] Aviso: falha ao carregar .env antes da Config: {e}")

    # 1. Carrega a configuração (config.py)
    from .config import Config
    app.config.from_object(Config)

    try:
        if app.config.get('USE_SQLITE_LOCALLY', False) or app.config.get('DEBUG', False):
            app.config['RATELIMIT_ENABLED'] = False
        else:
            app.config['RATELIMIT_ENABLED'] = True
    except Exception:
        app.config['RATELIMIT_ENABLED'] = True

    # i18n básico
    from .i18n import get_translator
    translator = get_translator(app)
    @app.context_processor
    def inject_i18n():
        return {
            't': translator,
            'lang': app.config.get('LANG', 'pt')
        }

    # Diagnóstico de inicialização: imprime variáveis Google
    try:
        gi = app.config.get('GOOGLE_CLIENT_ID')
        gs = app.config.get('GOOGLE_CLIENT_SECRET')
        gr = app.config.get('GOOGLE_REDIRECT_URI')
        print(f"[Startup] Google Config: CLIENT_ID={'definido' if gi else 'vazio'}, CLIENT_SECRET={'definido' if gs else 'vazio'}, REDIRECT_URI={'definido' if gr else 'vazio'}")
        print(f"[Startup] GOOGLE_OAUTH_ENABLED={bool(app.config.get('GOOGLE_OAUTH_ENABLED'))}")
    except Exception as e:
        print(f"[Startup] Falha ao imprimir Google Config: {e}")

    # Permite redirect_uri em HTTP (desenvolvimento/local). Útil para Authlib/OAuthlib.
    try:
        os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')
        os.environ.setdefault('AUTHLIB_INSECURE_TRANSPORT', '1')
    except Exception:
        pass

    # --- INÍCIO DA CORREÇÃO (Importações Atrasadas) ---
    # Importa os módulos APÓS a 'app' ser criada.
    from . import db 
    from .domain.gamification_service import _get_all_gamification_rules_grouped
    from .utils import format_date_br, format_date_iso_for_json
    from .constants import PERFIS_COM_GESTAO, PERFIL_ADMIN, ADMIN_EMAIL
    from .db import query_db, execute_db
    # --- FIM DA CORREÇÃO ---

    # Registrar os filtros no Jinja2
    app.jinja_env.filters['format_date_br'] = format_date_br
    app.jinja_env.filters['format_date_iso'] = format_date_iso_for_json

    # 2. Inicializa extensões
    # Session(app) # <-- REMOVIDO
    oauth.init_app(app)
    init_r2(app)
    db.init_app(app)

    # Inicializa Sentry para monitoramento de erros (se configurado)
    try:
        from .sentry_config import init_sentry
        init_sentry(app)
    except Exception as e:
        app.logger.warning(f"Sentry não inicializado: {e}")

    # Inicializa Flask-Compress para compressão de respostas
    from flask_compress import Compress
    compress = Compress()
    compress.init_app(app)
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html', 'text/css', 'text/xml', 'application/json',
        'application/javascript', 'text/javascript'
    ]
    app.config['COMPRESS_LEVEL'] = 6  # Nível de compressão (1-9, padrão 6)
    app.config['COMPRESS_MIN_SIZE'] = 500  # Comprime apenas respostas > 500 bytes

    # Inicializa Performance Monitoring (APM básico)
    from .performance_monitoring import performance_monitor
    performance_monitor.init_app(app)

    # Inicializa o connection pool para PostgreSQL
    from .db_pool import init_connection_pool, close_db_connection
    if not app.config.get('USE_SQLITE_LOCALLY', False):
        init_connection_pool(app)

    # Registra teardown para retornar conexões ao pool
    app.teardown_appcontext(close_db_connection)

    # Inicializa o rate limiter
    init_limiter(app)

    # Inicializa CSRF protection
    csrf.init_app(app)

    # Configura o sistema de logging
    setup_logging(app)

    # Configura middleware de segurança (headers de proteção)
    from .security_middleware import init_security_headers
    init_security_headers(app)

    # Inicializa o sistema de cache
    from .cache_config import init_cache
    init_cache(app)

    # --- Inicialização automática do DB em desenvolvimento (SQLite) ---
    # Cria tabelas e semeia o admin padrão se estiver em ambiente local (sem DATABASE_URL)
    try:
        if app.config.get('USE_SQLITE_LOCALLY', False):
            with app.app_context():
                # Cria/garante tabelas
                db.init_db()
                
                # Semeia usuário administrador padrão, se não existir
                try:
                    admin_exists = query_db("SELECT usuario FROM usuarios WHERE usuario = %s", (ADMIN_EMAIL,), one=True)
                    from werkzeug.security import generate_password_hash
                    seeded_hash = generate_password_hash('323397041')
                    if not admin_exists:
                        execute_db("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (ADMIN_EMAIL, seeded_hash))
                    else:
                        execute_db("UPDATE usuarios SET senha = %s WHERE usuario = %s", (seeded_hash, ADMIN_EMAIL))
                    perfil_exists = query_db("SELECT usuario FROM perfil_usuario WHERE usuario = %s", (ADMIN_EMAIL,), one=True)
                    if not perfil_exists:
                        execute_db(
                            "INSERT INTO perfil_usuario (usuario, nome, cargo, perfil_acesso, foto_url) VALUES (%s, %s, %s, %s, %s)",
                            (ADMIN_EMAIL, 'Admin Dev', None, PERFIL_ADMIN, None)
                        )
                    else:
                        execute_db("UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s", (PERFIL_ADMIN, ADMIN_EMAIL))
                except Exception as e_seed:
                    print(f"AVISO: Falha ao semear admin padrão: {e_seed}")
    except Exception as e_dbinit:
        print(f"AVISO: Falha ao inicializar DB automaticamente: {e_dbinit}")
    
    # Registrar o cliente Auth0
    # Registra o cliente Auth0 apenas se estiver habilitado
    if app.config.get('AUTH0_ENABLED', True):
        # Normaliza o domínio do Auth0 para evitar URLs inválidas (backticks, esquemas duplicados, barras finais)
        raw_domain = (app.config.get('AUTH0_DOMAIN') or '').strip().strip('`').strip()
        if raw_domain.startswith('http://') or raw_domain.startswith('https://'):
            raw_domain = raw_domain.split('://', 1)[1]
        auth0_domain = raw_domain.rstrip('/')

        authorize_url = f"https://{auth0_domain}/authorize"
        access_token_url = f"https://{auth0_domain}/oauth/token"
        server_metadata_url = f"https://{auth0_domain}/.well-known/openid-configuration"

        oauth.register(
            name='auth0',
            client_id=app.config['AUTH0_CLIENT_ID'],
            client_secret=app.config['AUTH0_CLIENT_SECRET'],
            authorize_url=authorize_url,
            access_token_url=access_token_url,
            server_metadata_url=server_metadata_url,
            client_kwargs={'scope': 'openid profile email'},
        )
        try:
            print(f"Auth0 registrado: domain={auth0_domain}")
        except Exception:
            pass
    else:
        print("Auth0 não registrado: AUTH0_ENABLED=False")

    # Registrar cliente Google (Agenda) se configurado
    try:
        if app.config.get('GOOGLE_OAUTH_ENABLED', False):
            # Define explicitamente os endpoints para evitar falhas ao buscar metadados
            oauth.register(
                name='google',
                client_id=app.config['GOOGLE_CLIENT_ID'],
                client_secret=app.config['GOOGLE_CLIENT_SECRET'],
                authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
                access_token_url='https://oauth2.googleapis.com/token',
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={
                    # Escopos agora configuráveis via .env (evita escopos restritos por padrão)
                    'scope': app.config.get('GOOGLE_OAUTH_SCOPES', 'openid email profile https://www.googleapis.com/auth/calendar'),
                    'prompt': 'consent',
                    'access_type': 'offline',
                },
            )
            print('OAuth Google registrado (Agenda).')
            # Revalida e loga após registro
            gi = app.config.get('GOOGLE_CLIENT_ID')
            gs = app.config.get('GOOGLE_CLIENT_SECRET')
            gr = app.config.get('GOOGLE_REDIRECT_URI')
            print(f"[Startup] Pós-registro OAuth: CLIENT_ID={'definido' if gi else 'vazio'}, CLIENT_SECRET={'definido' if gs else 'vazio'}, REDIRECT_URI={'definido' if gr else 'vazio'}")
        else:
            print('OAuth Google não registrado: GOOGLE_OAUTH_ENABLED=False')
    except Exception as e:
        print(f"AVISO: Falha ao registrar cliente OAuth Google: {e}")

    # Importa os blueprints AQUI, depois de tudo estar configurado
    from .blueprints.main import main_bp
    from .blueprints.auth import auth_bp
    from .blueprints.api import api_bp
    from .blueprints.api_v1 import api_v1_bp  # API versionada
    from .blueprints.implantacao_actions import implantacao_actions_bp
    from .blueprints.profile import profile_bp
    from .blueprints.management import management_bp
    from .blueprints.analytics import analytics_bp
    from .blueprints.gamification import gamification_bp
    from .blueprints.agenda import agenda_bp
    from .blueprints.health import health_bp
    from .api_docs import api_docs_bp

    # Isenta o blueprint da API da verificação de CSRF (endpoints JSON via fetch)
    try:
        csrf.exempt(api_bp)
        csrf.exempt(api_v1_bp)  # API v1 não precisa de CSRF
        csrf.exempt(health_bp)  # Health checks não precisam de CSRF
        csrf.exempt(api_docs_bp)  # Documentação não precisa de CSRF
    except Exception as e:
        print(f"Aviso: não foi possível isentar CSRF no api_bp: {e}")

    # 3. Registra os Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v1_bp)  # Registra API v1
    app.register_blueprint(implantacao_actions_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(api_docs_bp)

    # --- INÍCIO DA CORREÇÃO (BUG 1: Carregamento de Regras) ---
    # Carrega as regras de gamificação uma vez na inicialização
    try:
        with app.app_context():
            app.gamification_rules = _get_all_gamification_rules_grouped()
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao carregar regras de gamificação na inicialização: {e}")
        app.gamification_rules = {} # Define como vazio para evitar falhas
    # --- FIM DA CORREÇÃO ---

    # Comando CLI para backup de banco (para agendamento externo)
    @app.cli.command('backup-db')
    def backup_db_command():
        """Gera um backup do banco e imprime o caminho do arquivo."""
        try:
            from .blueprints.management import perform_backup
            result = perform_backup()
            click.echo(result.get('backup_file'))
        except Exception as e:
            click.echo(f"Erro ao executar backup: {e}")
            raise

    @app.before_request
    def load_logged_in_user():
        g.user_email = session.get('user', {}).get('email')
        g.user = session.get('user')
        
        g.perfil = None 
        if g.user_email:
            try:
                g.perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (g.user_email,), one=True)
            except Exception as e:
                print(f"ALERTA: Falha ao buscar perfil no before_request para {g.user_email}: {e}")
                # Fallback de desenvolvimento: se Auth0 estiver desativado e o usuário for ADMIN_EMAIL,
                # concede perfil Administrador para evitar bloqueios quando DB não está disponível.
                if not current_app.config.get('AUTH0_ENABLED', True) and g.user_email == ADMIN_EMAIL:
                    g.perfil = {
                        'nome': g.user.get('name', g.user_email) if g.user else 'Dev',
                        'usuario': g.user_email,
                        'foto_url': None,
                        'cargo': None,
                        'perfil_acesso': PERFIL_ADMIN
                    }
                else:
                    g.perfil = None 
        # Fortalece fallback em desenvolvimento: se perfil não existir ou perfil_acesso for None,
        # e Auth0 estiver desativado e o usuário for ADMIN_EMAIL, força Administrador.
        if not current_app.config.get('AUTH0_ENABLED', True) and g.user_email == ADMIN_EMAIL:
            if not g.perfil or g.perfil.get('perfil_acesso') is None:
                g.perfil = {
                    'nome': g.user.get('name', g.user_email) if g.user else 'Dev',
                    'usuario': g.user_email,
                    'foto_url': None,
                    'cargo': None,
                    'perfil_acesso': PERFIL_ADMIN
                }
        
        if g.perfil is None:
             g.perfil = {
                'nome': g.user.get('name', g.user_email) if g.user else 'Visitante',
                'usuario': g.user_email,
                'foto_url': None,
                'cargo': None,
                'perfil_acesso': None
            }
        
        g.R2_CONFIGURED = app.config.get('R2_CONFIGURADO', False)
        g.PERFIS_COM_GESTAO = PERFIS_COM_GESTAO
        g.PERFIL_ADMIN = PERFIL_ADMIN

        # --- INÍCIO DA CORREÇÃO (BUG 1: Leitura das Regras) ---
        # Lê as regras do contexto da aplicação (carregadas uma vez)
        # em vez de consultar o banco de dados a cada requisição.
        try:
            g.gamification_rules = current_app.gamification_rules
        except Exception as e:
            print(f"ALERTA: Falha ao carregar regras de gamificação no before_request (a partir do app.context): {e}")
            g.gamification_rules = {} 
        # --- FIM DA CORREÇÃO ---
    
    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        # Resposta JSON para solicitações da API
        if request.path.startswith('/api'):
            return jsonify({'ok': False, 'error': 'Recurso não encontrado'}), 404
        flash("Página não encontrada. Redirecionando para o Dashboard.", "warning")
        return redirect(url_for('main.dashboard'))

    @app.errorhandler(500)
    def internal_server_error(e):
        print(f"ERRO 500: {e}")
        # Resposta JSON para solicitações da API
        if request.path.startswith('/api'):
            return jsonify({'ok': False, 'error': 'Erro interno do servidor'}), 500
        flash("Ocorreu um erro interno no servidor. Redirecionando para o Dashboard.", "error")
        return redirect(url_for('main.dashboard'))

    # --- Segurança: Cabeçalhos HTTP ---
    @app.after_request
    def set_security_headers(response):
        # Proteções básicas
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        # HSTS (apenas se HTTPS estiver habilitado/por trás de proxy seguro)
        if request.headers.get('X-Forwarded-Proto', 'http') == 'https' or request.is_secure:
            # 6 meses de HSTS; includeSubDomains e preload opcionais
            response.headers.setdefault('Strict-Transport-Security', 'max-age=15552000; includeSubDomains')
        # Content-Security-Policy: permite CDNs necessários mantendo restrições
        csp = (
            "default-src 'self'; "
            # Permite imagens externas (ex.: R2 público) e data:
            "img-src 'self' data: https:; "
            # Permite estilos dos CDNs usados e gstatic (Google Translate)
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com https://www.gstatic.com; "
            # Alguns navegadores usam style-src-elem; alinhar com style-src
            "style-src-elem 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com https://www.gstatic.com; "
            # Scripts de CDNs necessários; incluir gstatic se usado por widgets
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://www.gstatic.com; "
            # Fontes de CDNs
            "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            # Conexões a origens HTTPS (Auth0/API externas, se houver)
            "connect-src 'self' https:"
        )
        response.headers.setdefault('Content-Security-Policy', csp)
        # Permissions-Policy (desativa features não usadas)
        response.headers.setdefault('Permissions-Policy', "geolocation=(), microphone=(), camera=(), fullscreen=(*)")
        try:
            if request.endpoint in ('auth.login', 'auth.dev_login', 'auth.dev_login_as', 'main.home', 'auth.register', 'auth.forgot_password', 'auth.reset_password'):
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
        except Exception:
            pass
        return response

    return app
