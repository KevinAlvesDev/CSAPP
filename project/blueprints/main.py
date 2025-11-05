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
from ..services import _get_progress
from ..constants import (
    MODULO_OBRIGATORIO, MODULO_PENDENCIAS, TAREFAS_TREINAMENTO_PADRAO,
    JUSTIFICATIVAS_PARADA, CARGOS_RESPONSAVEL, PERFIS_COM_CRIACAO,
    # NOVAS CONSTANTES
    NIVEIS_RECEITA, SEGUIMENTOS_LIST, TIPOS_PLANOS, MODALIDADES_LIST,
    HORARIOS_FUNCIONAMENTO, FORMAS_PAGAMENTO, SISTEMAS_ANTERIORES,
    RECORRENCIA_USADA,
    NAO_DEFINIDO_BOOL,
    SIM_NAO_OPTIONS,
    PERFIS_COM_GESTAO # ADICIONADO PARA TRANSFERÊNCIA (estava faltando no seu)
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
    from ..services import get_dashboard_data #
    
    user_email = g.user_email #
    user_info = g.user #
    
    # --- INÍCIO AJUSTE 4 ---
    perfil_acesso = g.perfil.get('perfil_acesso') if g.get('perfil') else None
    is_manager = perfil_acesso in PERFIS_COM_GESTAO
    
    # Pega o filtro da URL
    current_cs_filter = request.args.get('cs_filter', None)
    
    # Se não for manager, o filtro não deve ser aplicado/mostrado
    # A lógica de serviço já garante que ele só veja o dele
    if not is_manager:
        current_cs_filter = None
    # --- FIM AJUSTE 4 ---

    try:
        # --- AJUSTE 4: Passa o filtro para a função de serviço ---
        dashboard_data, metrics = get_dashboard_data(user_email, filtered_cs_email=current_cs_filter) #
        
        perfil_data = g.perfil if g.perfil else {} #
        default_metrics = { 'nome': user_info.get('name', user_email), 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'progresso_medio_carteira': 0, 'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0 }
        final_metrics = {**default_metrics, **perfil_data, **metrics}
        
        # --- AJUSTE 4: Busca todos os usuários para os modais E para o filtro ---
        # (Chamada movida para ser usada em ambos os casos, sucesso e erro)
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
            
            # --- INÍCIO AJUSTE 4: Passa os dados do filtro para o template ---
            is_manager=is_manager,
            current_cs_filter=current_cs_filter
            # --- FIM AJUSTE 4 ---
        )
        
    except Exception as e:
        print(f"ERRO ao carregar dashboard para {user_email}: {e}")
        flash("Erro ao carregar dados do dashboard.", "error")
        
        # --- AJUSTE 4: Garante que as variáveis existam mesmo em caso de erro ---
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

# --- Rotas de Ação (POST de Formulários) ---
@main_bp.route('/criar_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO) #
def criar_implantacao():
    from ..services import _create_default_tasks #
    
    usuario_criador = g.user_email # Quem está criando
    nome_empresa = request.form.get('nome_empresa', '').strip()
    usuario_atribuido = request.form.get('usuario_atribuido_cs', '').strip() or usuario_criador
    
    # --- AJUSTE 1 (Início) ---
    # O tipo agora é 'completa' (para diferenciar de 'modulo')
    tipo = 'completa'
    # O status inicial é SEMPRE 'nova'
    status = 'nova'
    # As datas de início são NULAS até o implantador agir
    data_inicio_previsto = None
    data_inicio_efetivo = None
    # --- AJUSTE 1 (Fim) ---

    if not nome_empresa:
        flash('Nome da empresa é obrigatório.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if not usuario_atribuido:
         flash('Usuário a ser atribuído não foi selecionado.', 'error')
         return redirect(url_for('main.dashboard'))

    try:
        agora = datetime.now()
        
        implantacao_id = execute_db( #
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (usuario_atribuido, nome_empresa, tipo, agora, status, data_inicio_previsto, data_inicio_efetivo)
        )
        if not implantacao_id:
            raise Exception("Falha ao obter ID da nova implantação.")

        logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação "{nome_empresa}" ({tipo.capitalize()}) criada e atribuída a {usuario_atribuido}.') #
        
        tasks_added = 0
        # Cria tarefas padrão para 'completa' (mas não para 'modulo')
        if tipo == 'completa': 
            tasks_added = _create_default_tasks(implantacao_id) #
            
        flash(f'Implantação "{nome_empresa}" criada com {tasks_added} tarefas padrão.', 'success')
        # --- AJUSTE 1 (Redirecionamento) ---
        # Redireciona para o dashboard, não para os detalhes
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        print(f"ERRO ao criar implantação por {usuario_criador}: {e}")
        flash(f'Erro ao criar implantação: {e}.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/criar_implantacao_modulo', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
def criar_implantacao_modulo():
    usuario_criador = g.user_email # Quem está criando
    nome_empresa = request.form.get('nome_empresa_modulo', '').strip()
    usuario_atribuido = request.form.get('usuario_atribuido_cs_modulo', '').strip()
    tipo = 'modulo'
    # O status inicial é SEMPRE 'nova'
    status = 'nova' 

    if not nome_empresa or not usuario_atribuido:
        flash('Nome da empresa e implantador atribuído são obrigatórios.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        agora = datetime.now()
        # Status 'nova' e tipo 'modulo', sem data de início efetivo ou previsto
        implantacao_id = execute_db(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (usuario_atribuido, nome_empresa, tipo, agora, status, None, None)
        )
        if not implantacao_id:
            raise Exception("Falha ao obter ID da nova implantação de módulo.")

        logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação de Módulo "{nome_empresa}" criada e atribuída a {usuario_atribuido}.')
        
        flash(f'Implantação de Módulo "{nome_empresa}" criada e atribuída a {usuario_atribuido}.', 'success')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        print(f"ERRO ao criar implantação de módulo por {usuario_criador}: {e}")
        flash(f'Erro ao criar implantação de módulo: {e}.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/iniciar_implantacao', methods=['POST'])
@login_required
def iniciar_implantacao():
    usuario_cs_email = g.user_email #
    implantacao_id = request.form.get('implantacao_id')
    
    # O 'redirect_to' é usado em caso de falha. Em caso de sucesso, sempre vai para 'ver_implantacao'
    redirect_to_fallback = request.form.get('redirect_to', 'dashboard')
    dest_url_fallback = url_for('main.dashboard')
    if redirect_to_fallback == 'detalhes':
        dest_url_fallback = url_for('main.ver_implantacao', impl_id=implantacao_id)
        
    try:
        impl = query_db( #
            "SELECT usuario_cs, nome_empresa, status, tipo FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        
        # O usuário deve ser o dono
        if not impl or impl.get('usuario_cs') != usuario_cs_email:
             flash('Operação negada. Implantação não pertence a você.', 'error')
             return redirect(request.referrer or dest_url_fallback)
             
        # Só pode iniciar se estiver 'nova' ou 'futura'
        if impl.get('status') not in ['nova', 'futura']:
            flash(f'Operação negada. Implantação com status "{impl.get("status")}" não pode ser iniciada.', 'error')
            return redirect(request.referrer or dest_url_fallback)

        agora = datetime.now()
        
        # Define o tipo para 'completa' se for 'futura' (pois 'futura' só vem de 'completa')
        # ou mantém 'modulo' se for 'modulo'.
        # Se for 'nova' e tipo 'completa', mantém 'completa'.
        novo_tipo = impl.get('tipo')
        if novo_tipo == 'futura': # Tipo 'futura' era um erro de lógica antigo
            novo_tipo = 'completa' 
        
        execute_db( #
            "UPDATE implantacoes SET tipo = %s, status = 'andamento', data_inicio_efetivo = %s, data_inicio_previsto = NULL WHERE id = %s",
            (novo_tipo, agora, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" iniciada.') #
        flash('Implantação iniciada com sucesso!', 'success')
        
        # Após iniciar, sempre vai para a página de detalhes
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    except Exception as e:
        print(f"Erro ao iniciar implantação ID {implantacao_id}: {e}")
        flash('Erro ao iniciar implantação.', 'error')
        return redirect(url_for('main.dashboard'))

# --- AJUSTE 1: NOVA ROTA ADICIONADA ---
@main_bp.route('/agendar_implantacao', methods=['POST'])
@login_required
def agendar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    data_prevista = request.form.get('data_inicio_previsto')

    if not data_prevista:
        flash('A data de início previsto é obrigatória.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )

        if not impl or impl.get('usuario_cs') != usuario_cs_email:
            flash('Operação negada. Implantação não pertence a você.', 'error')
            return redirect(url_for('main.dashboard'))

        if impl.get('status') != 'nova':
            flash('Apenas implantações "Novas" podem ser agendadas.', 'warning')
            return redirect(url_for('main.dashboard'))

        execute_db(
            "UPDATE implantacoes SET status = 'futura', data_inicio_previsto = %s WHERE id = %s",
            (data_prevista, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Início da implantação "{impl.get("nome_empresa")}" agendado para {data_prevista}.')
        flash(f'Implantação "{impl.get("nome_empresa")}" movida para "Futuras" com início em {data_prevista}.', 'success')

    except Exception as e:
        print(f"Erro ao agendar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao agendar implantação: {e}', 'error')
    
    return redirect(url_for('main.dashboard'))
# --- FIM DA NOVA ROTA ---


@main_bp.route('/finalizar_implantacao', methods=['POST'])
@login_required
def finalizar_implantacao():
    usuario_cs_email = g.user_email #
    implantacao_id = request.form.get('implantacao_id')
    redirect_target = request.form.get('redirect_to', 'dashboard')
    dest_url = url_for('main.dashboard')
    if redirect_target == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        impl = query_db( #
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento':
            raise Exception('Operação negada. Implantação não está "em andamento".')

        pending_tasks = query_db( #
            "SELECT COUNT(*) as total FROM tarefas WHERE implantacao_id = %s AND concluida = %s AND tarefa_pai != %s",
            (implantacao_id, 0, MODULO_PENDENCIAS), one=True #
        )

        if pending_tasks and pending_tasks.get('total', 0) > 0:
            total_pendentes = pending_tasks.get('total')
            flash(f'Não é possível finalizar: {total_pendentes} tarefas obrigatórias/treinamento ainda estão pendentes.', 'error')
            return redirect(dest_url)

        execute_db( #
            "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s",
            (implantacao_id,)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" finalizada manually.') #
        flash('Implantação finalizada com sucesso!', 'success')

    except Exception as e:
        print(f"Erro ao finalizar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao finalizar implantação: {e}', 'error')

    return redirect(dest_url)

@main_bp.route('/parar_implantacao', methods=['POST'])
@login_required
def parar_implantacao():
    usuario_cs_email = g.user_email #
    implantacao_id = request.form.get('implantacao_id')
    motivo = request.form.get('motivo_parada', '').strip()
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    if not motivo:
        flash('O motivo da parada é obrigatório.', 'error')
        return redirect(dest_url)

    try:
        impl = query_db( #
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento':
            raise Exception('Operação negada. Implantação não está "em andamento".')

        execute_db( #
            "UPDATE implantacoes SET status = 'parada', data_finalizacao = CURRENT_TIMESTAMP, motivo_parada = %s WHERE id = %s",
            (motivo, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" parada. Motivo: {motivo}') #
        flash('Implantação marcada como "Parada".', 'success')

    except Exception as e:
        print(f"Erro ao parar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao parar implantação: {e}', 'error')

    return redirect(dest_url)

@main_bp.route('/retomar_implantacao', methods=['POST'])
@login_required
def retomar_implantacao():
    usuario_cs_email = g.user_email #
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')

    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        impl = query_db( #
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'parada':
            flash('Apenas implantações "Paradas" podem ser retomadas.', 'warning')
            return redirect(request.referrer or url_for('main.dashboard'))

        execute_db( #
            "UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL, motivo_parada = '' WHERE id = %s",
            (implantacao_id,)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" retomada.') #
        flash('Implantação retomada e movida para "Em Andamento".', 'success')

    except Exception as e:
        print(f"Erro ao retomar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao retomar implantação: {e}', 'error')

    return redirect(dest_url)

@main_bp.route('/reabrir_implantacao', methods=['POST'])
@login_required
def reabrir_implantacao():
    usuario_cs_email = g.user_email #
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')

    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        impl = query_db( #
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email:
            flash('Permissão negada.', 'error')
            return redirect(request.referrer or url_for('main.dashboard'))
            
        if impl.get('status') != 'finalizada':
            flash('Apenas implantações "Finalizadas" podem ser reabertas.', 'warning')
            return redirect(dest_url)

        execute_db( #
            "UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL WHERE id = %s",
            (implantacao_id,)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" reaberta.') #
        flash('Implantação reaberta com sucesso e movida para "Em Andamento".', 'success')

    except Exception as e:
        print(f"Erro ao reabrir implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao reabrir implantação: {e}', 'error')

    return redirect(dest_url)

@main_bp.route('/atualizar_detalhes_empresa', methods=['POST'])
@login_required
def atualizar_detalhes_empresa():
    usuario_cs_email = g.user_email #
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')
    user_perfil_acesso = g.perfil.get('perfil_acesso') #

    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True) #
    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO #
    
    if not (is_owner or is_manager):
        flash('Permissão negada.', 'error')
        return redirect(url_for('main.dashboard'))

    def get_form_value(key):
        value = request.form.get(key, '').strip()
        if value == "": return None
        return value
    
    def get_boolean_value(key):
        value = request.form.get(key, NAO_DEFINIDO_BOOL).strip() #
        if value == NAO_DEFINIDO_BOOL or value == "": return None #
        return value
    
    try:
        alunos_ativos_str = request.form.get('alunos_ativos', '0').strip()
        alunos_ativos = int(alunos_ativos_str) if alunos_ativos_str else 0
    except (ValueError, TypeError):
        alunos_ativos = 0

    # *** INÍCIO DA ALTERAÇÃO ***
    # Coleta valores dos campos de lista (que agora são tags)
    # request.form.getlist() pega todos os valores de um campo com o mesmo nome
    # O 'or None' garante que um campo vazio seja salvo como NULL
    modalidades_val = ','.join(request.form.getlist('modalidades')) or None
    horarios_val = ','.join(request.form.getlist('horarios_func')) or None
    formas_pagamento_val = ','.join(request.form.getlist('formas_pagamento')) or None
    # *** FIM DA ALTERAÇÃO ***

    try:
        campos = {
            'responsavel_cliente': get_form_value('responsavel_cliente'),
            'cargo_responsavel': get_form_value('cargo_responsavel'),
            'telefone_responsavel': get_form_value('telefone_responsavel'),
            'email_responsavel': get_form_value('email_responsavel'),
            'data_inicio_producao': get_form_value('data_inicio_producao'),
            'data_final_implantacao': get_form_value('data_final_implantacao'),
            
            # --- INÍCIO DA ALTERAÇÃO ---
            # Adiciona o campo data_inicio_efetivo ao update
            'data_inicio_efetivo': get_form_value('data_inicio_efetivo'),
            # --- FIM DA ALTERAÇÃO ---

            'id_favorecido': get_form_value('id_favorecido'),
            'nivel_receita': get_form_value('nivel_receita'),
            'chave_oamd': get_form_value('chave_oamd'),
            'tela_apoio_link': get_form_value('tela_apoio_link'),
            'seguimento': get_form_value('seguimento'),
            'tipos_planos': get_form_value('tipos_planos'),
            
            # *** INÍCIO DA ALTERAÇÃO ***
            'modalidades': modalidades_val,
            'horarios_func': horarios_val,
            'formas_pagamento': formas_pagamento_val,
            # *** FIM DA ALTERAÇÃO ***
            
            'diaria': get_boolean_value('diaria'), 
            'freepass': get_boolean_value('freepass'), 
            'alunos_ativos': alunos_ativos, 
            'sistema_anterior': get_form_value('sistema_anterior'),
            'importacao': get_boolean_value('importacao'), 
            'recorrencia_usa': get_form_value('recorrencia_usa'),
            'boleto': get_boolean_value('boleto'), 
            'nota_fiscal': get_boolean_value('nota_fiscal'), 
            'catraca': get_boolean_value('catraca'), 
            'facial': get_boolean_value('facial'),
            'valor_atribuido': get_form_value('valor_atribuido'), 
            'resp_estrategico_nome': get_form_value('resp_estrategico_nome'),
            'resp_onb_nome': get_form_value('resp_onb_nome'),
            'resp_estrategico_obs': get_form_value('resp_estrategico_obs'),
            'contatos': get_form_value('contatos'),
        }
        set_clauses = [f"{k} = %s" for k in campos.keys()]
        query = f"UPDATE implantacoes SET {', '.join(set_clauses)} WHERE id = %s" # Removido AND usuario_cs = %s
        args = list(campos.values())
        args.append(implantacao_id) # ID é o último argumento
        
        execute_db(query, tuple(args)) #
        logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', 'Detalhes da empresa/cliente foram atualizados.') #
        flash('Detalhes da implantação atualizados com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao atualizar detalhes (Impl. ID {implantacao_id}): {e}")
        flash(f'Erro ao atualizar detalhes: {e}', 'error')
    return redirect(dest_url)

@main_bp.route('/transferir_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_GESTAO) #
def transferir_implantacao():
    usuario_cs_email = g.user_email #
    implantacao_id = request.form.get('implantacao_id')
    novo_usuario_cs = request.form.get('novo_usuario_cs')
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)
    if not novo_usuario_cs or not implantacao_id:
        flash('Dados inválidos para transferência.', 'error')
        return redirect(dest_url)
    try:
        impl = query_db("SELECT nome_empresa, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True) #
        if not impl:
            flash('Implantação não encontrada.', 'error')
            return redirect(url_for('main.dashboard'))
        antigo_usuario_cs = impl.get('usuario_cs', 'Ninguém')
        execute_db("UPDATE implantacoes SET usuario_cs = %s WHERE id = %s", (novo_usuario_cs, implantacao_id)) #
        logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', f'Implantação "{impl.get("nome_empresa")}" transferida de {antigo_usuario_cs} para {novo_usuario_cs} por {usuario_cs_email}.') #
        flash(f'Implantação transferida para {novo_usuario_cs} com sucesso!', 'success')
        if antigo_usuario_cs == usuario_cs_email:
            return redirect(url_for('main.dashboard'))
    except Exception as e:
        print(f"Erro ao transferir implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao transferir implantação: {e}', 'error')
    return redirect(dest_url)

@main_bp.route('/excluir_implantacao', methods=['POST'])
@login_required
def excluir_implantacao():
    usuario_cs_email = g.user_email #
    implantacao_id = request.form.get('implantacao_id')
    user_perfil_acesso = g.perfil.get('perfil_acesso') #
    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True) #
    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO #
    if not (is_owner or is_manager):
        flash('Permissão negada.', 'error')
        return redirect(url_for('main.dashboard'))
    from ..extensions import r2_client #
    if not r2_client:
        flash("Erro: Serviço de armazenamento R2 não configurado. Não é possível excluir as imagens associadas.", "error")
        return redirect(request.referrer or url_for('main.dashboard'))
    try:
        comentarios_img = query_db( #
            """ SELECT c.imagem_url FROM comentarios c JOIN tarefas t ON c.tarefa_id = t.id WHERE t.implantacao_id = %s AND c.imagem_url IS NOT NULL AND c.imagem_url != '' """, (implantacao_id,)
        )
        public_url_base = current_app.config['CLOUDFLARE_PUBLIC_URL'] #
        bucket_name = current_app.config['CLOUDFLARE_BUCKET_NAME'] #
        for c in comentarios_img:
            imagem_url = c.get('imagem_url')
            if imagem_url and public_url_base and imagem_url.startswith(public_url_base):
                try:
                    object_key = imagem_url.replace(f"{public_url_base}/", "")
                    if object_key: r2_client.delete_object(Bucket=bucket_name, Key=object_key) #
                except ClientError as e_delete: print(f"Aviso: Falha ao excluir R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
                except Exception as e_delete: print(f"Aviso: Falha ao excluir R2 (key: {object_key}). Erro: {e_delete}")
        execute_db("DELETE FROM implantacoes WHERE id = %s", (implantacao_id,)) #
        flash('Implantação e todos os dados associados foram excluídos com sucesso.', 'success')
    except Exception as e:
        print(f"Erro ao excluir implantação ID {implantacao_id}: {e}")
        flash('Erro ao excluir implantação.', 'error')
    return redirect(url_for('main.dashboard'))

@main_bp.route('/adicionar_tarefa', methods=['POST'])
@login_required
def adicionar_tarefa():
    usuario_cs_email = g.user_email #
    implantacao_id = request.form.get('implantacao_id')
    tarefa_filho = request.form.get('tarefa_filho', '').strip()
    tarefa_pai = request.form.get('tarefa_pai', '').strip()
    tag = request.form.get('tag', '').strip()
    user_perfil_acesso = g.perfil.get('perfil_acesso') #
    anchor = 'pendencias-content' if tarefa_pai == MODULO_PENDENCIAS else 'checklist-treinamentos-content' #
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id, _anchor=anchor) 
    if not all([implantacao_id, tarefa_filho, tarefa_pai]):
        flash('Dados inválidos para adicionar tarefa (ID, Nome, Módulo).', 'error')
        return redirect(request.referrer or dest_url) 
    try:
        impl = query_db( #
            "SELECT id, nome_empresa, status, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
        )
        is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
        is_manager = user_perfil_acesso in PERFIS_COM_GESTAO #
        if not (is_owner or is_manager):
            flash('Permissão negada ou implantação não encontrada.', 'error')
            return redirect(url_for('main.dashboard'))
        if impl.get('status') == 'finalizada':
            flash('Não é possível adicionar tarefas a implantações finalizadas.', 'warning')
            return redirect(dest_url)
        max_ordem = query_db( #
            "SELECT MAX(ordem) as max_o FROM tarefas WHERE implantacao_id = %s AND tarefa_pai = %s",
            (implantacao_id, tarefa_pai), one=True
        )
        nova_ordem = (max_ordem.get('max_o') or 0) + 1
        execute_db( #
            "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, tag, ordem, concluida) VALUES (%s, %s, %s, %s, %s, %s)",
            (implantacao_id, tarefa_pai, tarefa_filho, tag, nova_ordem, 0)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'tarefa_adicionada', f"Tarefa '{tarefa_filho}' adicionada ao módulo '{tarefa_pai}'.") #
        flash('Tarefa adicionada com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao adicionar tarefa para implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao adicionar tarefa: {e}', 'error')
    return redirect(dest_url)