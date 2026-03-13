from flask import Blueprint

onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/onboarding")

from ...modules.onboarding.api import routes  # noqa: F401,E402 — registra as rotas no blueprint

