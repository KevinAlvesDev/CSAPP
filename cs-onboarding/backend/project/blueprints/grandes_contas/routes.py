from flask import render_template

from ..auth import login_required
from . import grandes_contas_bp


@grandes_contas_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("pages/grandes_contas/dashboard.html")
