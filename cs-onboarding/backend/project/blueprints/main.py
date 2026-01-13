import os

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from ..blueprints.auth import login_required
from ..common.validation import ValidationError, sanitize_string, validate_integer
from ..constants import (
    CARGOS_RESPONSAVEL,
    FORMAS_PAGAMENTO,
    HORARIOS_FUNCIONAMENTO,
    MODALIDADES_LIST,
    NIVEIS_RECEITA,
    PERFIS_COM_CRIACAO,
    PERFIS_COM_GESTAO,
    RECORRENCIA_USADA,
    SEGUIMENTOS_LIST,
    SIM_NAO_OPTIONS,
    SISTEMAS_ANTERIORES,
    TIPOS_PLANOS,
)
from ..db import query_db
from ..domain.dashboard_service import get_dashboard_data, get_tags_metrics
from ..domain.implantacao_service import get_implantacao_details

main_bp = Blueprint('main', __name__)


def _get_all_cs_users():
    """Busca todos os usuários com perfil que podem receber implantações."""
    result = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")
    return result if result is not None else []


@main_bp.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('core.modules_selection'))
    auth0_enabled = current_app.config.get('AUTH0_ENABLED', True)
    try:
        session.pop('_flashes', None)
    except Exception:
        pass
    return render_template(
        'auth/login.html',
        auth0_enabled=auth0_enabled,
        use_custom_auth=not auth0_enabled
    )


@main_bp.route('/privacy')
def privacy():
    """Página de Política de Privacidade (pública - necessária para verificação Google OAuth)."""
    return render_template('legal/privacy.html')


@main_bp.route('/terms')
def terms():
    """Página de Termos de Serviço (pública - necessária para verificação Google OAuth)."""
    return render_template('legal/terms.html')


@main_bp.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    base_dir = os.path.join(os.path.dirname(current_app.root_path), 'uploads')
    return send_from_directory(base_dir, filename)



