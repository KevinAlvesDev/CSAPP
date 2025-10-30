import os
from flask import (
    Blueprint, request, redirect, url_for, g, session,
    current_app, send_from_directory, jsonify  # 'render_template' e 'flash' removidos
)
from collections import OrderedDict
from datetime import datetime
from botocore.exceptions import ClientError

# Importações internas do projeto
from ..blueprints.auth import login_required, permission_required 
from ..db import query_db, execute_db, logar_timeline 
from ..services import _get_progress, get_analytics_data 
from ..constants import (
    MODULO_OBRIGATORIO, MODULO_PENDENCIAS, TAREFAS_TREINAMENTO_PADRAO,
    JUSTIFICATIVAS_PARADA, CARGOS_RESPONSAVEL, PERFIS_COM_CRIACAO,
    NIVEIS_RECEITA, SEGUIMENTOS_LIST, TIPOS_PLANOS, MODALIDADES_LIST,
    HORARIOS_FUNCIONAMENTO, FORMAS_PAGAMENTO, SISTEMAS_ANTERIORES,
    RECORRENCIA_USADA,
    NAO_DEFINIDO_BOOL,
    SIM_NAO_OPTIONS,
    PERFIS_COM_GESTAO,
    PERFIL_ADMIN, PERFIL_COORDENADOR, PERFIL_IMPLANTADOR
)
from .. import utils 

main_bp = Blueprint('main', __name__)

# --- Helper ---
def _get_all_cs_users():
    """Busca todos os usuários com perfil que podem receber implantações (Admin, Coordenador, Implantador)."""
    return query_db(
        "SELECT usuario, nome FROM perfil_usuario WHERE perfil_acesso IN (%s, %s, %s) ORDER BY nome", 
        (PERFIL_ADMIN, PERFIL_COORDENADOR, PERFIL_IMPLANTADOR)
    )

# --- Rotas de Visualização (API GET) ---

@main_bp.route('/')
def home():
    # A API apenas informa que está rodando. O front-end (React/Vue) trata a rota raiz.
    # O decorator @login_required na rota /dashboard cuidará da autenticação.
    return jsonify({"status": "API running", "authenticated": 'user' in session})

@main_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    from ..services import get_dashboard_data
    
    user_email = g.user_email
    user_info = g.user
    user_perfil_acesso = g.perfil.get('perfil_acesso')
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO 

    # --- 1. Obter e Tratar Filtros ---
    target_user_email = request.args.get('cs_filter') 
    status_filter = request.args.get('status_filter') or None 
    start_date = request.args.get('start_date') or None 
    end_date = request.args.get('end_date') or None 

    if not is_manager or (target_user_email == 'todos'):
        target_user_email = None 
    
    if not is_manager:
        target_user_email = user_email
        status_filter = None 
    
    selected_cs_filter = target_user_email if target_user_email else 'todos'

    try:
        # --- 2. Chamar Serviços ---
        dashboard_data, metrics = get_dashboard_data(
            user_email=user_email, 
            user_perfil_acesso=user_perfil_acesso,
            target_user_email=target_user_email
        )
        
        global_metrics, cs_metrics_list, implantacoes_paradas_detalhadas = {}, [], []
        
        if is_manager:
            global_metrics, cs_metrics_list, implantacoes_paradas_detalhadas = get_analytics_data(
                target_cs_email=target_user_email, 
                target_status=status_filter,       
                start_date=start_date,             
                end_date=end_date                  
            )

        perfil_data = g.perfil if g.perfil else {} 
        default_metrics = { 'nome': user_info.get('name', user_email), 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'progresso_medio_carteira': 0, 'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0 }
        final_metrics = {**default_metrics, **perfil_data, **metrics}
        
        all_cs_users = _get_all_cs_users() if is_manager else []
        
        status_options = [
            {'value': 'todas', 'label': 'Todas as Implantações'},
            {'value': 'andamento', 'label': 'Em Andamento'},
            {'value': 'atrasadas_status', 'label': 'Atrasadas (> 25d)'},
            {'value': 'futura', 'label': 'Futuras'},
            {'value': 'finalizada', 'label': 'Finalizadas'},
            {'value': 'parada', 'label': 'Paradas'}
        ]

        # --- 4. Renderizar (AGORA COMO JSON) ---
        return jsonify(
            success=True,
            user_info=user_info, 
            metrics=final_metrics, 
            dashboard_data=dashboard_data, 
            implantacoes_andamento=dashboard_data.get('andamento', []), 
            implantacoes_futuras=dashboard_data.get('futuras', []), 
            implantacoes_finalizadas=dashboard_data.get('finalizadas', []), 
            implantacoes_paradas=dashboard_data.get('paradas', []), 
            implantacoes_atrasadas=dashboard_data.get('atrasadas', []), 

            # Constantes que o front-end pode precisar para filtros/modais
            constants={
                'CARGOS_RESPONSAVEL': CARGOS_RESPONSAVEL, 
                'PERFIS_COM_CRIACAO': PERFIS_COM_CRIACAO, 
                'NIVEIS_RECEITA': NIVEIS_RECEITA, 
                'SEGUIMENTOS_LIST': SEGUIMENTOS_LIST, 
                'TIPOS_PLANOS': TIPOS_PLANOS, 
                'MODALIDADES_LIST': MODALIDADES_LIST, 
                'HORARIOS_FUNCIONAMENTO': HORARIOS_FUNCIONAMENTO, 
                'FORMAS_PAGAMENTO': FORMAS_PAGAMENTO, 
                'SISTEMAS_ANTERIORES': SISTEMAS_ANTERIORES, 
                'RECORRENCIA_USADA': RECORRENCIA_USADA, 
                'SIM_NAO_OPTIONS': SIM_NAO_OPTIONS, 
                'JUSTIFICATIVAS_PARADA': JUSTIFICATIVAS_PARADA
            },
            
            is_manager=is_manager, 
            all_cs_users=all_cs_users, 
            selected_cs_filter=selected_cs_filter,
            
            # --- DADOS DE ANALYTICS ---
            analytics_filters={
                'status_options': status_options,
                'current_status_filter': status_filter,
                'current_start_date': start_date,
                'current_end_date': end_date,
            },
            global_metrics=global_metrics, 
            cs_metrics=cs_metrics_list, 
            implantacoes_paradas_detalhadas=implantacoes_paradas_detalhadas
        )
        
    except Exception as e:
        print(f"ERRO ao carregar dashboard para {user_email}: {e}")
        return jsonify(success=False, error=f"Erro ao carregar dados do dashboard: {e}"), 500

@main_bp.route('/implantacao/<int:impl_id>')
@login_required
def ver_implantacao(impl_id):
    usuario_cs_email = g.user_email
    user_perfil_acesso = g.perfil.get('perfil_acesso')
    
    try:
        implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s", (impl_id,), one=True )
        
        if not implantacao:
            return jsonify(success=False, error="Implantação não encontrada."), 404
        
        is_owner = implantacao.get('usuario_cs') == usuario_cs_email
        is_manager = user_perfil_acesso in PERFIS_COM_GESTAO
        
        if not is_owner and not is_manager:
            return jsonify(success=False, error="Acesso negado."), 403

        # Formatação de datas (o front-end pode reformatar, mas enviamos ISO e BR)
        implantacao['data_criacao_fmt_dt_hr'] = utils.format_date_br(implantacao.get('data_criacao'), True)
        implantacao['data_criacao_fmt_d'] = utils.format_date_br(implantacao.get('data_criacao'), False)
        implantacao['data_inicio_efetivo_fmt_d'] = utils.format_date_br(implantacao.get('data_inicio_efetivo'), False)
        implantacao['data_finalizacao_fmt_d'] = utils.format_date_br(implantacao.get('data_finalizacao'), False)
        implantacao['data_inicio_producao_fmt_d'] = utils.format_date_br(implantacao.get('data_inicio_producao'), False)
        implantacao['data_final_implantacao_fmt_d'] = utils.format_date_br(implantacao.get('data_final_implantacao'), False)
        implantacao['data_criacao_iso'] = utils.format_date_iso_for_json(implantacao.get('data_criacao'), only_date=True)
        implantacao['data_inicio_efetivo_iso'] = utils.format_date_iso_for_json(implantacao.get('data_inicio_efetivo'), only_date=True)
        implantacao['data_inicio_producao_iso'] = utils.format_date_iso_for_json(implantacao.get('data_inicio_producao'), only_date=True)
        implantacao['data_final_implantacao_iso'] = utils.format_date_iso_for_json(implantacao.get('data_final_implantacao'), only_date=True)
        implantacao['data_inicio_previsto_fmt_d'] = utils.format_date_br(implantacao.get('data_inicio_previsto'), False)

        progresso, _, _ = _get_progress(impl_id)

        tarefas_raw = query_db("SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem", (impl_id,))
        
        comentarios_raw = query_db( 
            """ SELECT c.*, COALESCE(p.nome, c.usuario_cs) as usuario_nome 
                FROM comentarios c 
                LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario 
                WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = %s) 
                ORDER BY c.data_criacao DESC """, 
            (impl_id,) 
        )

        comentarios_por_tarefa = {}
        for c in comentarios_raw:
            c_formatado = {**c, 'data_criacao_fmt_d': utils.format_date_br(c.get('data_criacao'))}
            comentarios_por_tarefa.setdefault(c['tarefa_id'], []).append(c_formatado)

        tarefas_agrupadas_treinamento = OrderedDict()
        tarefas_agrupadas_obrigatorio = OrderedDict()
        tarefas_agrupadas_pendencias = OrderedDict()
        todos_modulos_temp = set()

        for t in tarefas_raw:
            t['comentarios'] = comentarios_por_tarefa.get(t['id'], [])
            modulo = t['tarefa_pai']
            todos_modulos_temp.add(modulo)
            if modulo == MODULO_OBRIGATORIO: tarefas_agrupadas_obrigatorio.setdefault(modulo, []).append(t)
            elif modulo == MODULO_PENDENCIAS: tarefas_agrupadas_pendencias.setdefault(modulo, []).append(t)
            else: tarefas_agrupadas_treinamento.setdefault(modulo, []).append(t)

        ordered_treinamento = OrderedDict()
        for mp in TAREFAS_TREINAMENTO_PADRAO:
            if mp in tarefas_agrupadas_treinamento: ordered_treinamento[mp] = tarefas_agrupadas_treinamento.pop(mp)
        for mr in sorted(tarefas_agrupadas_treinamento.keys()): ordered_treinamento[mr] = tarefas_agrupadas_treinamento[mr]

        todos_modulos_lista = sorted(list(todos_modulos_temp))
        if MODULO_PENDENCIAS not in todos_modulos_lista: todos_modulos_lista.append(MODULO_PENDENCIAS)

        logs_timeline = query_db( """ SELECT tl.*, COALESCE(p.nome, tl.usuario_cs) as usuario_nome FROM timeline_log tl LEFT JOIN perfil_usuario p ON tl.usuario_cs = p.usuario WHERE tl.implantacao_id = %s ORDER BY tl.data_criacao DESC """, (impl_id,) )
        for log in logs_timeline:
            log['data_criacao_fmt_dt_hr'] = utils.format_date_br(log.get('data_criacao'), True)

        nome_usuario_logado = g.perfil.get('nome', usuario_cs_email)

        all_cs_users = []
        if is_manager:
            all_cs_users = _get_all_cs_users()

        # --- SUBSTITUIR RENDER_TEMPLATE POR JSONIFY ---
        return jsonify(
            success=True,
            user_info=g.user, 
            implantacao=implantacao, 
            tarefas_agrupadas_obrigatorio=tarefas_agrupadas_obrigatorio, 
            tarefas_agrupadas_treinamento=ordered_treinamento, 
            tarefas_agrupadas_pendencias=tarefas_agrupadas_pendencias, 
            todos_modulos=todos_modulos_lista, 
            modulo_pendencias_nome=MODULO_PENDENCIAS,
            progresso_porcentagem=progresso, 
            nome_usuario_logado=nome_usuario_logado, 
            email_usuario_logado=usuario_cs_email, 
            logs_timeline=logs_timeline, 
            all_cs_users=all_cs_users,
            is_manager=is_manager,
            
            # Constantes para os modais/formulários dessa página
            constants={
                'JUSTIFICATIVAS_PARADA': JUSTIFICATIVAS_PARADA,
                'CARGOS_RESPONSAVEL': CARGOS_RESPONSAVEL,
                'NIVEIS_RECEITA': NIVEIS_RECEITA,
                'SEGUIMENTOS_LIST': SEGUIMENTOS_LIST,
                'TIPOS_PLANOS': TIPOS_PLANOS,
                'MODALIDADES_LIST': MODALIDADES_LIST,
                'HORARIOS_FUNCIONAMENTO': HORARIOS_FUNCIONAMENTO,
                'FORMAS_PAGAMENTO': FORMAS_PAGAMENTO,
                'SISTEMAS_ANTERIORES': SISTEMAS_ANTERIORES,
                'RECORRENCIA_USADA': RECORRENCIA_USADA,
                'SIM_NAO_OPTIONS': SIM_NAO_OPTIONS
            }
        )
    except Exception as e:
        print(f"ERRO ao carregar detalhes da implantação ID {impl_id}: {e}")
        return jsonify(success=False, error=f"Erro ao carregar detalhes: {e}"), 500

# --- Rotas de Ação (API POST) ---

@main_bp.route('/criar_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
def criar_implantacao():
    from ..services import _create_default_tasks
    
    usuario_cs_email = g.user_email
    data = request.json  # <-- MUDADO: Recebe JSON em vez de form
    nome_empresa = data.get('nome_empresa', '').strip()
    tipo = data.get('tipo', 'agora')
    data_inicio_previsto_str = data.get('data_inicio_previsto')
    data_inicio_previsto = data_inicio_previsto_str if tipo == 'futura' and data_inicio_previsto_str else None

    if not nome_empresa or tipo not in ['agora', 'futura', 'modulo']:
        return jsonify(success=False, error="Dados inválidos para criar implantação."), 400

    try:
        agora = utils.get_now_utc()
        status = 'futura' if tipo == 'futura' else 'andamento'
        data_inicio_efetivo = agora if tipo in ['agora', 'modulo'] else None
        
        implantacao_id = execute_db(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (usuario_cs_email, nome_empresa, tipo, agora, status, data_inicio_previsto, data_inicio_efetivo)
        )
        if not implantacao_id:
            raise Exception("Falha ao obter ID da nova implantação.")

        logar_timeline(implantacao_id, usuario_cs_email, 'implantacao_criada', f'Implantação "{nome_empresa}" ({tipo.capitalize()}) criada.')
        
        tasks_added = 0
        if tipo in ['agora', 'futura']:
            tasks_added = _create_default_tasks(implantacao_id)
            
        # Busca a implantação recém-criada para retornar
        nova_implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
            
        return jsonify(
            success=True, 
            message=f'Implantação "{nome_empresa}" criada com {tasks_added} tarefas padrão.',
            implantacao_id=implantacao_id,
            nova_implantacao=nova_implantacao # Retorna o objeto criado
        ), 201 # 201 Created

    except Exception as e:
        print(f"ERRO ao criar implantação por {usuario_cs_email}: {e}")
        return jsonify(success=False, error=f'Erro ao criar implantação: {e}'), 500

# Rotas agora usam o ID na URL (mais padrão REST)
@main_bp.route('/implantacao/<int:implantacao_id>/iniciar', methods=['POST'])
@login_required
def iniciar_implantacao(implantacao_id):
    usuario_cs_email = g.user_email
    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, tipo FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl:
            return jsonify(success=False, error="Implantação não encontrada."), 404
        if impl.get('usuario_cs') != usuario_cs_email or impl.get('tipo') != 'futura':
            return jsonify(success=False, error='Operação negada. Implantação não é "futura" ou não pertence a você.'), 403

        agora = utils.get_now_utc()
        execute_db(
            "UPDATE implantacoes SET tipo = 'agora', status = 'andamento', data_inicio_efetivo = %s WHERE id = %s",
            (agora, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" iniciada.')
        
        implantacao_atualizada = query_db("SELECT * FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        return jsonify(success=True, message='Implantação iniciada com sucesso!', implantacao=implantacao_atualizada)

    except Exception as e:
        print(f"Erro ao iniciar implantação ID {implantacao_id}: {e}")
        return jsonify(success=False, error='Erro ao iniciar implantação.'), 500

@main_bp.route('/implantacao/<int:implantacao_id>/finalizar', methods=['POST'])
@login_required
def finalizar_implantacao(implantacao_id):
    usuario_cs_email = g.user_email
    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl:
            return jsonify(success=False, error="Implantação não encontrada."), 404
        if impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento':
            return jsonify(success=False, error='Operação negada. Implantação não está "em andamento".'), 403

        pending_tasks = query_db(
            "SELECT COUNT(*) as total FROM tarefas WHERE implantacao_id = %s AND concluida = %s AND tarefa_pai != %s",
            (implantacao_id, 0, MODULO_PENDENCIAS), one=True
        )

        if pending_tasks and pending_tasks.get('total', 0) > 0:
            total_pendentes = pending_tasks.get('total')
            return jsonify(success=False, error=f'Não é possível finalizar: {total_pendentes} tarefas obrigatórias/treinamento ainda estão pendentes.'), 400

        execute_db(
            "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = %s WHERE id = %s",
            (utils.get_now_utc(), implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" finalizada manually.')
        
        implantacao_atualizada = query_db("SELECT * FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        return jsonify(success=True, message='Implantação finalizada com sucesso!', implantacao=implantacao_atualizada)

    except Exception as e:
        print(f"Erro ao finalizar implantação ID {implantacao_id}: {e}")
        return jsonify(success=False, error=f'Erro ao finalizar implantação: {e}'), 500

@main_bp.route('/implantacao/<int:implantacao_id>/parar', methods=['POST'])
@login_required
def parar_implantacao(implantacao_id):
    usuario_cs_email = g.user_email
    data = request.json # <-- MUDADO: Recebe JSON
    motivo = data.get('motivo_parada', '').strip()

    if not motivo:
        return jsonify(success=False, error='O motivo da parada é obrigatório.'), 400

    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl:
            return jsonify(success=False, error="Implantação não encontrada."), 404
        if impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento':
            return jsonify(success=False, error='Operação negada. Implantação não está "em andamento".'), 403

        execute_db(
            "UPDATE implantacoes SET status = 'parada', data_finalizacao = %s, motivo_parada = %s WHERE id = %s",
            (utils.get_now_utc(), motivo, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" parada. Motivo: {motivo}')
        
        implantacao_atualizada = query_db("SELECT * FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        return jsonify(success=True, message='Implantação marcada como "Parada".', implantacao=implantacao_atualizada)

    except Exception as e:
        print(f"Erro ao parar implantação ID {implantacao_id}: {e}")
        return jsonify(success=False, error=f'Erro ao parar implantação: {e}'), 500

@main_bp.route('/implantacao/<int:implantacao_id>/retomar', methods=['POST'])
@login_required
def retomar_implantacao(implantacao_id):
    usuario_cs_email = g.user_email
    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl:
            return jsonify(success=False, error="Implantação não encontrada."), 404
        if impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'parada':
            return jsonify(success=False, error='Apenas implantações "Paradas" podem ser retomadas.'), 400

        execute_db(
            "UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL, motivo_parada = '' WHERE id = %s",
            (implantacao_id,)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" retomada.')
        
        implantacao_atualizada = query_db("SELECT * FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        return jsonify(success=True, message='Implantação retomada e movida para "Em Andamento".', implantacao=implantacao_atualizada)

    except Exception as e:
        print(f"Erro ao retomar implantação ID {implantacao_id}: {e}")
        return jsonify(success=False, error=f'Erro ao retomar implantação: {e}'), 500

@main_bp.route('/implantacao/<int:implantacao_id>/reabrir', methods=['POST'])
@login_required
def reabrir_implantacao(implantacao_id):
    usuario_cs_email = g.user_email
    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl:
            return jsonify(success=False, error="Implantação não encontrada."), 404
        if impl.get('usuario_cs') != usuario_cs_email:
            return jsonify(success=False, error='Permissão negada.'), 403
            
        if impl.get('status') != 'finalizada':
            return jsonify(success=False, error='Apenas implantações "Finalizadas" podem ser reabertas.'), 400

        execute_db(
            "UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL WHERE id = %s",
            (implantacao_id,)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" reaberta.')
        
        implantacao_atualizada = query_db("SELECT * FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        return jsonify(success=True, message='Implantação reaberta com sucesso.', implantacao=implantacao_atualizada)

    except Exception as e:
        print(f"Erro ao reabrir implantação ID {implantacao_id}: {e}")
        return jsonify(success=False, error=f'Erro ao reabrir implantação: {e}'), 500

@main_bp.route('/implantacao/<int:implantacao_id>/atualizar_detalhes', methods=['POST'])
@login_required
def atualizar_detalhes_empresa(implantacao_id):
    usuario_cs_email = g.user_email
    user_perfil_acesso = g.perfil.get('perfil_acesso')
    data = request.json # <-- MUDADO: Recebe JSON

    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    if not impl:
        return jsonify(success=False, error="Implantação não encontrada."), 404

    is_owner = impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO
    
    if not (is_owner or is_manager):
        return jsonify(success=False, error="Permissão negada."), 403

    def get_json_value(key, default=None):
        value = data.get(key, default)
        # Permite que o front-end envie 'null' para limpar um campo
        if value is None:
            return default if default is not None else None
        
        if isinstance(value, str):
            value = value.strip()
            # Converte string vazia para None (ou o default)
            if value == "": 
                return default if default is not None else None
            # Trata o valor padrão do front-end
            if value == "Não definido":
                 return None
        return value
    
    def get_boolean_value(key):
        value = get_json_value(key, NAO_DEFINIDO_BOOL)
        if value == NAO_DEFINIDO_BOOL or value is None: 
            return None
        return value

    try:
        alunos_ativos = int(data.get('alunos_ativos', 0))
    except (ValueError, TypeError):
        alunos_ativos = 0

    try:
        # Pega todos os campos possíveis do JSON
        campos_recebidos = {
            'responsavel_cliente': get_json_value('responsavel_cliente'),
            'cargo_responsavel': get_json_value('cargo_responsavel'),
            'telefone_responsavel': get_json_value('telefone_responsavel'),
            'email_responsavel': get_json_value('email_responsavel'),
            'data_inicio_producao': get_json_value('data_inicio_producao'),
            'data_final_implantacao': get_json_value('data_final_implantacao'),
            'id_favorecido': get_json_value('id_favorecido'),
            'nivel_receita': get_json_value('nivel_receita'),
            'chave_oamd': get_json_value('chave_oamd'),
            'tela_apoio_link': get_json_value('tela_apoio_link'),
            'seguimento': get_json_value('seguimento'),
            'tipos_planos': get_json_value('tipos_planos'),
            'modalidades': get_json_value('modalidades'),
            'horarios_func': get_json_value('horarios_func'),
            'formas_pagamento': get_json_value('formas_pagamento'),
            'diaria': get_boolean_value('diaria'), 
            'freepass': get_boolean_value('freepass'), 
            'alunos_ativos': alunos_ativos, 
            'sistema_anterior': get_json_value('sistema_anterior'),
            'importacao': get_boolean_value('importacao'), 
            'recorrencia_usa': get_json_value('recorrencia_usa'),
            'boleto': get_boolean_value('boleto'), 
            'nota_fiscal': get_boolean_value('nota_fiscal'), 
            'catraca': get_boolean_value('catraca'), 
            'facial': get_boolean_value('facial'),
            'valor_atribuido': get_json_value('valor_atribuido'), 
            'resp_estrategico_nome': get_json_value('resp_estrategico_nome'),
            'resp_onb_nome': get_json_value('resp_onb_nome'),
            'resp_estrategico_obs': get_json_value('resp_estrategico_obs'),
            'contatos': get_json_value('contatos'),
        }
        
        # Filtra apenas as chaves que *realmente* vieram no JSON
        # Isso permite atualizações parciais (PATCH)
        campos_para_atualizar = {k: v for k, v in campos_recebidos.items() if k in data}
        
        # Caso especial: 'alunos_ativos' sempre vem
        if 'alunos_ativos' in data:
            campos_para_atualizar['alunos_ativos'] = alunos_ativos

        if not campos_para_atualizar:
             return jsonify(success=False, error="Nenhum dado enviado para atualização."), 400

        set_clauses = [f"{k} = %s" for k in campos_para_atualizar.keys()]
        query = f"UPDATE implantacoes SET {', '.join(set_clauses)} WHERE id = %s"
        
        args = list(campos_para_atualizar.values())
        args.append(implantacao_id)
        
        execute_db(query, tuple(args))
        logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', 'Detalhes da empresa/cliente foram atualizados.')
        
        implantacao_atualizada = query_db("SELECT * FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        
        return jsonify(success=True, message='Detalhes da implantação atualizados com sucesso!', implantacao=implantacao_atualizada)
    except Exception as e:
        print(f"Erro ao atualizar detalhes (Impl. ID {implantacao_id}): {e}")
        return jsonify(success=False, error=f'Erro ao atualizar detalhes: {e}'), 500

@main_bp.route('/implantacao/<int:implantacao_id>/transferir', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
def transferir_implantacao(implantacao_id):
    usuario_cs_email = g.user_email
    data = request.json # <-- MUDADO: Recebe JSON
    novo_usuario_cs = data.get('novo_usuario_cs')
    
    if not novo_usuario_cs:
        return jsonify(success=False, error="Dados inválidos para transferência (novo_usuario_cs)."), 400
        
    try:
        impl = query_db("SELECT nome_empresa, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        if not impl:
            return jsonify(success=False, error="Implantação não encontrada."), 404
            
        antigo_usuario_cs = impl.get('usuario_cs', 'Ninguém')
        execute_db("UPDATE implantacoes SET usuario_cs = %s WHERE id = %s", (novo_usuario_cs, implantacao_id))
        logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', f'Implantação "{impl.get("nome_empresa")}" transferida de {antigo_usuario_cs} para {novo_usuario_cs} por {usuario_cs_email}.')
        
        implantacao_atualizada = query_db("SELECT * FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        return jsonify(success=True, message=f'Implantação transferida para {novo_usuario_cs} com sucesso!', implantacao=implantacao_atualizada)

    except Exception as e:
        print(f"Erro ao transferir implantação ID {implantacao_id}: {e}")
        return jsonify(success=False, error=f'Erro ao transferir implantação: {e}'), 500

@main_bp.route('/implantacao/<int:implantacao_id>/excluir', methods=['DELETE']) # <-- MUDADO: Método HTTP para DELETE
@login_required
def excluir_implantacao(implantacao_id):
    usuario_cs_email = g.user_email
    user_perfil_acesso = g.perfil.get('perfil_acesso')
    
    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    if not impl:
         return jsonify(success=False, error="Implantação não encontrada."), 404
         
    is_owner = impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO
    
    if not (is_owner or is_manager):
        return jsonify(success=False, error="Permissão negada."), 403
        
    from ..extensions import r2_client
    if not r2_client:
        return jsonify(success=False, error="Erro: Serviço de armazenamento R2 não configurado."), 500
        
    try:
        comentarios_img = query_db(
            """ SELECT c.imagem_url FROM comentarios c JOIN tarefas t ON c.tarefa_id = t.id WHERE t.implantacao_id = %s AND c.imagem_url IS NOT NULL AND c.imagem_url != '' """, (implantacao_id,)
        )
        public_url_base = current_app.config['CLOUDFLARE_PUBLIC_URL']
        bucket_name = current_app.config['CLOUDFLARE_BUCKET_NAME']
        
        for c in comentarios_img:
            imagem_url = c.get('imagem_url')
            if imagem_url and public_url_base and imagem_url.startswith(public_url_base):
                try:
                    object_key = imagem_url.replace(f"{public_url_base}/", "")
                    if object_key: r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                except ClientError as e_delete: print(f"Aviso: Falha ao excluir R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
                except Exception as e_delete: print(f"Aviso: Falha ao excluir R2 (key: {object_key}). Erro: {e_delete}")
                
        execute_db("DELETE FROM implantacoes WHERE id = %s", (implantacao_id,)) # Deleta em cascata
        return jsonify(success=True, message='Implantação e todos os dados associados foram excluídos com sucesso.', deleted_id=implantacao_id)
        
    except Exception as e:
        print(f"Erro ao excluir implantação ID {implantacao_id}: {e}")
        return jsonify(success=False, error='Erro ao excluir implantação.'), 500

@main_bp.route('/implantacao/<int:implantacao_id>/adicionar_tarefa', methods=['POST'])
@login_required
def adicionar_tarefa(implantacao_id):
    usuario_cs_email = g.user_email
    data = request.json # <-- MUDADO: Recebe JSON
    tarefa_filho = data.get('tarefa_filho', '').strip()
    tarefa_pai = data.get('tarefa_pai', '').strip()
    tag = data.get('tag', '').strip()
    user_perfil_acesso = g.perfil.get('perfil_acesso')

    if not all([implantacao_id, tarefa_filho, tarefa_pai]):
        return jsonify(success=False, error='Dados inválidos para adicionar tarefa (ID, Nome, Módulo).'), 400
        
    try:
        impl = query_db(
            "SELECT id, nome_empresa, status, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
        )
        if not impl:
            return jsonify(success=False, error="Implantação não encontrada."), 404
            
        is_owner = impl.get('usuario_cs') == usuario_cs_email
        is_manager = user_perfil_acesso in PERFIS_COM_GESTAO
        
        if not (is_owner or is_manager):
            return jsonify(success=False, error="Permissão negada."), 403
            
        if impl.get('status') == 'finalizada':
            return jsonify(success=False, error='Não é possível adicionar tarefas a implantações finalizadas.'), 400
            
        max_ordem = query_db(
            "SELECT MAX(ordem) as max_o FROM tarefas WHERE implantacao_id = %s AND tarefa_pai = %s",
            (implantacao_id, tarefa_pai), one=True
        )
        nova_ordem = (max_ordem.get('max_o') or 0) + 1
        
        # Assumindo que seu execute_db foi adaptado para RETURNING id (PostgreSQL)
        tarefa_id = execute_db(
            "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, tag, ordem, concluida) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (implantacao_id, tarefa_pai, tarefa_filho, tag, nova_ordem, 0),
            fetch_id=True # Flag para db.py
        )
        
        if not tarefa_id:
             # Fallback para SQLite
             tarefa_id = query_db("SELECT last_insert_rowid() as id", one=True)['id']
             if not tarefa_id:
                  raise Exception("Não foi possível obter o ID da tarefa recém-criada.")

        # Buscar a tarefa recém-criada para retornar ao front-end
        nova_tarefa = query_db("SELECT * FROM tarefas WHERE id = %s", (tarefa_id,), one=True)
        if nova_tarefa:
             nova_tarefa['comentarios'] = [] # Adiciona para consistência da UI
        
        logar_timeline(implantacao_id, usuario_cs_email, 'tarefa_adicionada', f"Tarefa '{tarefa_filho}' adicionada ao módulo '{tarefa_pai}'.")
        return jsonify(success=True, message='Tarefa adicionada com sucesso!', nova_tarefa=nova_tarefa), 201
        
    except Exception as e:
        print(f"Erro ao adicionar tarefa para implantação ID {implantacao_id}: {e}")
        return jsonify(success=False, error=f'Erro ao adicionar tarefa: {e}'), 500