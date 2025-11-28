import os
from dotenv import load_dotenv, find_dotenv
from flask import Flask, session, g, render_template, request, flash, redirect, url_for, current_app, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix                          
from .core.extensions import oauth, init_r2, init_limiter, limiter
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .config.logging_config import setup_logging
import click

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__,
                static_folder='../../frontend/static', 
                template_folder='../../frontend/templates')

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1
    )
    
    try:
        _dotenv_path = find_dotenv()
        if _dotenv_path:
            load_dotenv(_dotenv_path, override=True)
        else:
            load_dotenv(override=True)
        from pathlib import Path
        root_env = Path(__file__).resolve().parents[3] / '.env'
        if root_env.exists():
            load_dotenv(str(root_env), override=True)
            print(f"[Startup] .env carregado explicitamente de: {root_env}")
    except Exception as e:
        print(f"[Startup] Aviso: falha ao carregar .env antes da Config: {e}")

    from .config import Config
    app.config.from_object(Config)

    try:
        if app.config.get('USE_SQLITE_LOCALLY', False) or app.config.get('DEBUG', False):
            app.config['RATELIMIT_ENABLED'] = False
        else:
            app.config['RATELIMIT_ENABLED'] = True
    except Exception:
        app.config['RATELIMIT_ENABLED'] = True

    from .common.i18n import get_translator
    translator = get_translator(app)
    @app.context_processor
    def inject_i18n():
        return {
            't': translator,
            'lang': app.config.get('LANG', 'pt')
        }

    try:
        gi = app.config.get('GOOGLE_CLIENT_ID')
        gs = app.config.get('GOOGLE_CLIENT_SECRET')
        gr = app.config.get('GOOGLE_REDIRECT_URI')
        print(f"[Startup] Google Config: CLIENT_ID={'definido' if gi else 'vazio'}, CLIENT_SECRET={'definido' if gs else 'vazio'}, REDIRECT_URI={'definido' if gr else 'vazio'}")
        print(f"[Startup] GOOGLE_OAUTH_ENABLED={bool(app.config.get('GOOGLE_OAUTH_ENABLED'))}")
    except Exception as e:
        print(f"[Startup] Falha ao imprimir Google Config: {e}")

    try:
        os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')
        os.environ.setdefault('AUTHLIB_INSECURE_TRANSPORT', '1')
    except Exception:
        pass

    from . import db 
    from .domain.gamification_service import _get_all_gamification_rules_grouped
    from .common.utils import format_date_br, format_date_iso_for_json
    from .constants import PERFIS_COM_GESTAO, PERFIL_ADMIN, ADMIN_EMAIL
    from .db import query_db, execute_db

    app.jinja_env.filters['format_date_br'] = format_date_br
    app.jinja_env.filters['format_date_iso'] = format_date_iso_for_json


    oauth.init_app(app)
    init_r2(app)
    db.init_app(app)

    try:
        from .config.sentry_config import init_sentry
        init_sentry(app)
    except Exception as e:
        app.logger.warning(f"Sentry não inicializado: {e}")

    from flask_compress import Compress
    compress = Compress()
    compress.init_app(app)
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html', 'text/css', 'text/xml', 'application/json',
        'application/javascript', 'text/javascript'
    ]
    app.config['COMPRESS_LEVEL'] = 6                                       
    app.config['COMPRESS_MIN_SIZE'] = 500                                         

    from .monitoring.performance_monitoring import performance_monitor
    performance_monitor.init_app(app)

    from .database import init_connection_pool, close_db_connection
    from .db import ensure_implantacoes_status_constraint
    if not app.config.get('USE_SQLITE_LOCALLY', False):
        init_connection_pool(app)
        try:
            with app.app_context():
                ensure_implantacoes_status_constraint()
        except Exception:
            pass

    app.teardown_appcontext(close_db_connection)

    init_limiter(app)

    csrf.init_app(app)

    setup_logging(app)

    from .security.middleware import init_security_headers
    init_security_headers(app)

    from .config.cache_config import init_cache
    init_cache(app)

    try:
        if app.config.get('USE_SQLITE_LOCALLY', False):
            with app.app_context():
                db.init_db()
                
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
    
    if app.config.get('AUTH0_ENABLED', True):
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

    try:
        if app.config.get('GOOGLE_OAUTH_ENABLED', False):
            oauth.register(
                name='google',
                client_id=app.config['GOOGLE_CLIENT_ID'],
                client_secret=app.config['GOOGLE_CLIENT_SECRET'],
                authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
                access_token_url='https://oauth2.googleapis.com/token',
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={
                    'scope': app.config.get('GOOGLE_OAUTH_SCOPES', 'openid email profile https://www.googleapis.com/auth/calendar'),
                    'prompt': 'consent',
                    'access_type': 'offline',
                },
            )
            print('OAuth Google registrado (Agenda).')
            
            gi = app.config.get('GOOGLE_CLIENT_ID')
            gs = app.config.get('GOOGLE_CLIENT_SECRET')
            gr = app.config.get('GOOGLE_REDIRECT_URI')
            print(f"[Startup] Pós-registro OAuth: CLIENT_ID={'definido' if gi else 'vazio'}, CLIENT_SECRET={'definido' if gs else 'vazio'}, REDIRECT_URI={'definido' if gr else 'vazio'}")
        else:
            print('OAuth Google não registrado: GOOGLE_OAUTH_ENABLED=False')
    except Exception as e:
        print(f"AVISO: Falha ao registrar cliente OAuth Google: {e}")

    from .blueprints.main import main_bp
    from .blueprints.auth import auth_bp
    from .blueprints.api import api_bp
    from .blueprints.api_v1 import api_v1_bp                  
    from .blueprints.implantacao_actions import implantacao_actions_bp
    from .blueprints.profile import profile_bp
    from .blueprints.management import management_bp
    from .blueprints.analytics import analytics_bp
    from .blueprints.gamification import gamification_bp
    from .blueprints.agenda import agenda_bp
    from .blueprints.health import health_bp
    from .blueprints.api_docs import api_docs_bp
    from .blueprints.planos_bp import planos_bp
    from .blueprints.api_h import api_h_bp

    try:
        csrf.exempt(api_bp)
        csrf.exempt(api_v1_bp)                              
        csrf.exempt(health_bp)                                      
        csrf.exempt(api_docs_bp)
        csrf.exempt(api_h_bp)
    except Exception as e:
        print(f"Aviso: não foi possível isentar CSRF no api_bp: {e}")

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v1_bp)                   
    app.register_blueprint(implantacao_actions_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(api_docs_bp)
    app.register_blueprint(planos_bp)
    app.register_blueprint(api_h_bp)


    try:
        with app.app_context():
            app.gamification_rules = _get_all_gamification_rules_grouped()
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao carregar regras de gamificação na inicialização: {e}")
        app.gamification_rules = {}                                       

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



        try:
            g.gamification_rules = current_app.gamification_rules
        except Exception as e:
            print(f"ALERTA: Falha ao carregar regras de gamificação no before_request (a partir do app.context): {e}")
            g.gamification_rules = {} 

    @app.errorhandler(404)
    def page_not_found(e):

        if request.path.startswith('/api'):
            return jsonify({'ok': False, 'error': 'Recurso não encontrado'}), 404
        flash("Página não encontrada. Redirecionando para o Dashboard.", "warning")
        return redirect(url_for('main.dashboard'))

    @app.errorhandler(500)
    def internal_server_error(e):
        print(f"ERRO 500: {e}")

        if request.path.startswith('/api'):
            return jsonify({'ok': False, 'error': 'Erro interno do servidor'}), 500
        flash("Ocorreu um erro interno no servidor. Redirecionando para o Dashboard.", "error")
        return redirect(url_for('main.dashboard'))

    return app
