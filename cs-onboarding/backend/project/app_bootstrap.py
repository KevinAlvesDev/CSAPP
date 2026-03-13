import logging
from flask import Flask
from flask_wtf.csrf import CSRFProtect
logger = logging.getLogger(__name__)


def _diagnostic_smtp_enabled(app: Flask) -> bool:
    if app.config.get("DEBUG", False):
        return True
    return bool(app.config.get("ENABLE_DIAGNOSTIC_SMTP", False))


def init_security(app: Flask) -> None:
    from .security.middleware import configure_cors, init_security_headers

    init_security_headers(app)
    configure_cors(app)


def init_middleware(app: Flask) -> None:
    from .monitoring.performance_middleware import init_performance_monitoring

    init_performance_monitoring(app)


def register_blueprints(app: Flask, csrf: CSRFProtect) -> None:
    from .blueprints.api import api_bp
    from .blueprints.api_docs import api_docs_bp
    from .blueprints.api_planos import api_planos_bp
    from .blueprints.api_v1 import api_v1_bp
    from .blueprints.auth import auth_bp
    from .blueprints.checklist_api import checklist_bp
    from .blueprints.checklist_finalizacao_bp import checklist_finalizacao_bp
    from .blueprints.gamification import gamification_bp
    from .blueprints.health import health_bp
    from .blueprints.main import main_bp
    from .blueprints.management import management_bp
    from .blueprints.perfis_bp import perfis_bp
    from .blueprints.profile import profile_bp
    from .blueprints.risc_bp import risc_bp
    from .blueprints.upload import upload_bp
    from .modules.analytics.api.analytics import analytics_bp
    from .modules.dashboard.api.agenda import agenda_bp
    from .modules.planos.api.planos_bp import planos_bp
    from .modules.chat.api.routes import chat_api_bp

    diagnostic_bp = None
    if _diagnostic_smtp_enabled(app):
        from .blueprints.diagnostic_smtp import diagnostic_bp as _diagnostic_bp

        diagnostic_bp = _diagnostic_bp

    try:
        csrf_exempt_blueprints = [
            api_v1_bp,
            health_bp,
            api_docs_bp,
            # risc_bp: webhook externo do Google (RISC) — não pode enviar token CSRF; usa JWT próprio
            risc_bp,
            checklist_finalizacao_bp,
            chat_api_bp,
        ]
        if diagnostic_bp is not None:
            csrf_exempt_blueprints.append(diagnostic_bp)
        for bp in csrf_exempt_blueprints:
            csrf.exempt(bp)
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        pass

    for bp, kwargs in [
        (main_bp, {}),
        (auth_bp, {}),
        (api_bp, {}),
        (api_v1_bp, {}),
        (api_planos_bp, {}),
    ]:
        app.register_blueprint(bp, **kwargs)

    from .modules.onboarding.api.actions import onboarding_actions_bp

    module_blueprints = [
        (onboarding_actions_bp, {}),
        (profile_bp, {}),
        (management_bp, {}),
        (analytics_bp, {}),
        (gamification_bp, {}),
        (agenda_bp, {}),
        (health_bp, {}),
        (api_docs_bp, {}),
        (planos_bp, {}),
        (checklist_bp, {}),
        (perfis_bp, {}),
        (upload_bp, {}),
        (risc_bp, {}),
        (checklist_finalizacao_bp, {}),
        (chat_api_bp, {}),
    ]
    if diagnostic_bp is not None:
        module_blueprints.append((diagnostic_bp, {}))
    for bp, kwargs in module_blueprints:
        app.register_blueprint(bp, **kwargs)

    from .blueprints.core import core_bp
    from .blueprints.config_api import config_api
    from .blueprints.onboarding import onboarding_bp
    from .blueprints.ongoing import ongoing_bp
    from .blueprints.grandes_contas import grandes_contas_bp
    from .modules.ongoing.api.actions import ongoing_actions_bp
    from .modules.grandes_contas.api.actions import grandes_contas_actions_bp

    app.register_blueprint(core_bp)
    app.register_blueprint(config_api)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(ongoing_bp)
    app.register_blueprint(grandes_contas_bp)
    app.register_blueprint(ongoing_actions_bp, url_prefix="/ongoing/actions")
    app.register_blueprint(grandes_contas_actions_bp, url_prefix="/grandes-contas/actions")

    try:
        from .modules.gamification.application.gamification_service import _get_all_gamification_rules_grouped

        with app.app_context():
            app.gamification_rules = _get_all_gamification_rules_grouped()  # type: ignore[attr-defined]
    except Exception as e:
        app.logger.error(f"Falha ao carregar regras de gamificação na inicialização: {e}", exc_info=True)
        app.gamification_rules = {}  # type: ignore[attr-defined]
