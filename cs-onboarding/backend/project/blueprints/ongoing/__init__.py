from flask import Blueprint

ongoing_bp = Blueprint("ongoing", __name__, url_prefix="/ongoing")

from ...modules.ongoing.api import routes  # noqa: F401,E402 — registra as rotas no blueprint
