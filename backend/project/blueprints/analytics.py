from flask import Blueprint, render_template, g, flash, redirect, url_for, request, jsonify
from ..blueprints.auth import permission_required
# --- INÍCIO DA ALTERAÇÃO (ETAPA 2) ---
from ..domain.analytics_service import get_analytics_data
from ..domain.analytics_service import (
    get_implants_by_day,
    get_funnel_counts,
    get_gamification_rank,
)
# --- FIM DA ALTERAÇÃO ---
from ..db import query_db
from ..constants import PERFIS_COM_ANALYTICS, PERFIS_COM_GESTAO
from ..validation import validate_email, sanitize_string, validate_date, ValidationError

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
    cs_email = None
    status_filter = 'todas'
    start_date = None
    end_date = None
    
    try:
        # Valida e sanitiza o email do CS
        cs_email_param = request.args.get('cs_email')
        if cs_email_param:
            cs_email = validate_email(cs_email_param)
            
        # Valida e sanitiza o filtro de status
        status_filter_param = request.args.get('status_filter', 'todas')
        status_filter = sanitize_string(status_filter_param, max_length=20)
        
        # Valida as datas
        start_date_param = request.args.get('start_date')
        if start_date_param:
            start_date = validate_date(start_date_param)
            
        end_date_param = request.args.get('end_date')
        if end_date_param:
            end_date = validate_date(end_date_param)
            
    except ValidationError as e:
        flash(f'Erro nos filtros: {str(e)}', 'warning')
        return redirect(url_for('analytics.analytics_dashboard'))
    
    # --- INÍCIO AJUSTE 2: Captura dos Filtros de Produtividade ---
    task_cs_email = None
    task_start_date = None
    task_end_date = None
    
    try:
        # Valida e sanitiza o email do CS para tarefas
        task_cs_email_param = request.args.get('task_cs_email')
        if task_cs_email_param:
            task_cs_email = validate_email(task_cs_email_param)
            
        # Valida as datas das tarefas
        task_start_date_param = request.args.get('task_start_date')
        if task_start_date_param:
            task_start_date = validate_date(task_start_date_param)
            
        task_end_date_param = request.args.get('task_end_date')
        if task_end_date_param:
            task_end_date = validate_date(task_end_date_param)
            
    except ValidationError as e:
        flash(f'Erro nos filtros de tarefas: {str(e)}', 'warning')
        return redirect(url_for('analytics.analytics_dashboard'))
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
            {'value': 'parada', 'label': 'Paradas'},
            # NOVA OPÇÃO DE FILTRO
            {'value': 'cancelada', 'label': 'Canceladas'}
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
            modules_implantacao_lista=analytics_data.get('modules_implantacao_lista', []),
            chart_data=analytics_data.get('chart_data', {}),
            implantacoes_paradas_lista=analytics_data.get('implantacoes_paradas_lista', []),
            implantacoes_canceladas_lista=analytics_data.get('implantacoes_canceladas_lista', []),
            
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

# --- NOVAS ROTAS: API de Gráficos ---

@analytics_bp.route('/analytics/implants_by_day')
@permission_required(PERFIS_COM_ANALYTICS)
def api_implants_by_day():
    """Retorna contagem de implantações finalizadas por dia no período."""
    try:
        cs_email = request.args.get('cs_email')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if cs_email:
            cs_email = validate_email(cs_email)
        if start_date:
            start_date = validate_date(start_date)
        if end_date:
            end_date = validate_date(end_date)

        # Usuários sem perfil gerencial só podem consultar seus dados
        if g.perfil.get('perfil_acesso') not in PERFIS_COM_GESTAO:
            cs_email = g.user_email

        payload = get_implants_by_day(start_date=start_date, end_date=end_date, cs_email=cs_email)
        return jsonify({ 'ok': True, **payload })
    except ValidationError as e:
        return jsonify({ 'ok': False, 'error': f'Parâmetro inválido: {str(e)}' }), 400
    except Exception as e:
        return jsonify({ 'ok': False, 'error': f'Erro interno: {str(e)}' }), 500


@analytics_bp.route('/analytics/funnel')
@permission_required(PERFIS_COM_ANALYTICS)
def api_funnel():
    """Retorna contagem por status para funil em período opcional."""
    try:
        cs_email = request.args.get('cs_email')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if cs_email:
            cs_email = validate_email(cs_email)
        if start_date:
            start_date = validate_date(start_date)
        if end_date:
            end_date = validate_date(end_date)

        if g.perfil.get('perfil_acesso') not in PERFIS_COM_GESTAO:
            cs_email = g.user_email

        payload = get_funnel_counts(start_date=start_date, end_date=end_date, cs_email=cs_email)
        return jsonify({ 'ok': True, **payload })
    except ValidationError as e:
        return jsonify({ 'ok': False, 'error': f'Parâmetro inválido: {str(e)}' }), 400
    except Exception as e:
        return jsonify({ 'ok': False, 'error': f'Erro interno: {str(e)}' }), 500


@analytics_bp.route('/analytics/gamification_rank')
@permission_required(PERFIS_COM_ANALYTICS)
def api_gamification_rank():
    """Retorna ranking de gamificação por mês/ano."""
    try:
        month = request.args.get('month')
        year = request.args.get('year')

        # Valida números simples
        if month:
            month = int(sanitize_string(month, max_length=2))
        if year:
            year = int(sanitize_string(year, max_length=4))

        payload = get_gamification_rank(month=month, year=year)
        return jsonify({ 'ok': True, **payload })
    except ValueError:
        return jsonify({ 'ok': False, 'error': 'Parâmetros month/year devem ser inteiros.' }), 400
    except Exception as e:
        return jsonify({ 'ok': False, 'error': f'Erro interno: {str(e)}' }), 500