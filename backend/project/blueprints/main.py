import os
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, session,
    current_app, send_from_directory, jsonify\
)
\
\

\
from ..blueprints.auth import login_required, permission_required 
from ..db import query_db, execute_db, logar_timeline, get_db_connection                                   
\
\
from ..domain.dashboard_service import get_dashboard_data
from ..domain.implantacao_service import get_implantacao_details
\
from ..constants import (
\
\
    CARGOS_RESPONSAVEL, PERFIS_COM_CRIACAO,
    NIVEIS_RECEITA, SEGUIMENTOS_LIST, TIPOS_PLANOS, MODALIDADES_LIST,
    HORARIOS_FUNCIONAMENTO, FORMAS_PAGAMENTO, SISTEMAS_ANTERIORES,
    RECORRENCIA_USADA,
    NAO_DEFINIDO_BOOL,
    SIM_NAO_OPTIONS,
    PERFIS_COM_GESTAO
)
\
from .. import utils
from ..validation import validate_integer, sanitize_string, ValidationError
from ..cache_config import cache

main_bp = Blueprint('main', __name__)

\
\
\
def _get_all_cs_users():
    """Busca todos os usuários com perfil que podem receber implantações."""
    \
    result = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")
    return result if result is not None else []

\

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
        use_custom_auth=not auth0_enabled\
    )

@main_bp.route('/dashboard')
@login_required
def dashboard():
\
    
    user_email = g.user_email  
    user_info = g.user  
    
    perfil_acesso = g.perfil.get('perfil_acesso') if g.get('perfil') else None
    is_manager = perfil_acesso in PERFIS_COM_GESTAO
    
        \
    current_cs_filter = None
    try:
        cs_filter_param = request.args.get('cs_filter', None)
        if cs_filter_param and is_manager:
            current_cs_filter = sanitize_string(cs_filter_param, max_length=100)
    except ValidationError as e:
        flash(f"Filtro inválido: {str(e)}", "warning")
        current_cs_filter = None

    try:
        \
\
        if current_cs_filter is None and cache:
            \
            cache_key = f'dashboard_data_{user_email}'
            cached_result = cache.get(cache_key)

            if cached_result:
                dashboard_data, metrics = cached_result
            else:
                dashboard_data, metrics = get_dashboard_data(user_email, filtered_cs_email=None)
                \
                cache.set(cache_key, (dashboard_data, metrics), timeout=300)
        else:
            \
            dashboard_data, metrics = get_dashboard_data(user_email, filtered_cs_email=current_cs_filter)
        
        perfil_data = g.perfil if g.perfil else {}  
        default_metrics = { 'nome': user_info.get('name', user_email), 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'progresso_medio_carteira': 0, 'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0, 'implantacoes_sem_previsao': 0, 'total_valor_sem_previsao': 0.0 }
        final_metrics = {**default_metrics, **perfil_data, **metrics}
        
        all_cs_users = _get_all_cs_users()

            return render_template(
                'dashboard.html',\
                user_info=user_info, 
                metrics=final_metrics, 
                implantacoes_andamento=dashboard_data.get('andamento', []), 
                implantacoes_novas=dashboard_data.get('novas', []),\
                implantacoes_futuras=dashboard_data.get('futuras', []), 
                implantacoes_sem_previsao=dashboard_data.get('sem_previsao', []), 
                implantacoes_finalizadas=dashboard_data.get('finalizadas', []), 
                implantacoes_paradas=dashboard_data.get('paradas', []), 
                implantacoes_atrasadas=dashboard_data.get('atrasadas', []), 
            cargos_responsavel=CARGOS_RESPONSAVEL,\
            PERFIS_COM_CRIACAO=PERFIS_COM_CRIACAO, \
            NIVEIS_RECEITA=NIVEIS_RECEITA,\
            SEGUIMENTOS_LIST=SEGUIMENTOS_LIST,\
            TIPOS_PLANOS=TIPOS_PLANOS,\
            MODALIDADES_LIST=MODALIDADES_LIST,\
            HORARIOS_FUNCIONAMENTO=HORARIOS_FUNCIONAMENTO,\
            FORMAS_PAGAMENTO=FORMAS_PAGAMENTO,\
            SISTEMAS_ANTERIORES=SISTEMAS_ANTERIORES,\
            RECORRENCIA_USADA=RECORRENCIA_USADA,\
            SIM_NAO_OPTIONS=SIM_NAO_OPTIONS,\
            all_cs_users=all_cs_users,\
            
            is_manager=is_manager,
            current_cs_filter=current_cs_filter
        )
        
    except Exception as e:
        print(f"ERRO ao carregar dashboard para {user_email}: {e}")
        flash("Erro ao carregar dados do dashboard.", "error")
        
        perfil_acesso_erro = g.perfil.get('perfil_acesso') if g.get('perfil') else None
        is_manager_erro = perfil_acesso_erro in PERFIS_COM_GESTAO
        current_cs_filter_erro = request.args.get('cs_filter', None)
        if not is_manager_erro:
            current_cs_filter_erro = None

        return render_template('dashboard.html', user_info=user_info, metrics={}, 
                             implantacoes_andamento=[], implantacoes_novas=[], 
                             implantacoes_futuras=[], implantacoes_sem_previsao=[], implantacoes_finalizadas=[], 
                             implantacoes_paradas=[], implantacoes_atrasadas=[], 
                             cargos_responsavel=CARGOS_RESPONSAVEL, error="Falha ao carregar dados.", 
                             all_cs_users=[], PERFIS_COM_CRIACAO=PERFIS_COM_CRIACAO,
                             is_manager=is_manager_erro, current_cs_filter=current_cs_filter_erro)  

@main_bp.route('/implantacao/<int:impl_id>')
@login_required
def ver_implantacao(impl_id):
    \
    try:
        impl_id = validate_integer(impl_id, min_value=1)
    except ValidationError as e:
        flash(f"ID de implantação inválido: {str(e)}", "error")
        return redirect(url_for('main.dashboard'))
    try:
        \
        context_data = get_implantacao_details(
            impl_id=impl_id,
            usuario_cs_email=g.user_email,
            user_perfil=g.perfil
        )
        
                \
\
        return render_template( 
            'implantacao_detalhes.html', 
            **context_data
        )
        
    except ValueError as e:
        \
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        \
        from ..logging_config import get_logger
        logger = get_logger('main')
        logger.error(f"Erro ao carregar detalhes da implantação ID {impl_id}: {e}", exc_info=True)
        flash("Erro ao carregar detalhes da implantação.", "error")
        return redirect(url_for('main.dashboard'))


