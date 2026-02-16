from flask import Blueprint

grandes_contas_bp = Blueprint("grandes_contas", __name__, url_prefix="/grandes-contas")

from ...modules.grandes_contas.api import routes
