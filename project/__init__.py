# app2/CSAPP/project/__init__.py
import os
from flask import Flask, session, g, render_template, request, flash, redirect, url_for
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix # Para o HTTPS do Railway
from .config import Config
from .extensions import oauth, init_r2

# --- CORREÇÃO ---
# TODAS as importações de módulos do projeto (db, utils, domain, constants)
# foram REMOVIDAS do topo para evitar a importação circular.
# Elas serão importadas DENTRO de create_app().
# --- FIM DA CORREÇÃO ---


def create_app():
    app = Flask(__name__,
                static_folder='../static', 
                template_folder='../templates')

    # Adiciona o ProxyFix para o HTTPS do Railway
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1
    )
    
    # 1. Carrega a configuração (config.py)
    app.config.from_object(Config)

    # --- INÍCIO DA CORREÇÃO (Importações Atrasadas) ---
    # Importa os módulos APÓS a 'app' ser criada.
    from . import db 
    from .domain.gamification_service import _get_all_gamification_rules_grouped
    from .utils import format_date_br, format_date_iso_for_json
    from .constants import PERFIS_COM_GESTAO, PERFIL_ADMIN
    from .db import query_db
    # --- FIM DA CORREÇÃO ---

    # Registrar os filtros no Jinja2
    app.jinja_env.filters['format_date_br'] = format_date_br
    app.jinja_env.filters['format_date_iso'] = format_date_iso_for_json

    # 2. Inicializa extensões
    Session(app) # Inicializa o Flask-Session
    oauth.init_app(app)
    init_r2(app) 
    db.init_app(app)
    
    # Registrar o cliente Auth0
    oauth.register(
        name='auth0',
        client_id=app.config['AUTH0_CLIENT_ID'],
        client_secret=app.config['AUTH0_CLIENT_SECRET'],
        authorize_url=f"https://{app.config['AUTH0_DOMAIN']}/authorize",
        access_token_url=f"https://{app.config['AUTH0_DOMAIN']}/oauth/token",
        server_metadata_url=f"https://{app.config['AUTH0_DOMAIN']}/.well-known/openid-configuration",
        client_kwargs={'scope': 'openid profile email'},
    )

    # Importa os blueprints AQUI, depois de tudo estar configurado
    from .blueprints.main import main_bp
    from .blueprints.auth import auth_bp
    from .blueprints.api import api_bp
    from .blueprints.implantacao_actions import implantacao_actions_bp
    from .blueprints.profile import profile_bp
    from .blueprints.management import management_bp
    from .blueprints.analytics import analytics_bp
    from .blueprints.gamification import gamification_bp

    # 3. Registra os Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(implantacao_actions_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gamification_bp)

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
                g.perfil = None 
        
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
            g.gamification_rules = _get_all_gamification_rules_grouped()
        except Exception as e:
            print(f"ALERTA: Falha ao carregar regras de gamificação no before_request: {e}")
            g.gamification_rules = {} 
    
    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        flash("Página não encontrada. Redirecionando para o Dashboard.", "warning")
        return redirect(url_for('main.dashboard'))

    @app.errorhandler(500)
    def internal_server_error(e):
        print(f"ERRO 500: {e}")
        flash("Ocorreu um erro interno no servidor. Redirecionando para o Dashboard.", "error")
        return redirect(url_for('main.dashboard'))
    
    return app# app2/CSAPP/project/__init__.py
import os
from flask import Flask, session, g, render_template, request, flash, redirect, url_for
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix # Para o HTTPS do Railway
from .config import Config
from .extensions import oauth, init_r2

# --- CORREÇÃO ---
# TODAS as importações de módulos do projeto (db, utils, domain, constants)
# foram REMOVIDAS do topo para evitar a importação circular.
# Elas serão importadas DENTRO de create_app().
# --- FIM DA CORREÇÃO ---


def create_app():
    app = Flask(__name__,
                static_folder='../static', 
                template_folder='../templates')

    # Adiciona o ProxyFix para o HTTPS do Railway
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1
    )
    
    # 1. Carrega a configuração (config.py)
    app.config.from_object(Config)

    # --- INÍCIO DA CORREÇÃO (Importações Atrasadas) ---
    # Importa os módulos APÓS a 'app' ser criada.
    from . import db 
    from .domain.gamification_service import _get_all_gamification_rules_grouped
    from .utils import format_date_br, format_date_iso_for_json
    from .constants import PERFIS_COM_GESTAO, PERFIL_ADMIN
    from .db import query_db
    # --- FIM DA CORREÇÃO ---

    # Registrar os filtros no Jinja2
    app.jinja_env.filters['format_date_br'] = format_date_br
    app.jinja_env.filters['format_date_iso'] = format_date_iso_for_json

    # 2. Inicializa extensões
    Session(app) # Inicializa o Flask-Session
    oauth.init_app(app)
    init_r2(app) 
    db.init_app(app)
    
    # Registrar o cliente Auth0
    oauth.register(
        name='auth0',
        client_id=app.config['AUTH0_CLIENT_ID'],
        client_secret=app.config['AUTH0_CLIENT_SECRET'],
        authorize_url=f"https://{app.config['AUTH0_DOMAIN']}/authorize",
        access_token_url=f"https://{app.config['AUTH0_DOMAIN']}/oauth/token",
        server_metadata_url=f"https://{app.config['AUTH0_DOMAIN']}/.well-known/openid-configuration",
        client_kwargs={'scope': 'openid profile email'},
    )

    # Importa os blueprints AQUI, depois de tudo estar configurado
    from .blueprints.main import main_bp
    from .blueprints.auth import auth_bp
    from .blueprints.api import api_bp
    from .blueprints.implantacao_actions import implantacao_actions_bp
    from .blueprints.profile import profile_bp
    from .blueprints.management import management_bp
    from .blueprints.analytics import analytics_bp
    from .blueprints.gamification import gamification_bp

    # 3. Registra os Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(implantacao_actions_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gamification_bp)

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
                g.perfil = None 
        
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
            g.gamification_rules = _get_all_gamification_rules_grouped()
        except Exception as e:
            print(f"ALERTA: Falha ao carregar regras de gamificação no before_request: {e}")
            g.gamification_rules = {} 
    
    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        flash("Página não encontrada. Redirecionando para o Dashboard.", "warning")
        return redirect(url_for('main.dashboard'))

    @app.errorhandler(500)
    def internal_server_error(e):
        print(f"ERRO 500: {e}")
        flash("Ocorreu um erro interno no servidor. Redirecionando para o Dashboard.", "error")
        return redirect(url_for('main.dashboard'))
    
    return app