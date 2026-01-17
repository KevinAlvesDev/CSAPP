from flask import render_template

from ..auth import login_required
from . import ongoing_bp


@ongoing_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("pages/ongoing/dashboard.html")
