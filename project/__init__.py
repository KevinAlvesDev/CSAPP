import os
from flask import Flask, send_from_directory, g, session 
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import Config
from .extensions import oauth, r2_client, init_extensions
from .db import init_app as init_db_app, query_db 
from . import utils 

# Importa as constantes de perfil
from .constants import PERFIS_COM_GESTAO

project_dir = os.path.dirname(os.path.abspath(__file__))
app_root_dir = os.path.dirname(project_dir)
templates_dir = os.path.join(app_root_dir, 'templates')
static_dir = os.path.join(app_root_dir, 'static')

print(f"DEBUG: Flask usará pasta static em: {static_dir}")
print(f"DEBUG: Flask usará pasta templates em: {templates_dir}")


def create_app():
    """Application Factory Function"""
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    app.config.from_object(Config)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    init_extensions(app)
    init_db_app(app)
    
    # --- INÍCIO DA CORREÇÃO (REMOVER IMPORT CIRCULAR) ---
    # A importação de _get_all_gamification_rules_grouped foi MOVIDA
    # daqui de cima para DENTRO da função 'before_request_func'
    # --- FIM DA CORREÇÃO ---


    @app.before_request
    def before_request_func():
        """
        Executado antes de cada request.
        Carrega usuário, perfil e, se for gestor, as regras da gamificação.
        """
        
        # --- INÍCIO DA CORREÇÃO (MOVER IMPORT PARA CÁ) ---
        # Importa a função aqui para quebrar o ciclo de importação
        try:
            from .blueprints.gamification import _get_all_gamification_rules_grouped
        except ImportError:
            print("AVISO: Falha ao importar _get_all_gamification_rules_grouped. (before_request)")
            # Define uma função placeholder se a importação falhar
            def _get_all_gamification_rules_grouped():
                print("USANDO PLACEHOLDER: _get_all_gamification_rules_grouped")
                return {}
        # --- FIM DA CORREÇÃO ---
        
        g.user = session.get('user')
        g.user_email = g.user.get('email') if g.user else None
        
        g.PERFIS_COM_GESTAO = PERFIS_COM_GESTAO
        g.is_manager = False
        g.gamification_rules = {} 
        
        if g.user_email:
            session.permanent = True
            session.modified = True   
            
            g.perfil = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (g.user_email,), one=True)
            
            if not g.perfil:
                 g.perfil = {
                    'nome': g.user.get('name', g.user_email),
                    'usuario': g.user_email,
                    'foto_url': None,
                    'cargo': None,
                    'perfil_acesso': None 
                }
            
            if g.perfil.get('perfil_acesso') in g.PERFIS_COM_GESTAO:
                g.is_manager = True
                try:
                    # Agora a função é chamada após ter sido importada localmente
                    g.gamification_rules = _get_all_gamification_rules_grouped()
                except Exception as e:
                    print(f"AVISO: Falha ao pré-carregar regras de gamificação para gestor: {e}")
                    g.gamification_rules = {}
            
        else:
            g.perfil = None 


    # --- Registro de Blueprints ---
    try:
        from .blueprints.auth import auth_bp
        app.register_blueprint(auth_bp)
        print("Blueprint 'auth' registrado.")
    except ImportError as e: print(f"ERRO ao importar/registrar 'auth': {e}")

    try:
        from .blueprints.main import main_bp
        app.register_blueprint(main_bp)
        print("Blueprint 'main' registrado.")
    except ImportError as e: print(f"ERRO ao importar/registrar 'main': {e}")

    try:
        from .blueprints.implantacao_actions import actions_bp
        app.register_blueprint(actions_bp)
        print("Blueprint 'actions' (Implantacao Actions) registrado.")
    except ImportError as e: print(f"ERRO ao importar/registrar 'actions': {e}")

    try:
        from .blueprints.profile import profile_bp
        app.register_blueprint(profile_bp)
        print("Blueprint 'profile' registrado.")
    except ImportError as e: print(f"ERRO ao importar/registrar 'profile': {e}")

    try:
        from .blueprints.api import api_bp
        app.register_blueprint(api_bp)
        print("Blueprint 'api' registrado.")
    except ImportError as e: print(f"ERRO ao importar/registrar 'api': {e}")

    try:
        from .blueprints.management import management_bp
        app.register_blueprint(management_bp)
        print("Blueprint 'management' registrado.")
    except ImportError as e: print(f"ERRO ao importar/registrar 'management': {e}")

    try:
        from .blueprints.analytics import analytics_bp
        app.register_blueprint(analytics_bp)
        print("Blueprint 'analytics' registrado.")
    except ImportError as e: print(f"ERRO ao importar/registrar 'analytics': {e}")

    try:
        from .blueprints.gamification import gamification_bp
        app.register_blueprint(gamification_bp)
        print("Blueprint 'gamification' registrado com sucesso.")
    except ImportError as e:
        print(f"ERRO CRÍTICO: Falha ao importar/registrar Blueprint 'gamification'. Erro: {e}")


    # Registra filtros de template
    @app.template_filter('format_date_br')
    def format_date_br_filter(dt_obj, include_time=False):
        if dt_obj is None:
            return 'N/A' 
        return utils.format_date_br(dt_obj, include_time)

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
        return send_from_directory(os.path.join(app.root_path, 'static', 'images'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


    return app