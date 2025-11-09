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
    
    # Inicializa o rate limiter
    init_limiter(app)
    
    # Inicializa CSRF protection
    csrf.init_app(app)
    
    # Configura o sistema de logging
    setup_logging(app)

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
                    if not admin_exists:
                        execute_db("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)", (ADMIN_EMAIL, 'dev'))
                    perfil_exists = query_db("SELECT usuario FROM perfil_usuario WHERE usuario = %s", (ADMIN_EMAIL,), one=True)
                    if not perfil_exists:
                        execute_db(
                            "INSERT INTO perfil_usuario (usuario, nome, cargo, perfil_acesso, foto_url) VALUES (%s, %s, %s, %s, %s)",
                            (ADMIN_EMAIL, 'Admin Dev', None, PERFIL_ADMIN, None)
                        )
                except Exception as e_seed:
                    print(f"AVISO: Falha ao semear admin padrão: {e_seed}")
    except Exception as e_dbinit:
        print(f"AVISO: Falha ao inicializar DB automaticamente: {e_dbinit}")
    
    # Registrar o cliente Auth0
    # Registra o cliente Auth0 apenas se estiver habilitado
    if app.config.get('AUTH0_ENABLED', True):
        oauth.register(
            name='auth0',
            client_id=app.config['AUTH0_CLIENT_ID'],
            client_secret=app.config['AUTH0_CLIENT_SECRET'],
            authorize_url=f"https://{app.config['AUTH0_DOMAIN']}/authorize",
            access_token_url=f"https://{app.config['AUTH0_DOMAIN']}/oauth/token",
            server_metadata_url=f"https://{app.config['AUTH0_DOMAIN']}/.well-known/openid-configuration",
            client_kwargs={'scope': 'openid profile email'},
        )
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
                    'scope': 'openid email profile https://www.googleapis.com/auth/calendar',
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
    from .blueprints.implantacao_actions import implantacao_actions_bp
    from .blueprints.profile import profile_bp
    from .blueprints.management import management_bp
    from .blueprints.analytics import analytics_bp
    from .blueprints.gamification import gamification_bp
    from .blueprints.agenda import agenda_bp

    # Isenta o blueprint da API da verificação de CSRF (endpoints JSON via fetch)
    try:
        csrf.exempt(api_bp)
    except Exception as e:
        print(f"Aviso: não foi possível isentar CSRF no api_bp: {e}")

    # 3. Registra os Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(implantacao_actions_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(agenda_bp)

    # --- INÍCIO DA CORREÇÃO (BUG 1: Carregamento de Regras) ---
    # Carrega as regras de gamificação uma vez na inicialização
    try:
        with app.app_context():
            app.gamification_rules = _get_all_gamification_rules_grouped()
    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao carregar regras de gamificação na inicialização: {e}")
        app.gamification_rules = {} # Define como vazio para evitar falhas
    # --- FIM DA CORREÇÃO ---

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
        return response

    return app