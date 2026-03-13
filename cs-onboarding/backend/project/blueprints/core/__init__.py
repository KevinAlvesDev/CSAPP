from flask import Blueprint

core_bp = Blueprint("core", __name__)

from . import routes  # noqa: F401,E402 — registra as rotas no blueprint
