import os
from flask import Flask, session, g, render_template, request, flash, redirect, url_for
from flask_session import Session # Importa o Session
from .config import Config
from .extensions import oauth, init_r2 # <-- IMPORTA A NOVA FUNÇÃO init_r2
from . import db # Importa o módulo db

# Importa os blueprints
from .blueprints.main import main_bp
from .blueprints.auth import auth_bp
from .blueprints.api import api_bp
from .blueprints.implantacao_actions import implantacao_actions_bp
from .blueprints.profile import profile_bp
from .blueprints.management import management_bp
from .blueprints.analytics import analytics_bp
from .blueprints.gamification import gamification_bp

# Importa constantes para o 'g'
from .constants import PERFIS_COM_GESTAO, PERFIL_ADMIN
from .db import query_db # Para o before_request


def create_app():
    app = Flask(__name__,
                static_folder='../static', 
                template_folder='../templates')
    
    # 1. Carrega a configuração (config.py)
    app.config.from_object(Config)

    # 2. Inicializa extensões
    Session(app) # Inicializa o Flask-Session
    oauth.init_app(app)
    init_r2(app) # <-- ADICIONA A INICIALIZAÇÃO DO R2 AQUI
    db.init_app(app)
    
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
                g.perfil = None # Garante que é None em caso de falha no DB
        
        # Se o perfil não foi encontrado no DB (ou não estava logado),
        # cria um placeholder
        if g.perfil is None:
             g.perfil = {
                'nome': g.user.get('name', g.user_email) if g.user else 'Visitante',
                'usuario': g.user_email,
                'foto_url': None,
                'cargo': None,
                'perfil_acesso': None
            }
        
        # Injeta constantes globais no 'g' para uso nos templates
        # (Lê do app.config, que é seguro)
        g.R2_CONFIGURED = app.config.get('R2_CONFIGURADO', False)
        g.PERFIS_COM_GESTAO = PERFIS_COM_GESTAO
        g.PERFIL_ADMIN = PERFIL_ADMIN
    
    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('dashboard.html'), 404 # Redireciona para o dashboard em 404

    @app.errorhandler(500)
    def internal_server_error(e):
        print(f"ERRO 500: {e}")
        flash("Ocorreu um erro interno no servidor.", "error")
        return render_template('dashboard.html'), 500 # Redireciona para o dashboard
    
    return app