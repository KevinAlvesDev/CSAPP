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

# Define o caminho absoluto para a pasta static (APP-23-10/static/)
static_dir = os.path.join(app_root_dir, 'static')

# PRINT DE DEBUG
print(f"DEBUG: Flask usará pasta static em: {static_dir}")
print(f"DEBUG: Flask usará pasta templates em: {templates_dir}")


def create_app():
    """Application Factory Function"""
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    # Carrega a configuração do config.py
    app.config.from_object(Config)

    # Corrige o proxy para o Gunicorn/Heroku/outros proxies
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Inicializa extensões (OAuth, Boto3/R2)
    init_extensions(app)

    # Configura o banco de dados (registra get_db, close_connection, init_db_command)
    init_db_app(app)

    # --- Registro de Blueprints (Blocos try/except removidos para garantir que erros de importação sejam visíveis e o registro seja forçado) ---
    
    # AUTH
    from .blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
    print("Blueprint 'auth' registrado.")

    # MAIN
    from .blueprints.main import main_bp
    app.register_blueprint(main_bp)
    print("Blueprint 'main' registrado.")

    # PROFILE (O foco da correção)
    from .blueprints.profile import profile_bp
    app.register_blueprint(profile_bp)
    print("Blueprint 'profile' registrado.")

    # API
    from .blueprints.api import api_bp
    app.register_blueprint(api_bp)
    print("Blueprint 'api' registrado.")

    # MANAGEMENT
    from .blueprints.management import management_bp
    app.register_blueprint(management_bp)
    print("Blueprint 'management' registrado.")

    # ANALYTICS
    from .blueprints.analytics import analytics_bp
    app.register_blueprint(analytics_bp)
    print("Blueprint 'analytics' registrado.")

    # --- NOVO BLUEPRINT (MANTIDO o try/except pois não é essencial para o erro) ---
    try:
        from .blueprints.gamification import gamification_bp
        app.register_blueprint(gamification_bp)
        print("Blueprint 'gamification' registrado com sucesso.")
    except ImportError as e:
        print(f"ERRO CRÍTICO: Falha ao importar/registrar Blueprint 'gamification'. Erro: {e}")
    # --- FIM NOVO BLUEPRINT ---


    # Registra filtros de template (ex: format_date_br)
    # Isso torna as funções de utils.py disponíveis no HTML
    @app.template_filter('format_date_br')
    def format_date_br_filter(dt_obj, include_time=False):
        # Adiciona verificação para evitar erro se dt_obj for None
        if dt_obj is None:
            return 'N/A' # Ou '', dependendo do desejado
        return utils.format_date_br(dt_obj, include_time)

    # Adiciona a pasta de uploads local como rota estática (para fallback)
    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        # A pasta 'uploads' está um nível acima de 'project' (APP-23-10/uploads)
        uploads_dir = os.path.join(app_root_dir, 'uploads')
        # Verifica se o diretório existe para evitar erros 500
        if not os.path.isdir(uploads_dir):
             from flask import abort
             print(f"AVISO: Diretório de uploads não encontrado: {uploads_dir}")
             return abort(404)
        return send_from_directory(uploads_dir, filename)

    # Rota para favicon (opcional, mas evita erros 404 no log)
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static', 'images'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


    return app