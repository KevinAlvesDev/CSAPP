import os
from flask import Flask, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS  # Já está importado
from .config import Config
from .extensions import oauth, r2_client, init_extensions
from .db import init_app as init_db_app

# Define o caminho absoluto para o diretório do projeto
project_dir = os.path.dirname(os.path.abspath(__file__))
# Define o caminho absoluto para a pasta raiz da aplicação
app_root_dir = os.path.dirname(project_dir)
# Define o caminho absoluto para a pasta static
static_dir = os.path.join(app_root_dir, 'static')

print(f"DEBUG: Flask usará pasta static em: {static_dir}")


def create_app():
    """Application Factory Function"""
    app = Flask(__name__, static_folder=static_dir)

    # Carrega a configuração do config.py
    app.config.from_object(Config)
    
    # --- CORREÇÃO DO CORS ---
    # Em vez da configuração padrão, especificamos exatamente
    # qual 'origem' (o seu front-end React) pode aceder à API
    # e que pode enviar 'credentials' (os cookies de login).
    CORS(app, 
         origins=["http://localhost:5173"],  # Permite o seu front-end
         supports_credentials=True         # Permite o envio de cookies
    )
    print("Extensão Flask-CORS inicializada (com origem específica).")
    # -------------------------

    # Corrige o proxy para o Gunicorn/Heroku/outros proxies
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Inicializa extensões (OAuth, Boto3/R2)
    init_extensions(app)

    # Configura o banco de dados
    init_db_app(app)

    # --- Registro de Blueprints ---
    from .blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
    print("Blueprint 'auth' registrado.")

    from .blueprints.main import main_bp
    app.register_blueprint(main_bp)
    print("Blueprint 'main' registrado.")

    from .blueprints.profile import profile_bp
    app.register_blueprint(profile_bp)
    print("Blueprint 'profile' registrado.")

    from .blueprints.api import api_bp
    app.register_blueprint(api_bp)
    print("Blueprint 'api' registrado.")

    from .blueprints.management import management_bp
    app.register_blueprint(management_bp)
    print("Blueprint 'management' registrado.")

    from .blueprints.analytics import analytics_bp
    app.register_blueprint(analytics_bp)
    print("Blueprint 'analytics' registrado.")

    try:
        from .blueprints.gamification import gamification_bp
        app.register_blueprint(gamification_bp)
        print("Blueprint 'gamification' registrado com sucesso.")
    except ImportError as e:
        print(f"ERRO CRÍTICO: Falha ao importar/registrar Blueprint 'gamification'. Erro: {e}")

    # Adiciona a pasta de uploads local como rota estática
    @app.route('/uploads/<path:filename>')
    def serve_uploads(filename):
        uploads_dir = os.path.join(app_root_dir, 'uploads')
        if not os.path.isdir(uploads_dir):
             from flask import abort
             print(f"AVISO: Diretório de uploads não encontrado: {uploads_dir}")
             return abort(404)
        return send_from_directory(uploads_dir, filename)

    # Rota para favicon
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.static_folder, 'images'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

    return app