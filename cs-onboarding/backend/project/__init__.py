import os

import click
from dotenv import find_dotenv, load_dotenv
from flask import Flask, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from .config.logging_config import setup_logging
from .core.extensions import init_limiter, init_r2, limiter, oauth

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, static_folder="../../frontend/static", template_folder="../../frontend/templates")

    # Configuração do ProxyFix para lidar com HTTPS atrás de proxies (Render, Heroku, etc.)
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    try:
        from pathlib import Path

        # Ajuste: A raiz do projeto (onde está o .env) é parents[2] (cs-onboarding), não parents[3]
        project_root = Path(__file__).resolve().parents[2]

        # Prioridade: .env.local (desenvolvimento) > .env (produção)
        env_local = project_root / ".env.local"
        env_prod = project_root / ".env"

        if env_local.exists():
            load_dotenv(str(env_local), override=True)
        elif env_prod.exists():
            load_dotenv(str(env_prod), override=True)
        else:
            # Fallback para tentar encontrar o .env subindo diretórios
            _dotenv_path = find_dotenv()
            if _dotenv_path:
                load_dotenv(_dotenv_path, override=True)
            else:
                load_dotenv(override=True)
    except Exception:
        pass

    from .config import Config

    app.config.from_object(Config)

    # ================================================
    # VALIDAÇÃO DE SECRETS (fail-fast em produção)
    # ================================================
    try:
        from .config.secrets_validator import validate_secrets

        secrets_result = validate_secrets(app)
        if secrets_result["warnings"]:
            app.logger.warning(f"⚠️  Validação de secrets: {len(secrets_result['warnings'])} avisos")
    except Exception as e:
        # Em produção, SecretsValidationError já foi lançada
        # Em dev, apenas logar
        if not app.config.get("USE_SQLITE_LOCALLY", False):
            raise
        app.logger.warning(f"Validação de secrets ignorada em dev: {e}")

    # CSRF nunca expira (evita erro de token expirado em sessões longas)
    app.config["WTF_CSRF_TIME_LIMIT"] = None

    if test_config is not None:
        app.config.from_mapping(test_config)

    try:
        if app.config.get("USE_SQLITE_LOCALLY", False) or app.config.get("DEBUG", False):
            app.config["RATELIMIT_ENABLED"] = False
        else:
            app.config["RATELIMIT_ENABLED"] = True
    except Exception:
        app.config["RATELIMIT_ENABLED"] = True

    from .common.i18n import get_translator

    translator = get_translator(app)

    @app.context_processor
    def inject_i18n():
        return {"t": translator, "lang": app.config.get("LANG", "pt")}

    try:
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
        os.environ.setdefault("AUTHLIB_INSECURE_TRANSPORT", "1")
    except Exception:
        pass

    from . import db
    from .common.utils import format_date_br, format_date_iso_for_json
    from .constants import ADMIN_EMAIL, PERFIL_ADMIN, PERFIS_COM_GESTAO
    from .database import schema
    from .db import execute_db, query_db
    from .modules.gamification.application.gamification_service import _get_all_gamification_rules_grouped

    app.jinja_env.filters["format_date_br"] = format_date_br
    app.jinja_env.filters["format_date_iso"] = format_date_iso_for_json

    # ================================================
    # CACHE-BUSTING: Versão global para arquivos estáticos
    # ================================================
    import time
    from pathlib import Path

    # Gerar versão única por deploy (timestamp de início da aplicação)
    APP_VERSION = str(int(time.time()))

    # Função para obter versão do arquivo (mtime) ou fallback para APP_VERSION
    def get_static_version(filename):
        """Retorna a versão do arquivo estático para cache-busting."""
        try:
            static_folder = Path(app.static_folder)
            file_path = static_folder / filename
            if file_path.exists():
                return str(int(file_path.stat().st_mtime))
        except Exception:
            pass
        return APP_VERSION

    # Filtro Jinja para adicionar versão ao URL de arquivos estáticos
    def static_versioned(filename):
        """Retorna URL do arquivo estático com parâmetro de versão para cache-busting."""
        from flask import url_for

        version = get_static_version(filename)
        return url_for("static", filename=filename) + f"?v={version}"

    app.jinja_env.filters["static_versioned"] = static_versioned

    # Expor versão da aplicação globalmente nos templates
    @app.context_processor
    def inject_app_version():
        return {"APP_VERSION": APP_VERSION}

    oauth.init_app(app)

    init_r2(app)
    schema.init_app(app)

    try:
        from .config.sentry_config import init_sentry

        init_sentry(app)
    except Exception as e:
        app.logger.warning(f"Sentry não inicializado: {e}")

    from flask_compress import Compress

    compress = Compress()
    compress.init_app(app)
    app.config["COMPRESS_MIMETYPES"] = [
        "text/html",
        "text/css",
        "text/xml",
        "application/json",
        "application/javascript",
        "text/javascript",
    ]
    app.config["COMPRESS_LEVEL"] = 6
    app.config["COMPRESS_MIN_SIZE"] = 500

    from .monitoring.performance_monitoring import performance_monitor

    performance_monitor.init_app(app)

    from .database import close_db_connection, init_connection_pool
    from .database.schema import ensure_implantacoes_status_constraint

    # Inicializar pool de conexões (com retry logic para conexões instáveis)
    db_initialized = init_connection_pool(app)

    if db_initialized and not app.config.get("USE_SQLITE_LOCALLY", False):
        try:
            with app.app_context():
                ensure_implantacoes_status_constraint()
        except Exception as e:
            app.logger.warning(f"⚠️  Não foi possível verificar constraints: {e}")
    elif not db_initialized and not app.config.get("USE_SQLITE_LOCALLY", False):
        app.logger.warning(
            "⚠️  Aplicação iniciando SEM conexão com banco de dados. "
            "Algumas funcionalidades podem não estar disponíveis."
        )

    app.teardown_appcontext(close_db_connection)

    init_limiter(app)

    csrf.init_app(app)

    setup_logging(app)

    # ================================================
    # SANITIZAÇÃO DE LOGS (proteger dados sensíveis)
    # ================================================
    try:
        from .config.log_sanitizer import SensitiveDataFilter

        sanitize_filter = SensitiveDataFilter()
        for handler in app.logger.handlers:
            handler.addFilter(sanitize_filter)
        app.logger.info("🔒 Sanitização de logs ativada")
    except Exception as e:
        app.logger.warning(f"Sanitização de logs não ativada: {e}")

    from .security.middleware import configure_cors, init_security_headers

    init_security_headers(app)
    configure_cors(app)

    from .config.cache_config import init_cache

    cache_instance = init_cache(app)

    # ================================================
    # CACHE MANAGER APRIMORADO (TTL por recurso)
    # ================================================
    try:
        from .config.cache_manager import cache_manager

        cache_manager.init_app(app, cache_instance=cache_instance)
        app.logger.info("📦 Cache Manager com TTL por recurso inicializado")
    except Exception as e:
        app.logger.warning(f"Cache Manager não inicializado: {e}")

    # ================================================
    # SERVICE CONTAINER (Dependency Injection)
    # ================================================
    try:
        from .core.container import ServiceContainer
        from .core.service_registry import register_all_services

        container = ServiceContainer(app)
        register_all_services(app, container)
    except Exception as e:
        app.logger.warning(f"ServiceContainer não inicializado: {e}")

    # ================================================
    # EVENT HANDLERS (reações a eventos de domínio)
    # ================================================
    try:
        from .core.event_handlers import register_event_handlers
        from .core.events import event_bus

        register_event_handlers(event_bus)
    except Exception as e:
        app.logger.warning(f"Event Handlers não registrados: {e}")

    # Monitoramento de performance
    from .monitoring.performance_middleware import init_performance_monitoring

    init_performance_monitoring(app)

    try:
        # Log explícito do modo de banco de dados
        if app.config.get("USE_SQLITE_LOCALLY", False):
            app.logger.info("🗄️  DATABASE MODE: SQLite LOCAL")
        else:
            app.logger.info("🗄️  DATABASE MODE: PostgreSQL (Production)")

        if app.config.get("USE_SQLITE_LOCALLY", False):
            with app.app_context():
                # Garantir que o banco existe e está inicializado
                try:
                    from .database import get_db_connection

                    conn, _db_type = get_db_connection()
                    if conn:
                        conn.close()
                except Exception as e:
                    app.logger.warning(f"Banco não existe ainda, será criado: {e}")

                schema.init_db()
                try:
                    from .common.context_profiles import ensure_context_profile_schema

                    ensure_context_profile_schema()
                except Exception as e_ctx_schema:
                    app.logger.warning(f"Falha ao inicializar schema contextual de perfis: {e_ctx_schema}")

                # Criar usuário admin padrão automaticamente
                try:
                    from werkzeug.security import generate_password_hash

                    from .constants import ADMIN_EMAIL

                    seeded_hash = generate_password_hash("admin123@")
                    # Usar INSERT OR REPLACE para garantir que o admin existe
                    execute_db(
                        "INSERT OR REPLACE INTO usuarios (usuario, senha) VALUES (%s, %s)", (ADMIN_EMAIL, seeded_hash)
                    )
                    execute_db(
                        "INSERT OR REPLACE INTO perfil_usuario (usuario, nome, cargo, perfil_acesso, foto_url) VALUES (%s, %s, %s, %s, %s)",
                        (ADMIN_EMAIL, "Administrador", None, PERFIL_ADMIN, None),
                    )
                except Exception as e_seed:
                    app.logger.warning(f"Falha ao garantir usuário admin: {e_seed}")
    except Exception as e_dbinit:
        app.logger.warning(f"Falha na inicialização do banco (dev): {e_dbinit}")

    # ================================================
    # CACHE WARMING (moved after DB init)
    # ================================================
    try:
        from .common.context_profiles import ensure_context_profile_schema

        with app.app_context():
            ensure_context_profile_schema()
    except Exception as e:
        app.logger.warning(f"Falha ao garantir schema contextual de perfis: {e}")

    try:
        from .config.cache_warming import warm_cache

        with app.app_context():
            warm_cache(app)
    except Exception as e:
        app.logger.warning(f"Cache Warming falhou: {e}")

    if app.config.get("AUTH0_ENABLED", True):
        raw_domain = (app.config.get("AUTH0_DOMAIN") or "").strip().strip("`").strip()
        if raw_domain.startswith("http://") or raw_domain.startswith("https://"):
            raw_domain = raw_domain.split("://", 1)[1]
        auth0_domain = raw_domain.rstrip("/")

        authorize_url = f"https://{auth0_domain}/authorize"
        access_token_url = f"https://{auth0_domain}/oauth/token"
        server_metadata_url = f"https://{auth0_domain}/.well-known/openid-configuration"

        oauth.register(
            name="auth0",
            client_id=app.config["AUTH0_CLIENT_ID"],
            client_secret=app.config["AUTH0_CLIENT_SECRET"],
            authorize_url=authorize_url,
            access_token_url=access_token_url,
            server_metadata_url=server_metadata_url,
            client_kwargs={"scope": "openid profile email"},
        )

    try:
        if app.config.get("GOOGLE_OAUTH_ENABLED", False):
            oauth.register(
                name="google",
                client_id=app.config["GOOGLE_CLIENT_ID"],
                client_secret=app.config["GOOGLE_CLIENT_SECRET"],
                authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
                access_token_url="https://oauth2.googleapis.com/token",
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={
                    # Apenas escopos básicos no login inicial
                    "scope": app.config.get("GOOGLE_OAUTH_SCOPES_BASIC", "openid email profile"),
                    "prompt": "select_account",  # Permitir escolha de conta
                    "access_type": "offline",  # Obter refresh_token
                    "include_granted_scopes": "true",  # AUTORIZAÇÃO INCREMENTAL
                },
            )
        pass
    except Exception:
        pass

    from .modules.dashboard.api.agenda import agenda_bp
    from .modules.analytics.api.analytics import analytics_bp
    from .blueprints.api import api_bp
    from .blueprints.api_docs import api_docs_bp
    from .blueprints.api_v1 import api_v1_bp
    from .blueprints.api_planos import api_planos_bp
    from .blueprints.auth import auth_bp  # Blueprint de autenticação
    from .blueprints.checklist_api import checklist_bp
    from .blueprints.checklist_finalizacao_bp import checklist_finalizacao_bp
    from .blueprints.diagnostic_smtp import diagnostic_bp  # Diagnóstico SMTP
    from .blueprints.gamification import gamification_bp
    from .blueprints.health import health_bp

    # from .blueprints.implantacao_actions import implantacao_actions_bp # MOVIDO
    from .blueprints.main import main_bp
    from .blueprints.management import management_bp
    from .blueprints.perfis_bp import perfis_bp
    from .modules.planos.api.planos_bp import planos_bp
    from .blueprints.profile import profile_bp
    from .blueprints.risc_bp import risc_bp  # RISC (Proteção entre Contas)
    from .blueprints.upload import upload_bp

    try:
        csrf.exempt(api_v1_bp)
        csrf.exempt(health_bp)
        csrf.exempt(api_docs_bp)
        csrf.exempt(upload_bp)
        csrf.exempt(risc_bp)  # RISC precisa receber eventos do Google sem CSRF
        csrf.exempt(checklist_finalizacao_bp)  # API REST de checklist de finalização
        csrf.exempt(diagnostic_bp)  # Diagnóstico SMTP

        # checklist_bp deixa de ser isento para proteger mutações
    except Exception:
        pass

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(api_planos_bp)
    # app.register_blueprint(implantacao_actions_bp) # MOVIDO PARA ONBOARDING

    from .modules.onboarding.api.actions import onboarding_actions_bp

    app.register_blueprint(onboarding_actions_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(api_docs_bp)
    app.register_blueprint(planos_bp)

    app.register_blueprint(checklist_bp)
    app.register_blueprint(perfis_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(risc_bp)  # RISC (Proteção entre Contas)
    app.register_blueprint(checklist_finalizacao_bp)
    app.register_blueprint(diagnostic_bp)  # Diagnóstico SMTP

    from .blueprints.core import core_bp

    app.register_blueprint(core_bp)

    from .blueprints.config_api import config_api

    app.register_blueprint(config_api)

    from .blueprints.onboarding import onboarding_bp

    app.register_blueprint(onboarding_bp)

    from .blueprints.ongoing import ongoing_bp

    app.register_blueprint(ongoing_bp)

    from .blueprints.grandes_contas import grandes_contas_bp

    app.register_blueprint(grandes_contas_bp)

    from .modules.grandes_contas.api.actions import grandes_contas_actions_bp

    app.register_blueprint(grandes_contas_actions_bp, url_prefix="/grandes-contas/actions")

    try:
        with app.app_context():
            app.gamification_rules = _get_all_gamification_rules_grouped()
    except Exception as e:
        app.logger.error(f"Falha ao carregar regras de gamificação na inicialização: {e}", exc_info=True)
        app.gamification_rules = {}

    @app.cli.command("backup-db")
    def backup_db_command():
        """Gera um backup do banco e imprime o caminho do arquivo."""
        try:
            from .modules.management.application.management_service import perform_backup

            result = perform_backup()
            click.echo(result.get("backup_file"))
        except Exception as e:
            click.echo(f"Erro ao executar backup: {e}")
            raise

    @app.before_request
    def load_logged_in_user():
        # Ignorar rotas estáticas, API health e favicon
        if (
            request.path.startswith("/static/")
            or request.path.startswith("/api/health")
            or request.path == "/favicon.ico"
        ):
            return

        # Persistir contexto do módulo para evitar redirecionamentos cruzados.
        from .common.context_navigation import persist_current_context

        persist_current_context()

        # Importar constantes no início da função para garantir escopo
        from .constants import ADMIN_EMAIL, MASTER_ADMIN_EMAIL, PERFIL_ADMIN

        # Carregar usuário da sessão PRIMEIRO
        g.user_email = session.get("user", {}).get("email")
        g.user = session.get("user")

        # Login automático em desenvolvimento local
        use_sqlite = app.config.get("USE_SQLITE_LOCALLY", False)
        flask_debug = app.config.get("DEBUG", False)
        flask_env = os.environ.get("FLASK_ENV", "production")
        auth0_enabled = app.config.get("AUTH0_ENABLED", True)

        # Se estiver em dev local, Auth0 desabilitado, não houver usuário, e não for rota de auth
        if (use_sqlite or flask_debug) and flask_env != "production" and not auth0_enabled:
            rotas_auth = [
                "/login",
                "/dev-login",
                "/dev-login-as",
                "/logout",
                "/callback",
                "/login/google",
                "/login/google/callback",
            ]
            is_rota_auth = any(request.path.startswith(rota) for rota in rotas_auth)

            if not is_rota_auth and not g.user_email:
                try:
                    admin_email = ADMIN_EMAIL
                    session["user"] = {"email": admin_email, "name": "Administrador", "sub": "dev|local"}
                    session.permanent = True
                    # Atualizar g.user_email IMEDIATAMENTE
                    g.user_email = admin_email
                    g.user = session["user"]
                    # Sincronizar perfil
                    try:
                        from .blueprints.auth import _sync_user_profile

                        _sync_user_profile(admin_email, "Administrador", "dev|local")
                    except Exception as e:
                        app.logger.warning(f"Falha ao sincronizar perfil automático: {e}")
                except Exception as e:
                    app.logger.error(f"Erro no login automático: {e}")

        g.perfil = None
        if g.user_email:
            try:
                from .common.context_profiles import get_contextual_profile

                g.perfil = get_contextual_profile(g.user_email, getattr(g, "modulo_atual", None))
            except Exception as e:
                # Se a tabela não existir ainda, criar perfil básico
                app.logger.warning(f"Falha ao buscar perfil para {g.user_email}: {e}")
                g.perfil = None

        # Fallback para admin em desenvolvimento local
        if not auth0_enabled and g.user_email and g.user_email == ADMIN_EMAIL:
            if not g.perfil or g.perfil.get("perfil_acesso") is None:
                g.perfil = {
                    "nome": g.user.get("name", g.user_email) if g.user else "Administrador",
                    "usuario": g.user_email,
                    "foto_url": None,
                    "cargo": None,
                    "perfil_acesso": PERFIL_ADMIN,
                    "contexto": getattr(g, "modulo_atual", "onboarding"),
                }

        # Robustez: garantir PERFIL_ADMIN para ADMIN_EMAIL sempre que detectado
        if g.user_email and g.user_email == MASTER_ADMIN_EMAIL:
            try:
                if not g.perfil or g.perfil.get("perfil_acesso") != PERFIL_ADMIN:
                    from .common.context_profiles import set_user_role_for_all_contexts
                    from .modules.auth.application.auth_service import sync_user_profile_service, update_user_role_service

                    # Cria perfil se necessário e marca como admin
                    sync_user_profile_service(g.user_email, g.user.get("name", "Administrador"), "system|enforce")
                    update_user_role_service(g.user_email, PERFIL_ADMIN)
                    set_user_role_for_all_contexts(g.user_email, PERFIL_ADMIN, updated_by="system|enforce")
                    from .common.context_profiles import get_contextual_profile

                    g.perfil = get_contextual_profile(g.user_email, getattr(g, "modulo_atual", None)) or {
                        "nome": g.user.get("name", g.user_email) if g.user else "Administrador",
                        "usuario": g.user_email,
                        "foto_url": None,
                        "cargo": None,
                        "perfil_acesso": PERFIL_ADMIN,
                        "contexto": getattr(g, "modulo_atual", "onboarding"),
                    }
            except Exception as e:
                app.logger.warning(f"Falha ao reforçar perfil admin: {e}")

        if g.perfil is None:
            g.perfil = {
                "nome": g.user.get("name", g.user_email) if g.user else "Visitante",
                "usuario": g.user_email,
                "foto_url": None,
                "cargo": None,
                "perfil_acesso": None,
                "contexto": getattr(g, "modulo_atual", "onboarding"),
            }

        g.R2_CONFIGURED = app.config.get("R2_CONFIGURADO", False)
        g.PERFIS_COM_GESTAO = PERFIS_COM_GESTAO
        g.PERFIL_ADMIN = PERFIL_ADMIN

        # Carregar regras de gamificação (otimizado)
        g.gamification_rules = getattr(current_app, "gamification_rules", {})

    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith("/api"):
            return jsonify({"ok": False, "error": "Recurso não encontrado"}), 404

        # Renderiza template 404 em vez de redirecionar
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # Tenta identificar erros de construção de rota (BuildError)
        error_msg = str(e)
        if "Could not build url" in error_msg:
            app.logger.critical(
                f"ROUTING ERROR: {e} - Verifique se todos os endpoints estão registrados.", exc_info=True
            )
        else:
            app.logger.error(f"Erro 500: {e}", exc_info=True)

        if request.path.startswith("/api"):
            return jsonify({"ok": False, "error": "Erro interno do servidor"}), 500

        flash("Ocorreu um erro interno no servidor. Redirecionando para o Dashboard.", "error")
        return redirect(url_for("main.dashboard"))

    # Verificação de endpoints críticos na inicialização
    if app.config.get("DEBUG") or app.config.get("FLASK_ENV") == "development":
        with app.app_context():
            required_endpoints = ["auth.login", "auth.google_login", "auth.google_callback"]
            registered_rules = [rule.endpoint for rule in app.url_map.iter_rules()]
            missing = [ep for ep in required_endpoints if ep not in registered_rules]
            if missing:
                app.logger.warning(f"⚠️  ALERTA DE ROTA: Endpoints críticos ausentes: {missing}")
            else:
                app.logger.info("✅ Verificação de rotas de auth concluída com sucesso.")

            checklist_required = [
                "checklist.toggle_item",
                "checklist.add_comment",
                "checklist.get_comments",
                "checklist.send_comment_email",
                "checklist.delete_comment",
                "checklist.delete_item",
                "checklist.get_tree",
                "checklist.get_item_progress",
                "checklist.update_responsavel",
                "checklist.update_prazos",
                "checklist.get_responsavel_history",
                "checklist.get_prazos_history",
                "checklist.get_implantacao_comments",
            ]
            checklist_missing = [ep for ep in checklist_required if ep not in registered_rules]
            if checklist_missing:
                app.logger.warning(f"⚠️  ALERTA DE ROTA: Endpoints de checklist ausentes: {checklist_missing}")
            else:
                app.logger.info("✅ Verificação de rotas de checklist concluída com sucesso.")

    return app
