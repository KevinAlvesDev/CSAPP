from flask import Blueprint, render_template, g, flash, redirect, url_for, request
from ..blueprints.auth import permission_required
from ..services import get_analytics_data
from ..db import query_db
from ..constants import PERFIS_COM_ANALYTICS, PERFIS_COM_GESTAO, JUSTIFICATIVAS_PARADA

analytics_bp = Blueprint('analytics', __name__)

def get_all_customer_success():
    """Busca a lista de todos os CS com nome e e-mail para o filtro."""
    return query_db("SELECT usuario, nome, perfil_acesso FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome", ())

@analytics_bp.route('/analytics')
@permission_required(PERFIS_COM_ANALYTICS)
def analytics_dashboard():
    """Rota para o dashboard gerencial de métricas e relatórios, com filtros."""
    
    user_perfil = g.perfil.get('perfil_acesso')
    
    # Captura parâmetros de filtro
    cs_email = request.args.get('cs_email', None)
    status_filter = request.args.get('status_filter', 'todas')
    start_date = request.args.get('start_date') or None
    end_date = request.args.get('end_date') or None
    
    # Se o usuário não for gerencial, ele só pode ver os próprios dados
    if user_perfil not in PERFIS_COM_GESTAO:
        cs_email = g.user_email
    
    try:
        # ATUALIZAÇÃO: Recebe 3 valores, incluindo a nova lista
        global_metrics, cs_metrics_list, implantacoes_paradas_detalhadas = get_analytics_data(
            target_cs_email=cs_email, 
            target_status=status_filter,
            start_date=start_date,
            end_date=end_date,
            target_tag=None # Tag filter é tratado no frontend agora
        )
        
        all_cs = get_all_customer_success()
        
        # Filtros de status para a UI
        status_options = [
            {'value': 'todas', 'label': 'Todas as Implantações'},
            {'value': 'andamento', 'label': 'Em Andamento'},
            {'value': 'atrasadas_status', 'label': 'Atrasadas (> 25d)'},
            {'value': 'futura', 'label': 'Futuras'},
            {'value': 'finalizada', 'label': 'Finalizadas'},
            {'value': 'parada', 'label': 'Paradas'}
        ]
        
        # Ordena a lista de CSs por nome
        cs_metrics_list.sort(key=lambda x: x['nome'])
        
        # ATUALIZAÇÃO: Ordena a nova lista de paradas por dias (mais tempo parado primeiro)
        implantacoes_paradas_detalhadas.sort(key=lambda x: x.get('parada_dias', 0), reverse=True)
        
        return render_template(
            'analytics.html',
            global_metrics=global_metrics,
            cs_metrics=cs_metrics_list,
            all_cs=all_cs,
            status_options=status_options,
            current_cs_email=cs_email,
            current_status_filter=status_filter,
            current_start_date=start_date,
            current_end_date=end_date,
            user_info=g.user,
            user_perfil=user_perfil,
            justificativas_parada=JUSTIFICATIVAS_PARADA,
            # ATUALIZAÇÃO: Passa a nova lista para o template
            implantacoes_paradas_detalhadas=implantacoes_paradas_detalhadas
        )
        
    except Exception as e:
        print(f"ERRO ao carregar dashboard de analytics: {e}")
        flash("Erro interno ao carregar os dados de relatórios.", "error")
        return redirect(url_for('main.dashboard'))