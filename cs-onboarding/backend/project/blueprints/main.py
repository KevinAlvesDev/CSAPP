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
from ..domain.dashboard_service import get_dashboard_data
from ..domain.implantacao_service import get_implantacao_details

main_bp = Blueprint('main', __name__)


def _get_all_cs_users():
    """Busca todos os usuários com perfil que podem receber implantações."""
    result = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")
    return result if result is not None else []


@main_bp.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('main.dashboard'))
    auth0_enabled = current_app.config.get('AUTH0_ENABLED', True)
    try:
        session.pop('_flashes', None)
    except Exception:
        pass
    return render_template(
        'login.html',
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


@main_bp.route('/dashboard')
@login_required
def dashboard():
    user_email = g.user_email
    user_info = g.user

    perfil_acesso = g.perfil.get('perfil_acesso') if g.get('perfil') else None
    
    # Garantia explícita: Implantador visualiza apenas sua carteira (sem filtro de dashboard)
    if perfil_acesso == 'Implantador':
        is_manager = False
    else:
        is_manager = perfil_acesso in PERFIS_COM_GESTAO

    current_cs_filter = None
    sort_days = None
    try:
        cs_filter_param = request.args.get('cs_filter', None)
        if cs_filter_param and is_manager:
            current_cs_filter = sanitize_string(cs_filter_param, max_length=100)
        sort_days_param = request.args.get('sort_days', None)
        if sort_days_param:
            sort_days = sanitize_string(sort_days_param, max_length=4)
    except ValidationError as e:
        flash(f"Filtro inválido: {str(e)}", "warning")
        current_cs_filter = None
        sort_days = None

    try:
        dashboard_data, metrics = get_dashboard_data(
            user_email,
            filtered_cs_email=current_cs_filter,
            use_cache=False
        )

        if sort_days in ['asc', 'desc']:
            andamento_list = dashboard_data.get('andamento', [])
            try:
                andamento_list_sorted = sorted(
                    andamento_list,
                    key=lambda x: (x.get('dias_passados') or 0),
                    reverse=(sort_days == 'desc')
                )
                dashboard_data['andamento'] = andamento_list_sorted
            except Exception:
                pass

        perfil_data = g.perfil if g.perfil else {}
        default_metrics = {
            'nome': user_info.get('name', user_email), 'impl_andamento': 0, 'impl_finalizadas': 0,
            'impl_paradas': 0, 'progresso_medio_carteira': 0, 'impl_andamento_total': 0,
            'implantacoes_futuras': 0, 'implantacoes_sem_previsao': 0,
            'total_valor_sem_previsao': 0.0
        }
        final_metrics = {**default_metrics, **perfil_data}
        final_metrics.update(metrics)
        final_metrics['impl_andamento_total'] = len(dashboard_data.get('andamento', []))

        all_cs_users = _get_all_cs_users()

        return render_template(
            'dashboard.html',
            user_info=user_info,
            metrics=final_metrics,
            implantacoes_andamento=dashboard_data.get('andamento', []),
            implantacoes_novas=dashboard_data.get('novas', []),
            implantacoes_futuras=dashboard_data.get('futuras', []),
            implantacoes_sem_previsao=dashboard_data.get('sem_previsao', []),
            implantacoes_finalizadas=dashboard_data.get('finalizadas', []),
            implantacoes_paradas=dashboard_data.get('paradas', []),
            implantacoes_canceladas=dashboard_data.get('canceladas', []),
            cargos_responsavel=CARGOS_RESPONSAVEL,
            PERFIS_COM_CRIACAO=PERFIS_COM_CRIACAO,
            NIVEIS_RECEITA=NIVEIS_RECEITA,
            SEGUIMENTOS_LIST=SEGUIMENTOS_LIST,
            TIPOS_PLANOS=TIPOS_PLANOS,
            MODALIDADES_LIST=MODALIDADES_LIST,
            HORARIOS_FUNCIONAMENTO=HORARIOS_FUNCIONAMENTO,
            FORMAS_PAGAMENTO=FORMAS_PAGAMENTO,
            SISTEMAS_ANTERIORES=SISTEMAS_ANTERIORES,
            RECORRENCIA_USADA=RECORRENCIA_USADA,
            SIM_NAO_OPTIONS=SIM_NAO_OPTIONS,
            all_cs_users=all_cs_users,
            is_manager=is_manager,
            current_cs_filter=current_cs_filter,
            sort_days=sort_days
        )

    except Exception:
        flash("Erro ao carregar dados do dashboard.", "error")

        perfil_acesso_erro = g.perfil.get('perfil_acesso') if g.get('perfil') else None
        is_manager_erro = perfil_acesso_erro in PERFIS_COM_GESTAO
        current_cs_filter_erro = request.args.get('cs_filter', None)
        if not is_manager_erro:
            current_cs_filter_erro = None

        return render_template('dashboard.html', user_info=user_info, metrics={},
                               implantacoes_andamento=[], implantacoes_novas=[],
                               implantacoes_futuras=[], implantacoes_sem_previsao=[], implantacoes_finalizadas=[],
                               implantacoes_paradas=[], implantacoes_canceladas=[],
                               cargos_responsavel=CARGOS_RESPONSAVEL, error="Falha ao carregar dados.",
                               all_cs_users=[], PERFIS_COM_CRIACAO=PERFIS_COM_CRIACAO,
                               is_manager=is_manager_erro, current_cs_filter=current_cs_filter_erro)


@main_bp.route('/implantacao/<int:impl_id>')
@login_required
def ver_implantacao(impl_id):
    from ..config.logging_config import get_logger
    logger = get_logger('main')

    logger.info(f"Tentando acessar implantação ID {impl_id} - Usuário: {g.user_email}")

    try:
        impl_id = validate_integer(impl_id, min_value=1)
        logger.info(f"ID validado: {impl_id}")
    except ValidationError as e:
        logger.error(f"ID de implantação inválido: {str(e)}")
        flash(f"ID de implantação inválido: {str(e)}", "error")
        return redirect(url_for('main.dashboard'))

    try:
        logger.info(f"Chamando get_implantacao_details para ID {impl_id}")
        user_perfil = g.perfil if hasattr(g, 'perfil') and g.perfil else {}
        context_data = get_implantacao_details(
            impl_id=impl_id,
            usuario_cs_email=g.user_email,
            user_perfil=user_perfil
        )
        logger.info(f"Dados da implantação {impl_id} obtidos com sucesso")

        return render_template(
            'implantacao_detalhes.html',
            **context_data
        )

    except ValueError as e:
        logger.warning(f"Acesso negado à implantação {impl_id}: {str(e)}")
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Erro ao carregar detalhes da implantação ID {impl_id}: {e}\n{error_trace}")
        flash(f"Erro ao carregar detalhes da implantação: {str(e)}", "error")
        return redirect(url_for('main.dashboard'))
