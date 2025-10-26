import os
from flask import Flask, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import Config
from .extensions import oauth, r2_client, init_extensions
from .db import init_app as init_db_app
from . import utils # Para registrar os filtros do Jinja2

# Define o caminho absoluto para o diretório do projeto (APP-23-10/project/)
project_dir = os.path.dirname(os.path.abspath(__file__))
# Define o caminho absoluto para a pasta raiz da aplicação (APP-23-10/)
app_root_dir = os.path.dirname(project_dir)
# Define o caminho absoluto para a pasta de templates (APP-23-10/templates/)
templates_dir = os.path.join(app_root_dir, 'templates')

# NOVO: Define o caminho absoluto para a pasta static (APP-23-10/static/)
static_dir = os.path.join(app_root_dir, 'static')

# NOVO: PRINT DE DEBUG CRÍTICO
print(f"DEBUG CRÍTICO: Flask está usando a pasta static em: {static_dir}")

def create_app():
    """Application Factory Function"""
    # NOVO: Adicionando explicitamente o static_folder
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    # Carrega a configuração do config.py
    app.config.from_object(Config)

    # Corrige o proxy para o Gunicorn/Heroku
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Inicializa extensões (OAuth, Boto3/R2)
    init_extensions(app)

    # Configura o banco de dados (registra get_db, close_connection, init_db_command)
    init_db_app(app)

    # --- Registro de Blueprints ---
    # Importa e registra o Blueprint Auth
    from .blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)

    # Importa e registra o Blueprint Main
    from .blueprints.main import main_bp
    app.register_blueprint(main_bp)

    from .blueprints.profile import profile_bp
    app.register_blueprint(profile_bp)

    from .blueprints.api import api_bp
    app.register_blueprint(api_bp)
    
    # REGISTRO DO BLUEPRINT MANAGEMENT
    try:
        from .blueprints.management import management_bp
        app.register_blueprint(management_bp)
        print("Blueprint 'management' registrado com sucesso.")
    except ImportError as e:
        print(f"ERRO CRÍTICO: Falha ao importar Blueprint 'management'. Erro: {e}")

    # NOVO: REGISTRO DO BLUEPRINT ANALYTICS
    try:
        from .blueprints.analytics import analytics_bp
        app.register_blueprint(analytics_bp)
        print("Blueprint 'analytics' registrado com sucesso.")
    except ImportError as e:
        print(f"ERRO CRÍTICO: Falha ao importar Blueprint 'analytics'. Erro: {e}")


    # Registra filtros de template (ex: format_date_br)
    # Isso torna as funções de utils.py disponíveis no HTML
    @app.template_filter('format_date_br')
    def format_date_br_filter(dt_obj, include_time=False):
        return utils.format_date_br(dt_obj, include_time)

    # Adiciona a pasta de uploads local como rota estática (para fallback)
    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        # A pasta 'uploads' está um nível acima de 'project' (APP-23-10/uploads)
        uploads_dir = os.path.join(app_root_dir, 'uploads')
        return send_from_directory(uploads_dir, filename)

    return app