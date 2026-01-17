from flask import render_template

from ..auth import login_required
from . import core_bp


@core_bp.route("/modules")
@login_required
def modules_selection():
    """
    Tela de seleção de módulos (Onboarding, Ongoing, Grandes Contas).
    """
    return render_template("pages/modules_selection.html")
