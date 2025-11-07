import os
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, session,
    current_app, send_from_directory, jsonify # <-- ADICIONADO jsonify
)
# collections.OrderedDict e datetime removidos (não são mais necessários aqui)
# botocore.exceptions.ClientError removido (não é mais necessário aqui)

# Importações internas do projeto
from ..blueprints.auth import login_required, permission_required 
from ..db import query_db, execute_db, logar_timeline, get_db_connection # <-- ADICIONADO get_db_connection
# --- INÍCIO DA CORREÇÃO (Refatoração Passo 2) ---
# Importa dos novos arquivos de serviço no domínio
from ..domain.dashboard_service import get_dashboard_data
from ..domain.implantacao_service import get_implantacao_details
# --- FIM DA CORREÇÃO ---
from ..constants import (
    # Constantes específicas da implantação (MODULO_OBRIGATORIO, etc.) foram removidas
    # Elas agora são usadas apenas na camada de serviço (domain)
    CARGOS_RESPONSAVEL, PERFIS_COM_CRIACAO,
    NIVEIS_RECEITA, SEGUIMENTOS_LIST, TIPOS_PLANOS, MODALIDADES_LIST,
    HORARIOS_FUNCIONAMENTO, FORMAS_PAGAMENTO, SISTEMAS_ANTERIORES,
    RECORRENCIA_USADA,
    NAO_DEFINIDO_BOOL,
    SIM_NAO_OPTIONS,
    PERFIS_COM_GESTAO
)
# Garanta que o 'utils' seja importado
from .. import utils

main_bp = Blueprint('main', __name__)

# --- Helper para buscar usuários (usado em ver_implantacao) ---
# NOTA: Esta função ainda é usada pelo 'dashboard'.
# A lógica de 'ver_implantacao' agora usa a que está em 'implantacao_service'.
def _get_all_cs_users():
    """Busca todos os usuários com perfil que podem receber implantações."""
    # Garante que a query retorne uma lista vazia em vez de None se falhar
    result = query_db("SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IS NOT NULL AND perfil_acesso != '' ORDER BY nome")
    return result if result is not None else []

# --- Rotas de Visualização ---

@main_bp.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html') #

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # (A importação de get_dashboard_data foi movida para o topo)
    
    user_email = g.user_email #
    user_info = g.user #
    
    perfil_acesso = g.perfil.get('perfil_acesso') if g.get('perfil') else None
    is_manager = perfil_acesso in PERFIS_COM_GESTAO
    
    # Pega o filtro da URL
    current_cs_filter = request.args.get('cs_filter', None)
    
    if not is_manager:
        current_cs_filter = None

    try:
        # A função get_dashboard_data agora vem do dashboard_service
        dashboard_data, metrics = get_dashboard_data(user_email, filtered_cs_email=current_cs_filter) #
        
        perfil_data = g.perfil if g.perfil else {} #
        default_metrics = { 'nome': user_info.get('name', user_email), 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'progresso_medio_carteira': 0, 'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0 }
        final_metrics = {**default_metrics, **perfil_data, **metrics}
        
        all_cs_users = _get_all_cs_users()

        return render_template(
            'dashboard.html', #
            user_info=user_info, 
            metrics=final_metrics, 
            implantacoes_andamento=dashboard_data.get('andamento', []), 
            implantacoes_novas=dashboard_data.get('novas', []), # Envia 'novas'
            implantacoes_futuras=dashboard_data.get('futuras', []), 
            implantacoes_finalizadas=dashboard_data.get('finalizadas', []), 
            implantacoes_paradas=dashboard_data.get('paradas', []), 
            implantacoes_atrasadas=dashboard_data.get('atrasadas', []), 
            cargos_responsavel=CARGOS_RESPONSAVEL, #
            PERFIS_COM_CRIACAO=PERFIS_COM_CRIACAO, # 
            NIVEIS_RECEITA=NIVEIS_RECEITA, #
            SEGUIMENTOS_LIST=SEGUIMENTOS_LIST, #
            TIPOS_PLANOS=TIPOS_PLANOS, #
            MODALIDADES_LIST=MODALIDADES_LIST, #
            HORARIOS_FUNCIONAMENTO=HORARIOS_FUNCIONAMENTO, #
            FORMAS_PAGAMENTO=FORMAS_PAGAMENTO, #
            SISTEMAS_ANTERIORES=SISTEMAS_ANTERIORES, #
            RECORRENCIA_USADA=RECORRENCIA_USADA, #
            SIM_NAO_OPTIONS=SIM_NAO_OPTIONS, #
            all_cs_users=all_cs_users, # Usado para modais E para o novo filtro
            
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
                             implantacoes_futuras=[], implantacoes_finalizadas=[], 
                             implantacoes_paradas=[], implantacoes_atrasadas=[], 
                             cargos_responsavel=CARGOS_RESPONSAVEL, error="Falha ao carregar dados.", 
                             all_cs_users=[], PERFIS_COM_CRIACAO=PERFIS_COM_CRIACAO,
                             is_manager=is_manager_erro, current_cs_filter=current_cs_filter_erro) #

@main_bp.route('/implantacao/<int:impl_id>')
@login_required
def ver_implantacao(impl_id):
    # --- INÍCIO DA REATORAÇÃO (Lógica movida para o serviço) ---
    try:
        # 1. Delega toda a busca e processamento para a camada de serviço
        context_data = get_implantacao_details(
            impl_id=impl_id,
            usuario_cs_email=g.user_email,
            user_perfil=g.perfil
        )
        
        # 2. Renderiza o template passando o dicionário de contexto
        # O operador ** desempacota o dicionário (ex: 'implantacao', 'logs_timeline', etc.)
        return render_template( 
            'implantacao_detalhes.html', 
            **context_data
        )
        
    except ValueError as e:
        # 3. Captura erros de validação (Não encontrado, Permissão negada)
        flash(str(e), 'error')
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        # 4. Captura erros inesperados do servidor
        print(f"ERRO ao carregar detalhes da implantação ID {impl_id}: {e}")
        flash("Erro ao carregar detalhes da implantação.", "error")
        return redirect(url_for('main.dashboard'))


# --- ROTAS SECRETAS REMOVIDAS ---
# A rota /@_SECURE_PROMOTE_ME_@ foi removida.
# A rota /@_CHECK_DB_TABLES_@ foi removida.
# --- FIM DA CORREÇÃO ---