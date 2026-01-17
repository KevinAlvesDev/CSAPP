import os

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    send_from_directory,
    session,
    url_for,
)

from ..blueprints.auth import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    if "user" in session:
        return redirect(url_for("core.modules_selection"))
    auth0_enabled = current_app.config.get("AUTH0_ENABLED", True)
    try:
        session.pop("_flashes", None)
    except Exception:
        pass
    return render_template("auth/login.html", auth0_enabled=auth0_enabled, use_custom_auth=not auth0_enabled)


@main_bp.route("/privacy")
def privacy():
    """Página de Política de Privacidade (pública - necessária para verificação Google OAuth)."""
    return render_template("legal/privacy.html")


@main_bp.route("/terms")
def terms():
    """Página de Termos de Serviço (pública - necessária para verificação Google OAuth)."""
    return render_template("legal/terms.html")


@main_bp.route("/uploads/<path:filename>")
@login_required
def serve_upload(filename):
    base_dir = os.path.join(os.path.dirname(current_app.root_path), "uploads")
    return send_from_directory(base_dir, filename)
