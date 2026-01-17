from flask import Blueprint

ongoing_bp = Blueprint("ongoing", __name__, url_prefix="/ongoing")

from . import routes
