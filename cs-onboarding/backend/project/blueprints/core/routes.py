from flask import g, render_template

from ...common.context_profiles import get_contextual_profile
from ...constants import PERFIL_SEM_ACESSO
from ..auth import login_required
from . import core_bp

VALID_CONTEXTS = ("onboarding", "ongoing", "grandes_contas")


@core_bp.route("/modules")
@login_required
def modules_selection():
    """
    Tela de seleção de módulos (Onboarding, Ongoing, Grandes Contas).
    """
    accessible = []
    for ctx in VALID_CONTEXTS:
        perfil = get_contextual_profile(g.user_email, ctx)
        if perfil and perfil.get("perfil_acesso") not in (None, PERFIL_SEM_ACESSO):
            accessible.append(ctx)
    return render_template("pages/modules_selection.html", accessible_contexts=accessible)
