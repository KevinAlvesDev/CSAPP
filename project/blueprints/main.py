import os
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, session,
    current_app, send_from_directory
)
from collections import OrderedDict
from datetime import datetime
from botocore.exceptions import ClientError

# Importações internas do projeto
from ..blueprints.auth import login_required, permission_required 
from ..db import query_db, execute_db, logar_timeline 
# --- INÍCIO DA CORREÇÃO ---
# Importa do 'services.py' geral, pois a refatoração do domain não foi concluída
from ..services import _get_progress, get_dashboard_data
# --- FIM DA CORREÇÃO ---
from ..constants import (
    MODULO_OBRIGATORIO, MODULO_PENDENCIAS, TAREFAS_TREINAMENTO_PADRAO,
    JUSTIFICATIVAS_PARADA, CARGOS_RESPONSAVEL, PERFIS_COM_CRIACAO,
    # NOVAS CONSTANTES
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
    # from ..services import get_dashboard_data # (Removido, importado no topo)
    
    user_email = g.user_email #
    user_info = g.user #
    
    perfil_acesso = g.perfil.get('perfil_acesso') if g.get('perfil') else None
    is_manager = perfil_acesso in PERFIS_COM_GESTAO
    
    # Pega o filtro da URL
    current_cs_filter = request.args.get('cs_filter', None)
    
    if not is_manager:
        current_cs_filter = None

    try:
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
    usuario_cs_email = g.user_email #
    user_perfil_acesso = g.perfil.get('perfil_acesso') #
    
    try:
        implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s", (impl_id,), one=True ) #
        
        if not implantacao:
            flash('Implantação não encontrada.', 'error')
            return redirect(url_for('main.dashboard'))
        
        is_owner = implantacao.get('usuario_cs') == usuario_cs_email
        is_manager = user_perfil_acesso in PERFIS_COM_GESTAO #
        
        if not is_owner and not is_manager:
            # Se não for dono nem gerente, mas o status for 'nova', também não deve ver
            if implantacao.get('status') == 'nova':
                 flash('Esta implantação ainda não foi iniciada.', 'warning')
            else:
                flash('Implantação não encontrada ou não pertence a você.', 'error')
            return redirect(url_for('main.dashboard'))
            
        # --- BLOQUEIO PARA STATUS 'NOVA' ---
        # Um implantador não deve acessar a página de detalhes de algo que ele ainda não iniciou.
        if implantacao.get('status') == 'nova' and is_owner and not is_manager:
             flash('Esta implantação está aguardando início. Use os botões "Iniciar" ou "Início Futuro" no dashboard.', 'warning')
             return redirect(url_for('main.dashboard'))
        # --- FIM DO BLOQUEIO ---


        # Formatação de datas
        implantacao['data_criacao_fmt_dt_hr'] = utils.format_date_br(implantacao.get('data_criacao'), True) #
        implantacao['data_criacao_fmt_d'] = utils.format_date_br(implantacao.get('data_criacao'), False) #
        implantacao['data_inicio_efetivo_fmt_d'] = utils.format_date_br(implantacao.get('data_inicio_efetivo'), False) #
        implantacao['data_finalizacao_fmt_d'] = utils.format_date_br(implantacao.get('data_finalizacao'), False) #
        implantacao['data_inicio_producao_fmt_d'] = utils.format_date_br(implantacao.get('data_inicio_producao'), False) #
        implantacao['data_final_implantacao_fmt_d'] = utils.format_date_br(implantacao.get('data_final_implantacao'), False) #
        implantacao['data_criacao_iso'] = utils.format_date_iso_for_json(implantacao.get('data_criacao'), only_date=True) #
        implantacao['data_inicio_efetivo_iso'] = utils.format_date_iso_for_json(implantacao.get('data_inicio_efetivo'), only_date=True) #
        implantacao['data_inicio_producao_iso'] = utils.format_date_iso_for_json(implantacao.get('data_inicio_producao'), only_date=True) #
        implantacao['data_final_implantacao_iso'] = utils.format_date_iso_for_json(implantacao.get('data_final_implantacao'), only_date=True) #
        implantacao['data_inicio_previsto_fmt_d'] = utils.format_date_br(implantacao.get('data_inicio_previsto'), False) #

        progresso, _, _ = _get_progress(impl_id) #

        tarefas_raw = query_db("SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem", (impl_id,)) #
        comentarios_raw = query_db( """ SELECT c.*, COALESCE(p.nome, c.usuario_cs) as usuario_nome FROM comentarios c LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = %s) ORDER BY c.data_criacao DESC """, (impl_id,) ) #

        comentarios_por_tarefa = {}
        for c in comentarios_raw:
            c_formatado = {**c, 'data_criacao_fmt_d': utils.format_date_br(c.get('data_criacao'))} #
            comentarios_por_tarefa.setdefault(c['tarefa_id'], []).append(c_formatado)

        tarefas_agrupadas_treinamento = OrderedDict()
        tarefas_agrupadas_obrigatorio = OrderedDict()
        tarefas_agrupadas_pendencias = OrderedDict()
        todos_modulos_temp = set()

        for t in tarefas_raw:
            t['comentarios'] = comentarios_por_tarefa.get(t['id'], [])
            modulo = t['tarefa_pai']
            todos_modulos_temp.add(modulo)
            if modulo == MODULO_OBRIGATORIO: tarefas_agrupadas_obrigatorio.setdefault(modulo, []).append(t) #
            elif modulo == MODULO_PENDENCIAS: tarefas_agrupadas_pendencias.setdefault(modulo, []).append(t) #
            else: tarefas_agrupadas_treinamento.setdefault(modulo, []).append(t)

        ordered_treinamento = OrderedDict()
        for mp in TAREFAS_TREINAMENTO_PADRAO: #
            if mp in tarefas_agrupadas_treinamento: ordered_treinamento[mp] = tarefas_agrupadas_treinamento.pop(mp)
        for mr in sorted(tarefas_agrupadas_treinamento.keys()): ordered_treinamento[mr] = tarefas_agrupadas_treinamento[mr]

        todos_modulos_lista = sorted(list(todos_modulos_temp))
        if MODULO_PENDENCIAS not in todos_modulos_lista: todos_modulos_lista.append(MODULO_PENDENCIAS) #

        logs_timeline = query_db( """ SELECT tl.*, COALESCE(p.nome, tl.usuario_cs) as usuario_nome FROM timeline_log tl LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario WHERE tl.implantacao_id = %s ORDER BY tl.data_criacao DESC """, (impl_id,) ) #
        for log in logs_timeline:
            log['data_criacao_fmt_dt_hr'] = utils.format_date_br(log.get('data_criacao'), True) #

        nome_usuario_logado = g.perfil.get('nome', usuario_cs_email) #

        all_cs_users = []
        if is_manager:
            all_cs_users = _get_all_cs_users()

        return render_template( 
            'implantacao_detalhes.html', #
            user_info=g.user, 
            implantacao=implantacao, 
            tarefas_agrupadas_obrigatorio=tarefas_agrupadas_obrigatorio, 
            tarefas_agrupadas_treinamento=ordered_treinamento, 
            tarefas_agrupadas_pendencias=tarefas_agrupadas_pendencias, 
            todos_modulos=todos_modulos_lista, 
            modulo_pendencias_nome=MODULO_PENDENCIAS, #
            progresso_porcentagem=progresso, 
            nome_usuario_logado=nome_usuario_logado, 
            email_usuario_logado=usuario_cs_email, 
            justificativas_parada=JUSTIFICATIVAS_PARADA, #
            logs_timeline=logs_timeline, 
            cargos_responsavel=CARGOS_RESPONSAVEL, #
            NIVEIS_RECEITA=NIVEIS_RECEITA, #
            SEGUIMENTOS_LIST=SEGUIMENTOS_LIST, #
            TIPOS_PLANOS=TIPOS_PLANOS, #
            MODALIDADES_LIST=MODALIDADES_LIST, #
            HORARIOS_FUNCIONAMENTO=HORARIOS_FUNCIONAMENTO, #
            FORMAS_PAGAMENTO=FORMAS_PAGAMENTO, #
            SISTEMAS_ANTERIORES=SISTEMAS_ANTERIORES, #
            RECORRENCIA_USADA=RECORRENCIA_USADA, #
            SIM_NAO_OPTIONS=SIM_NAO_OPTIONS, #
            all_cs_users=all_cs_users,
            is_manager=is_manager
        )
    except Exception as e:
        print(f"ERRO ao carregar detalhes da implantação ID {impl_id}: {e}")
        flash("Erro ao carregar detalhes da implantação.", "error")
        return redirect(url_for('main.dashboard'))