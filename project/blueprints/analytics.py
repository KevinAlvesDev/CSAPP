from flask import Blueprint, render_template, g, flash, redirect, url_for, request
from ..blueprints.auth import permission_required
from ..services import get_analytics_data
from ..db import query_db
from ..constants import PERFIS_COM_ANALYTICS, PERFIS_COM_GESTAO

analytics_bp = Blueprint('analytics', __name__)

def get_all_customer_success():
    """Busca a lista de todos os CS com nome e e-mail para o filtro."""
    # Garante que a query retorne uma lista vazia em vez de None se falhar
    result = query_db("SELECT usuario, nome, perfil_acesso FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome", ())
    return result if result is not None else []

@analytics_bp.route('/analytics')
@permission_required(PERFIS_COM_ANALYTICS)
def analytics_dashboard():
    """Rota para o dashboard gerencial de métricas e relatórios, com filtros."""
    
    user_perfil = g.perfil.get('perfil_acesso')
    
    # --- Filtros Principais (Gráficos e Listas de Implantações) ---
    cs_email = request.args.get('cs_email', None)
    status_filter = request.args.get('status_filter', 'todas')
    start_date = request.args.get('start_date') or None
    end_date = request.args.get('end_date') or None
    
    # --- INÍCIO AJUSTE 2: Captura dos Filtros de Produtividade ---
    task_cs_email = request.args.get('task_cs_email', None)
    task_start_date = request.args.get('task_start_date') or None
    task_end_date = request.args.get('task_end_date') or None
    # --- FIM AJUSTE 2 ---
    
    # Se o usuário não for gerencial, ele só pode ver os próprios dados
    if user_perfil not in PERFIS_COM_GESTAO:
        cs_email = g.user_email
        task_cs_email = g.user_email # Restringe o filtro de tarefas a ele mesmo também
    
    try:
        # ATUALIZAÇÃO: Passa os novos filtros para a função de serviço
        analytics_data = get_analytics_data(
            target_cs_email=cs_email, 
            target_status=status_filter,
            start_date=start_date,
            end_date=end_date,
            target_tag=None,
            # --- INÍCIO AJUSTE 2 ---
            task_cs_email=task_cs_email,
            task_start_date=task_start_date,
            task_end_date=task_end_date
            # --- FIM AJUSTE 2 ---
        )
        
        all_cs = get_all_customer_success()
        
        # Filtros de status para a UI
        status_options = [
            {'value': 'todas', 'label': 'Todas as Implantações'},
            {'value': 'nova', 'label': 'Novas'},
            {'value': 'andamento', 'label': 'Em Andamento'},
            {'value': 'atrasadas_status', 'label': 'Atrasadas (> 25d)'},
            {'value': 'futura', 'label': 'Futuras'},
            {'value': 'finalizada', 'label': 'Finalizadas'},
            {'value': 'parada', 'label': 'Paradas'}
        ]
        
        # --- INÍCIO AJUSTE 2: Define os valores atuais dos filtros de tarefas ---
        # Usa os valores recebidos da função de serviço (que contêm os defaults)
        current_task_cs_email = task_cs_email
        current_task_start_date = task_start_date or analytics_data.get('default_task_start_date')
        current_task_end_date = task_end_date or analytics_data.get('default_task_end_date')
        # --- FIM AJUSTE 2 ---

        return render_template(
            'analytics.html',
            # Dados principais
            kpi_cards=analytics_data.get('kpi_cards', {}),
            implantacoes_lista_detalhada=analytics_data.get('implantacoes_lista_detalhada', []),
            chart_data=analytics_data.get('chart_data', {}),
            implantacoes_paradas_lista=analytics_data.get('implantacoes_paradas_lista', []),
            
            # --- INÍCIO AJUSTE 2: Passa novos dados para o template ---
            task_summary_data=analytics_data.get('task_summary_data', []),
            current_task_cs_email=current_task_cs_email,
            current_task_start_date=current_task_start_date,
            current_task_end_date=current_task_end_date,
            # --- FIM AJUSTE 2 ---

            # Filtros e dados antigos
            all_cs=all_cs,
            status_options=status_options,
            current_cs_email=cs_email,
            current_status_filter=status_filter,
            current_start_date=start_date,
            current_end_date=end_date,
            user_info=g.user,
            user_perfil=user_perfil
        )
        
    except Exception as e:
        print(f"ERRO ao carregar dashboard de analytics: {e}")
        flash(f"Erro interno ao carregar os dados de relatórios: {e}", "error")
        return redirect(url_for('main.dashboard'))