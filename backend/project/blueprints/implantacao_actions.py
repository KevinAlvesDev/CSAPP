# app2/CSAPP/project/blueprints/implantacao_actions.py
import os
import time
from flask import (
    Blueprint, request, flash, redirect, url_for, g, current_app
)
from datetime import datetime
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename

# Importações internas do projeto
from ..blueprints.auth import login_required, permission_required 
# --- INÍCIO DA CORREÇÃO (BUG 4) ---
# Importa a nova função 'execute_and_fetch_one'
from ..db import query_db, execute_db, logar_timeline, execute_and_fetch_one
# --- FIM DA CORREÇÃO (BUG 4) ---
# Importa dos novos arquivos de serviço no domínio
from ..domain.implantacao_service import _get_progress, _create_default_tasks

# --- INÍCIO DA CORREÇÃO (Refatoração Passo 4) ---
# Importa as definições de tarefas do novo arquivo
from ..task_definitions import (
    MODULO_OBRIGATORIO, MODULO_PENDENCIAS, TAREFAS_TREINAMENTO_PADRAO
)
# Importa as constantes restantes do arquivo constants
from ..constants import (
    JUSTIFICATIVAS_PARADA, CARGOS_RESPONSAVEL, PERFIS_COM_CRIACAO,
    NIVEIS_RECEITA, SEGUIMENTOS_LIST, TIPOS_PLANOS, MODALIDADES_LIST,
    HORARIOS_FUNCIONAMENTO, FORMAS_PAGAMENTO, SISTEMAS_ANTERIORES,
    RECORRENCIA_USADA,
    NAO_DEFINIDO_BOOL,
    SIM_NAO_OPTIONS,
    PERFIS_COM_GESTAO
)
# --- FIM DA CORREÇÃO ---

from .. import utils
from ..extensions import r2_client # Necessário para excluir_implantacao
from ..extensions import limiter
from flask_limiter.util import get_remote_address
from ..validation import validate_integer, sanitize_string, validate_date, ValidationError

# --- CORREÇÃO: Renomeado de 'actions_bp' para 'implantacao_actions_bp' ---
implantacao_actions_bp = Blueprint('actions', __name__)


# --- Rotas de Ação (POST de Formulários) ---
# (Movidas de main.py)

@implantacao_actions_bp.route('/criar_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO) #
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def criar_implantacao():
    # A importação de _create_default_tasks foi movida para o topo do arquivo
    
    usuario_criador = g.user_email # Quem está criando
    
    try:
        # Valida e sanitiza os campos obrigatórios
        nome_empresa = sanitize_string(request.form.get('nome_empresa', ''), max_length=200)
        if not nome_empresa:
            raise ValidationError('Nome da empresa é obrigatório.')
            
        usuario_atribuido = sanitize_string(request.form.get('usuario_atribuido_cs', ''), max_length=100)
        usuario_atribuido = usuario_atribuido or usuario_criador
        
    except ValidationError as e:
        flash(f'Erro nos dados: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))
    
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

    # --- VALIDAÇÃO: Evitar duplicidade de empresa ativa ---
    try:
        existente = query_db(
            """
            SELECT id, status
            FROM implantacoes
            WHERE LOWER(nome_empresa) = LOWER(%s)
              AND status IN ('nova','futura','andamento','parada')
            LIMIT 1
            """,
            (nome_empresa,), one=True
        )
        if existente:
            status_existente = existente.get('status')
            flash(f'Já existe uma implantação ativa para "{nome_empresa}" (status: {status_existente}). Evite duplicados.', 'error')
            return redirect(url_for('main.dashboard'))
    except Exception as e:
        print(f"Falha ao verificar duplicidade de empresa '{nome_empresa}': {e}")
        flash('Erro ao validar duplicidade de empresa.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        agora = datetime.now()
        
        # --- INÍCIO DA CORREÇÃO (BUG 4) ---
        # Usa a nova função 'execute_and_fetch_one' em vez de 'query_db'
        result = execute_and_fetch_one(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (usuario_atribuido, nome_empresa, tipo, agora, status, data_inicio_previsto, data_inicio_efetivo)
        )
        # --- FIM DA CORREÇÃO (BUG 4) ---

        implantacao_id = result.get('id') if result else None
        
        if not implantacao_id:
            # Captura a falha na inserção, que antes era capturada erroneamente.
            raise Exception("Falha ao obter ID da nova implantação.")

        logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação "{nome_empresa}" ({tipo.capitalize()}) criada e atribuída a {usuario_atribuido}.') #
        
        tasks_added = 0
        # O implantacao_id agora é um inteiro válido (PostgreSQL ou SQLite), permitindo a criação de tarefas
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

@implantacao_actions_bp.route('/criar_implantacao_modulo', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def criar_implantacao_modulo():
    usuario_criador = g.user_email # Quem está criando
    
    try:
        # Valida e sanitiza os campos obrigatórios
        nome_empresa = sanitize_string(request.form.get('nome_empresa_modulo', ''), max_length=200)
        if not nome_empresa:
            raise ValidationError('Nome da empresa é obrigatório.')
            
        usuario_atribuido = sanitize_string(request.form.get('usuario_atribuido_cs_modulo', ''), max_length=100)
        if not usuario_atribuido:
            raise ValidationError('Implantador atribuído é obrigatório.')
            
    except ValidationError as e:
        flash(f'Erro nos dados: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))
    
    tipo = 'modulo'
    # O status inicial é SEMPRE 'nova'
    status = 'nova'

    # --- VALIDAÇÃO: Evitar duplicidade de empresa ativa ---
    try:
        existente = query_db(
            """
            SELECT id, status
            FROM implantacoes
            WHERE LOWER(nome_empresa) = LOWER(%s)
              AND status IN ('nova','futura','andamento','parada')
            LIMIT 1
            """,
            (nome_empresa,), one=True
        )
        if existente:
            status_existente = existente.get('status')
            flash(f'Já existe uma implantação ativa para "{nome_empresa}" (status: {status_existente}). Evite duplicados.', 'error')
            return redirect(url_for('main.dashboard'))
    except Exception as e:
        print(f"Falha ao verificar duplicidade de empresa (módulo) '{nome_empresa}': {e}")
        flash('Erro ao validar duplicidade de empresa.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        agora = datetime.now()
        
        # --- INÍCIO DA CORREÇÃO (BUG 4) ---
        # Usa a nova função 'execute_and_fetch_one' em vez de 'query_db'
        result = execute_and_fetch_one(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (usuario_atribuido, nome_empresa, tipo, agora, status, None, None)
        )
        # --- FIM DA CORREÇÃO (BUG 4) ---

        implantacao_id = result.get('id') if result else None
        
        if not implantacao_id:
            raise Exception("Falha ao obter ID da nova implantação de módulo.")

        logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação de Módulo "{nome_empresa}" criada e atribuída a {usuario_atribuido}.')
        
        # NOTA: Módulos não criam tarefas padrão, apenas a "Obrigações para Finalização"
        # que deve ser adicionada manualmente ou em outro lugar.
        
        flash(f'Implantação de Módulo "{nome_empresa}" criada e atribuída a {usuario_atribuido}.', 'success')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        print(f"ERRO ao criar implantação de módulo por {usuario_criador}: {e}")
        flash(f'Erro ao criar implantação de módulo: {e}.', 'error')
        return redirect(url_for('main.dashboard'))

@implantacao_actions_bp.route('/iniciar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def iniciar_implantacao():
    usuario_cs_email = g.user_email #
    
    try:
        # Valida o ID da implantação
        implantacao_id = validate_integer(request.form.get('implantacao_id'), min_value=1)
    except ValidationError as e:
        flash(f'ID de implantação inválido: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))
    
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

@implantacao_actions_bp.route('/agendar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
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


@implantacao_actions_bp.route('/finalizar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
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

        # Conta tarefas pendentes fora do módulo "Pendências" e inclui tarefas sem módulo (NULL)
        pending_tasks = query_db(
            "SELECT COUNT(*) as total FROM tarefas WHERE implantacao_id = %s AND concluida = %s AND (tarefa_pai != %s OR tarefa_pai IS NULL)",
            (implantacao_id, 0, MODULO_PENDENCIAS), one=True
        )

        # Garante que existam tarefas obrigatórias/treinamento cadastradas (fora de Pendências)
        total_nonpend_tasks = query_db(
            "SELECT COUNT(*) as total FROM tarefas WHERE implantacao_id = %s AND (tarefa_pai != %s OR tarefa_pai IS NULL)",
            (implantacao_id, MODULO_PENDENCIAS), one=True
        )

        total_nonpend = total_nonpend_tasks.get('total', 0) if total_nonpend_tasks else 0
        if total_nonpend == 0:
            flash('Não é possível finalizar: nenhuma tarefa obrigatória/treinamento foi cadastrada.', 'error')
            return redirect(dest_url)

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

@implantacao_actions_bp.route('/parar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def parar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    motivo = request.form.get('motivo_parada', '').strip()
    # --- NOVO CAMPO RETROATIVO ---
    data_parada = request.form.get('data_parada')
    # ------------------------------
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    if not motivo:
        flash('O motivo da parada é obrigatório.', 'error')
        return redirect(dest_url)
    
    # --- NOVA VALIDAÇÃO ---
    if not data_parada:
        flash('A data da parada é obrigatória.', 'error')
        return redirect(dest_url)
    # ------------------------------

    try:
        impl = query_db( 
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento':
            raise Exception('Operação negada. Implantação não está "em andamento".')

        # --- UPDATE CORRIGIDO: Usa data_parada retroativa ---
        execute_db(
            "UPDATE implantacoes SET status = 'parada', data_finalizacao = %s, motivo_parada = %s WHERE id = %s",
            (data_parada, motivo, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" parada retroativamente em {data_parada}. Motivo: {motivo}')
        flash('Implantação marcada como "Parada" com data retroativa.', 'success')

    except Exception as e:
        print(f"Erro ao parar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao parar implantação: {e}', 'error')

    return redirect(dest_url)

@implantacao_actions_bp.route('/retomar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
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

@implantacao_actions_bp.route('/reabrir_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
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

@implantacao_actions_bp.route('/atualizar_detalhes_empresa', methods=['POST'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
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
            
            # --- (ALTERAÇÃO DA ÚLTIMA REQUISIÇÃO) ---
            'data_inicio_efetivo': get_form_value('data_inicio_efetivo'),
            # --- FIM DA ALTERAÇÃO ---

            'id_favorecido': get_form_value('id_favorecido'),
            'nivel_receita': get_form_value('nivel_receita'),
            'chave_oamd': get_form_value('chave_oamd'),
            'tela_apoio_link': get_form_value('tela_apoio_link'),
            'seguimento': get_form_value('seguimento'),
            'tipos_planos': get_form_value('tipos_planos'),
            
            'modalidades': modalidades_val,
            'horarios_func': horarios_val,
            'formas_pagamento': formas_pagamento_val,
            
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

@implantacao_actions_bp.route('/transferir_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_GESTAO) #
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
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

@implantacao_actions_bp.route('/excluir_implantacao', methods=['POST'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
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
    
    # R2 opcional: continua a exclusão mesmo sem armazenamento configurado
    try:
        comentarios_img = query_db( #
            """ SELECT c.imagem_url FROM comentarios c JOIN tarefas t ON c.tarefa_id = t.id WHERE t.implantacao_id = %s AND c.imagem_url IS NOT NULL AND c.imagem_url != '' """, (implantacao_id,)
        )
        public_url_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL') #
        bucket_name = current_app.config.get('CLOUDFLARE_BUCKET_NAME') #
        if r2_client and public_url_base and bucket_name:
            for c in comentarios_img:
                imagem_url = c.get('imagem_url')
                if imagem_url and imagem_url.startswith(public_url_base):
                    try:
                        object_key = imagem_url.replace(f"{public_url_base}/", "")
                        if object_key:
                            r2_client.delete_object(Bucket=bucket_name, Key=object_key) #
                    except ClientError as e_delete:
                        print(f"Aviso: Falha ao excluir R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
                    except Exception as e_delete:
                        print(f"Aviso: Falha ao excluir R2 (key: {object_key}). Erro: {e_delete}")
        else:
            print("Aviso: R2 não configurado ou variáveis ausentes; exclusão seguirá apenas no banco de dados.")
        execute_db("DELETE FROM implantacoes WHERE id = %s", (implantacao_id,)) #
        flash('Implantação e todos os dados associados foram excluídos com sucesso.', 'success')
    except Exception as e:
        print(f"Erro ao excluir implantação ID {implantacao_id}: {e}")
        flash('Erro ao excluir implantação.', 'error')
    return redirect(url_for('main.dashboard'))

@implantacao_actions_bp.route('/adicionar_tarefa', methods=['POST'])
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

@implantacao_actions_bp.route('/cancelar_implantacao', methods=['POST'])
@login_required
def cancelar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    data_cancelamento = request.form.get('data_cancelamento')
    motivo = request.form.get('motivo_cancelamento', '').strip()
    
    # Verifica R2 antes de tudo, pois o arquivo é obrigatório
    if not r2_client:
         flash('Erro: Serviço de armazenamento R2 não configurado. Não é possível fazer upload do comprovante obrigatório.', 'error')
         return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    # Validação de campos obrigatórios
    if not all([implantacao_id, data_cancelamento, motivo]):
        flash('Todos os campos (Data, Motivo Resumo) são obrigatórios para cancelar.', 'error')
         # A URL de redirecionamento é construída aqui para garantir que o erro seja exibido.
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))
        
    file = request.files.get('comprovante_cancelamento')
    if not file or file.filename == '':
        flash('O upload do print do e-mail de cancelamento é obrigatório.', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    try:
        impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        
        # Permissões (Dono ou Gestor)
        is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        if not (is_owner or is_manager):
             flash('Permissão negada para cancelar esta implantação.', 'error')
             return redirect(url_for('main.dashboard'))
             
        if impl.get('status') in ['finalizada', 'cancelada']:
             flash(f'Implantação já está {impl.get("status")}.', 'warning')
             return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

        # Processo de Upload do Comprovante
        comprovante_url = None
        if file and utils.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            nome_base, extensao = os.path.splitext(filename)
            nome_unico = f"cancel_proof_{implantacao_id}_{int(time.time())}{extensao}"
            object_name = f"comprovantes_cancelamento/{nome_unico}"
            
            r2_client.upload_fileobj(
                file,
                current_app.config['CLOUDFLARE_BUCKET_NAME'],
                object_name,
                ExtraArgs={'ContentType': file.content_type}
            )
            comprovante_url = f"{current_app.config['CLOUDFLARE_PUBLIC_URL']}/{object_name}"
        else:
             flash('Tipo de arquivo inválido para o comprovante.', 'error')
             return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

        # Atualiza DB
        execute_db(
            "UPDATE implantacoes SET status = 'cancelada', data_cancelamento = %s, motivo_cancelamento = %s, comprovante_cancelamento_url = %s, data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s",
            (data_cancelamento, motivo, comprovante_url, implantacao_id)
        )
        
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação CANCELADA.\nMotivo: {motivo}\nData inf.: {utils.format_date_br(data_cancelamento)}')
        flash('Implantação cancelada com sucesso.', 'success')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        print(f"Erro ao cancelar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao cancelar implantação: {e}', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))