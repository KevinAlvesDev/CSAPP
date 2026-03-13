import logging
import os
logger = logging.getLogger(__name__)

import click
from dotenv import find_dotenv, load_dotenv
from flask import Flask, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect

from .app_bootstrap import init_middleware, init_security, register_blueprints
from .config.logging_config import setup_logging
from .core.extensions import init_limiter, init_r2, oauth

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, static_folder="../../frontend/static", template_folder="../../frontend/templates")

    # Configuração do ProxyFix para lidar com HTTPS atrás de proxies (Render, Heroku, etc.)
    from werkzeug.middleware.proxy_fix import ProxyFix # type: ignore[import-not-found]
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1) # type: ignore[assignment]

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
                load_dotenv(str(_dotenv_path), override=True)
            else:
                load_dotenv(override=True)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        pass

    from .config import get_config

    app.config.from_object(get_config())

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
        if not app.config.get("DEBUG", False):
            raise
        app.logger.warning(f"Validação de secrets ignorada em dev: {e}", exc_info=True)

    # CSRF nunca expira (evita erro de token expirado em sessões longas)
    app.config["WTF_CSRF_TIME_LIMIT"] = None

    if test_config is not None:
        app.config.from_mapping(test_config)

    app.config["RATELIMIT_ENABLED"] = not app.config.get("DEBUG", False)

    from .common.i18n import get_translator

    translator = get_translator(app)

    @app.context_processor
    def inject_i18n():
        return {"t": translator, "lang": app.config.get("LANG", "pt")}

    @app.context_processor
    def inject_csp_nonce():
        return {"csp_nonce": lambda: getattr(g, "csp_nonce", "")}

    try:
        if app.config.get("DEBUG", False):
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
            os.environ.setdefault("AUTHLIB_INSECURE_TRANSPORT", "1")
        else:
            os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT", None)
            os.environ.pop("AUTHLIB_INSECURE_TRANSPORT", None)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        pass

    from .common.utils import format_date_br, format_date_iso_for_json
    from .constants import PERFIL_ADMIN, PERFIS_COM_GESTAO
    from .database import schema
    from .db import Session, init_db_session

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
    def get_static_version(filename: str) -> str:
        """Retorna a versão do arquivo estático para cache-busting."""
        try:
            if not app.static_folder:
                return APP_VERSION
                
            static_folder = Path(app.static_folder)
            file_path = static_folder / filename
            if file_path.exists():
                return str(int(file_path.stat().st_mtime))
        except Exception as exc:
            logger.exception("Unhandled exception", exc_info=True)
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
    init_db_session(app)

    try:
        from .config.sentry_config import init_sentry

        init_sentry(app)
    except Exception as e:
        app.logger.warning(f"Sentry não inicializado: {e}", exc_info=True)

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

    # Inicializar pool de conexões (com retry logic para conexões instáveis)
    db_initialized = init_connection_pool(app)

    if not db_initialized:
        app.logger.warning(
            "⚠️  Aplicação iniciando SEM conexão com banco de dados. "
            "Algumas funcionalidades críticas podem falhar."
        )

    # Ignore de typevar devido a Callable incompatível das versões antigas Flask vs current mypy
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        close_db_connection(exception)
        Session.remove()

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
        app.logger.warning(f"Sanitização de logs não ativada: {e}", exc_info=True)

    init_security(app)

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
        app.logger.warning(f"Cache Manager não inicializado: {e}", exc_info=True)

    # ================================================
    # SERVICE CONTAINER (Dependency Injection)
    # ================================================
    try:
        from .core.container import ServiceContainer
        from .core.service_registry import register_all_services

        container = ServiceContainer(app)
        register_all_services(app, container)
    except Exception as e:
        app.logger.warning(f"ServiceContainer não inicializado: {e}", exc_info=True)

    # ================================================
    # EVENT HANDLERS (reações a eventos de domínio)
    # ================================================
    try:
        from .core.event_handlers import register_event_handlers
        from .core.events import configure_event_bus_after_commit, event_bus

        register_event_handlers(event_bus)
        configure_event_bus_after_commit(app, event_bus)
    except Exception as e:
        app.logger.warning(f"Event Handlers não registrados: {e}", exc_info=True)

    # Monitoramento de performance
    init_middleware(app)

    try:
        app.logger.info("🗄️  DATABASE MODE: PostgreSQL (Production)")

        # Inicialização do schema usando a conexão PostgreSQL padrão
        try:
            with app.app_context():
                schema.init_db()
        except Exception as e:
            app.logger.warning(f"Falha ao rodar schema em DB remota: {e}", exc_info=True)

    except Exception as e_dbinit:
        app.logger.warning(f"Falha na inicialização do banco: {e_dbinit}", exc_info=True)

    # ================================================
    # CACHE WARMING (moved after DB init)
    # ================================================
    try:
        from .common.context_profiles import ensure_context_profile_schema

        with app.app_context():
            ensure_context_profile_schema()
    except Exception as e:
        app.logger.warning(f"Falha ao garantir schema contextual de perfis: {e}", exc_info=True)

    try:
        from .config.cache_warming import warm_cache

        with app.app_context():
            warm_cache(app)
    except Exception as e:
        app.logger.warning(f"Cache Warming falhou: {e}", exc_info=True)



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
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        pass

    register_blueprints(app, csrf)

    @app.after_request
    def _force_utf8(resp):
        try:
            ct = resp.headers.get("Content-Type", "")
            if ct.startswith("text/html") and "charset" not in ct.lower():
                resp.headers["Content-Type"] = f"{ct}; charset=utf-8"
        except Exception:
            pass
        return resp

    @app.cli.command("backup-db")
    def backup_db_command():
        """Gera um backup do banco e imprime o caminho do arquivo."""
        try:
            from .modules.management.application.management_service import perform_backup

            result = perform_backup()
            click.echo(result.get("backup_file"))
        except Exception as e:
            logger.exception("Unhandled exception", exc_info=True)
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
        from .constants import MASTER_ADMIN_EMAIL

        # Carregar usuário da sessão PRIMEIRO
        g.user_email = session.get("user", {}).get("email")
        g.user = session.get("user")



        g.perfil = None
        if g.user_email:
            try:
                from .common.context_profiles import get_contextual_profile

                g.perfil = get_contextual_profile(g.user_email, getattr(g, "modulo_atual", None))
            except Exception as e:
                # Se a tabela não existir ainda, criar perfil básico
                app.logger.warning(f"Falha ao buscar perfil para {g.user_email}: {e}", exc_info=True)
                g.perfil = None

        # Fallback para perfil admin para conta MASTER_ADMIN_EMAIL (apenas se configurado via env)
        if MASTER_ADMIN_EMAIL and g.user_email and g.user_email == MASTER_ADMIN_EMAIL:
            try:
                if not g.perfil or g.perfil.get("perfil_acesso") != PERFIL_ADMIN:
                    from .modules.auth.application.auth_service import (
                        sync_user_profile_service,
                        update_user_role_service,
                    )

                    # Cria perfil se necessário e marca como admin
                    sync_user_profile_service(g.user_email, g.user.get("name", "Administrador"), "system|enforce")
                    update_user_role_service(g.user_email, PERFIL_ADMIN)

                    from .common.context_profiles import get_contextual_profile
                    g.perfil = get_contextual_profile(g.user_email, getattr(g, "modulo_atual", None))
            except Exception as e:
                app.logger.warning(f"Falha ao reforçar perfil admin: {e}", exc_info=True)

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
        from .common.context_navigation import redirect_to_current_dashboard
        return redirect_to_current_dashboard()

    from .common.exceptions import CSAPPException, ValidationError, ResourceNotFoundError, AuthenticationError, AuthorizationError

    @app.errorhandler(CSAPPException)
    def handle_csapp_exception(e):
        """Manipulador global para exceções de domínio da aplicação."""
        # Se for uma exceção de validação ou regra de negócio, logar como warning
        # Erros técnicos (DatabaseError, ExternalServiceError) logar como error
        log_level = "warning"
        status_code = 400
        
        if isinstance(e, (ValidationError, ResourceNotFoundError)):
            status_code = 404 if isinstance(e, ResourceNotFoundError) else 400
        elif isinstance(e, (AuthenticationError, AuthorizationError)):
            status_code = 401 if isinstance(e, AuthenticationError) else 403
        else:
            log_level = "error"
            status_code = 500

        getattr(app.logger, log_level)(f"CSAPP Exception [{e.__class__.__name__}]: {e.message} - Details: {e.details}")

        if request.path.startswith("/api") or request.is_json:
            return jsonify({
                "ok": False, 
                "error": e.message,
                "type": e.__class__.__name__,
                "details": e.details
            }), status_code

        flash(e.message, "error")
        # Tenta redirecionar para a página anterior ou dashboard
        target = request.referrer or url_for("main.dashboard")
        return redirect(target)

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
