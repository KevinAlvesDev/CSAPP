import os
import time
import re
from datetime import datetime, date

from flask import (
    Blueprint, request, flash, redirect, url_for, g, current_app
)
from flask_limiter.util import get_remote_address
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename

from ..blueprints.auth import login_required, permission_required
from ..db import query_db, execute_db, logar_timeline, execute_and_fetch_one
from ..config.cache_config import clear_user_cache, clear_implantacao_cache
from ..domain.task_definitions import MODULO_PENDENCIAS
from ..constants import (
    PERFIS_COM_CRIACAO,
    NAO_DEFINIDO_BOOL,
    PERFIS_COM_GESTAO
)
from ..common import utils
from ..core.extensions import r2_client, limiter
from ..common.validation import validate_integer, sanitize_string, validate_date, ValidationError
from ..config.logging_config import app_logger

implantacao_actions_bp = Blueprint('actions', __name__)


@implantacao_actions_bp.route('/criar_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def criar_implantacao():
    usuario_criador = g.user_email

    try:
        nome_empresa = sanitize_string(request.form.get('nome_empresa', ''), max_length=200)
        if not nome_empresa:
            raise ValidationError('Nome da empresa é obrigatório.')

        usuario_atribuido = sanitize_string(request.form.get('usuario_atribuido_cs', ''), max_length=100)
        usuario_atribuido = usuario_atribuido or usuario_criador

    except ValidationError as e:
        flash(f'Erro nos dados: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

    tipo = 'completa'
    status = 'nova'
    data_inicio_previsto = None
    data_inicio_efetivo = None

    if not nome_empresa:
        flash('Nome da empresa é obrigatório.', 'error')
        return redirect(url_for('main.dashboard'))

    if not usuario_atribuido:
        flash('Usuário a ser atribuído não foi selecionado.', 'error')
        return redirect(url_for('main.dashboard'))

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
        app_logger.error(f"Falha ao verificar duplicidade de empresa '{nome_empresa}': {e}")
        flash('Erro ao validar duplicidade de empresa.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        agora = datetime.now()

        result = execute_and_fetch_one(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (usuario_atribuido, nome_empresa, tipo, agora, status, data_inicio_previsto, data_inicio_efetivo)
        )

        implantacao_id = result.get('id') if result else None

        if not implantacao_id:
            raise Exception("Falha ao obter ID da nova implantação.")

        logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação "{nome_empresa}" ({tipo.capitalize()}) criada e atribuída a {usuario_atribuido}.')

        flash(f'Implantação "{nome_empresa}" criada com sucesso. Aplique um plano de sucesso para criar as tarefas.', 'success')

        try:
            clear_user_cache(usuario_criador)
            if usuario_atribuido and usuario_atribuido != usuario_criador:
                clear_user_cache(usuario_atribuido)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        app_logger.error(f"ERRO ao criar implantação por {usuario_criador}: {e}")
        flash(f'Erro ao criar implantação: {e}.', 'error')
        return redirect(url_for('main.dashboard'))


@implantacao_actions_bp.route('/criar_implantacao_modulo', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO)
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def criar_implantacao_modulo():
    usuario_criador = g.user_email

    try:
        nome_empresa = sanitize_string(request.form.get('nome_empresa_modulo', ''), max_length=200)
        if not nome_empresa:
            raise ValidationError('Nome da empresa é obrigatório.')

        usuario_atribuido = sanitize_string(request.form.get('usuario_atribuido_cs_modulo', ''), max_length=100)
        if not usuario_atribuido:
            raise ValidationError('Implantador atribuído é obrigatório.')

        modulo_tipo = sanitize_string(request.form.get('modulo_tipo', ''), max_length=50)
        modulo_opcoes = {
            'nota_fiscal': 'Nota fiscal',
            'vendas_online': 'Vendas Online',
            'app_treino': 'App Treino',
            'recorrencia': 'Recorrência'
        }
        if modulo_tipo not in modulo_opcoes:
            raise ValidationError('Selecione o módulo a ser implantado.')

    except ValidationError as e:
        flash(f'Erro nos dados: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

    tipo = 'modulo'
    status = 'nova'

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
        app_logger.error(f"Falha ao verificar duplicidade de empresa (módulo) '{nome_empresa}': {e}")
        flash('Erro ao validar duplicidade de empresa.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        agora = datetime.now()

        result = execute_and_fetch_one(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status, data_inicio_previsto, data_inicio_efetivo) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (usuario_atribuido, nome_empresa, tipo, agora, status, None, None)
        )

        implantacao_id = result.get('id') if result else None

        if not implantacao_id:
            raise Exception("Falha ao obter ID da nova implantação de módulo.")

        modulo_label = modulo_opcoes.get(modulo_tipo, modulo_tipo)
        logar_timeline(implantacao_id, usuario_criador, 'implantacao_criada', f'Implantação de Módulo "{nome_empresa}" (módulo: {modulo_label}) criada e atribuída a {usuario_atribuido}.')

        try:
            clear_user_cache(usuario_criador)
            if usuario_atribuido and usuario_atribuido != usuario_criador:
                clear_user_cache(usuario_atribuido)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

        flash(f'Implantação de Módulo "{nome_empresa}" (módulo: {modulo_label}) criada e atribuída a {usuario_atribuido}.', 'success')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        app_logger.error(f"ERRO ao criar implantação de módulo por {usuario_criador}: {e}")
        flash(f'Erro ao criar implantação de módulo: {e}.', 'error')
        return redirect(url_for('main.dashboard'))


@implantacao_actions_bp.route('/iniciar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def iniciar_implantacao():
    usuario_cs_email = g.user_email

    try:
        implantacao_id = validate_integer(request.form.get('implantacao_id'), min_value=1)
    except ValidationError as e:
        flash(f'ID de implantação inválido: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

    redirect_to_fallback = request.form.get('redirect_to', 'dashboard')
    dest_url_fallback = url_for('main.dashboard')
    if redirect_to_fallback == 'detalhes':
        dest_url_fallback = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status, tipo FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )

        if not impl or impl.get('usuario_cs') != usuario_cs_email:
            flash('Operação negada. Implantação não pertence a você.', 'error')
            return redirect(request.referrer or dest_url_fallback)

        if impl.get('status') not in ['nova', 'futura', 'sem_previsao']:
            flash(f'Operação negada. Implantação com status "{impl.get("status")}" não pode ser iniciada.', 'error')
            return redirect(request.referrer or dest_url_fallback)

        agora = datetime.now()

        novo_tipo = impl.get('tipo')
        if novo_tipo == 'futura':
            novo_tipo = 'completa'

        execute_db(
            "UPDATE implantacoes SET tipo = %s, status = 'andamento', data_inicio_efetivo = %s, data_inicio_previsto = NULL WHERE id = %s",
            (novo_tipo, agora, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" iniciada.')
        flash('Implantação iniciada com sucesso!', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    except Exception as e:
        app_logger.error(f"Erro ao iniciar implantação ID {implantacao_id}: {e}")
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
        data_prevista_iso = validate_date(data_prevista)
    except ValidationError:
        flash('Data de início inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.', 'error')
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
            (data_prevista_iso, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Início da implantação "{impl.get("nome_empresa")}" agendado para {data_prevista_iso}.')
        flash(f'Implantação "{impl.get("nome_empresa")}" movida para "Futuras" com início em {data_prevista}.', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except Exception as e:
        app_logger.error(f"Erro ao agendar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao agendar implantação: {e}', 'error')

    return redirect(url_for('main.dashboard', refresh='1'))


@implantacao_actions_bp.route('/marcar_sem_previsao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def marcar_sem_previsao():
    usuario_cs_email = g.user_email
    implantacao_id_raw = request.form.get('implantacao_id')
    try:
        implantacao_id = validate_integer(int(implantacao_id_raw), min_value=1)
    except Exception:
        flash('ID da implantação inválido.', 'error')
        return redirect(url_for('main.dashboard', refresh='1'))

    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )

        if not impl or impl.get('usuario_cs') != usuario_cs_email:
            flash('Operação negada. Implantação não pertence a você.', 'error')
            return redirect(url_for('main.dashboard'))

        if impl.get('status') != 'nova':
            flash('Apenas implantações "Novas" podem ser marcadas como Sem previsão.', 'warning')
            return redirect(url_for('main.dashboard'))

        updated = execute_db(
            "UPDATE implantacoes SET status = 'sem_previsao', data_inicio_previsto = NULL WHERE id = %s",
            (implantacao_id,)
        )
        if not updated:
            raise Exception('Falha ao atualizar status para Sem previsão.')

        ver = query_db(
            "SELECT status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not ver or ver.get('status') != 'sem_previsao':
            raise Exception('Atualização não persistida. Tente novamente.')
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa")}" marcada como "Sem previsão".')
        flash(f'Implantação "{impl.get("nome_empresa")}" marcada como "Sem previsão".', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
    except Exception as e:
        app_logger.error(f"Erro ao marcar sem previsão implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao marcar sem previsão: {e}', 'error')

    return redirect(url_for('main.dashboard', refresh='1'))


@implantacao_actions_bp.route('/finalizar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def finalizar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_target = request.form.get('redirect_to', 'dashboard')
    dest_url = url_for('main.dashboard')
    if redirect_target == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        app_logger.info(f"Finalizar solicitada por {usuario_cs_email} para implantacao_id={implantacao_id}")
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl:
            app_logger.warning(f"Finalizar negada: implantação inexistente id={implantacao_id} user={usuario_cs_email}")
            flash('Implantação não encontrada.', 'error')
            return redirect(dest_url)
        if impl.get('usuario_cs') != usuario_cs_email:
            app_logger.warning(f"Finalizar negada: permissão user={usuario_cs_email} não é dono da implantação id={implantacao_id}")
            flash('Permissão negada. Esta implantação não pertence a você.', 'error')
            return redirect(dest_url)
        if impl.get('status') != 'andamento':
            app_logger.warning(f"Finalizar negada: status atual='{impl.get('status')}' id={implantacao_id} user={usuario_cs_email}")
            flash(f"Operação não permitida: status atual é '{impl.get('status')}'. Retome ou inicie antes de finalizar.", 'warning')
            return redirect(dest_url)

        pending_tasks = query_db(
            """SELECT COUNT(*) as total 
               FROM checklist_items ci
               WHERE ci.implantacao_id = %s 
               AND ci.tipo_item = 'subtarefa' 
               AND ci.completed = %s""",
            (implantacao_id, False), one=True
        )

        total_tasks_row = query_db(
            """SELECT COUNT(*) as total 
               FROM checklist_items ci
               WHERE ci.implantacao_id = %s 
               AND ci.tipo_item = 'subtarefa'""",
            (implantacao_id,), one=True
        )

        total_all = total_tasks_row.get('total', 0) if total_tasks_row else 0
        app_logger.info(f"Finalizar validação tarefas: total={total_all} pendentes={pending_tasks.get('total', 0) if pending_tasks else 0} id={implantacao_id} user={usuario_cs_email}")
        if total_all == 0:
            flash('Não é possível finalizar: nenhuma tarefa foi cadastrada.', 'error')
            return redirect(dest_url)

        if pending_tasks and pending_tasks.get('total', 0) > 0:
            total_pendentes = pending_tasks.get('total')
            nomes = query_db(
                """SELECT ci.title as tarefa_filho 
                   FROM checklist_items ci
                   WHERE ci.implantacao_id = %s 
                   AND ci.tipo_item = 'subtarefa' 
                   AND ci.completed = %s 
                   ORDER BY ci.title LIMIT 10""",
                (implantacao_id, False)
            ) or []
            nomes_txt = ", ".join([n.get('tarefa_filho') for n in nomes])
            flash(f'Não é possível finalizar: {total_pendentes} tarefa(s) pendente(s). Pendentes: {nomes_txt}...', 'error')
            return redirect(dest_url)

        data_finalizacao = request.form.get('data_finalizacao')
        if not data_finalizacao:
            flash('A data da finalização é obrigatória.', 'error')
            return redirect(dest_url)
        try:
            data_final_iso = validate_date(data_finalizacao)
        except ValidationError:
            flash('Data da finalização inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.', 'error')
            return redirect(dest_url)

        execute_db(
            "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = %s WHERE id = %s",
            (data_final_iso, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" finalizada manually.')
        flash('Implantação finalizada com sucesso!', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
        app_logger.info(f"Finalizar concluída id={implantacao_id} user={usuario_cs_email}")
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except Exception as e:
        app_logger.error(f"Erro ao finalizar implantação id={implantacao_id} user={usuario_cs_email}: {e}")
        flash('Erro ao finalizar implantação.', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/parar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def parar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    motivo = request.form.get('motivo_parada', '').strip()

    data_parada = request.form.get('data_parada')

    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    if not motivo:
        flash('O motivo da parada é obrigatório.', 'error')
        return redirect(dest_url)

    if not data_parada:
        flash('A data da parada é obrigatória.', 'error')
        return redirect(dest_url)
    try:
        data_parada_iso = validate_date(data_parada)
    except ValidationError:
        flash('Data da parada inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.', 'error')
        return redirect(dest_url)

    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento':
            raise Exception('Operação negada. Implantação não está "em andamento".')

        execute_db(
            "UPDATE implantacoes SET status = 'parada', data_finalizacao = %s, motivo_parada = %s WHERE id = %s",
            (data_parada_iso, motivo, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" parada retroativamente em {data_parada_iso}. Motivo: {motivo}')
        flash('Implantação marcada como "Parada" com data retroativa.', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except Exception as e:
        app_logger.error(f"Erro ao parar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao parar implantação: {e}', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/retomar_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def retomar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')

    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'parada':
            flash('Apenas implantações "Paradas" podem ser retomadas.', 'warning')
            return redirect(request.referrer or url_for('main.dashboard'))

        execute_db(
            "UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL, motivo_parada = '' WHERE id = %s",
            (implantacao_id,)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" retomada.')
        flash('Implantação retomada e movida para "Em Andamento".', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except Exception as e:
        app_logger.error(f"Erro ao retomar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao retomar implantação: {e}', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/reabrir_implantacao', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def reabrir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')

    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email:
            flash('Permissão negada.', 'error')
            return redirect(request.referrer or url_for('main.dashboard'))

        if impl.get('status') != 'finalizada':
            flash('Apenas implantações "Finalizadas" podem ser reabertas.', 'warning')
            return redirect(dest_url)

        execute_db(
            "UPDATE implantacoes SET status = 'andamento', data_finalizacao = NULL WHERE id = %s",
            (implantacao_id,)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" reaberta.')
        flash('Implantação reaberta com sucesso e movida para "Em Andamento".', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass

    except Exception as e:
        app_logger.error(f"Erro ao reabrir implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao reabrir implantação: {e}', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/atualizar_detalhes_empresa', methods=['POST'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def atualizar_detalhes_empresa():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')
    user_perfil_acesso = g.perfil.get('perfil_acesso') if g.perfil else None

    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        flash('Permissão negada.', 'error')
        return redirect(url_for('main.dashboard'))

    def get_form_value(key):
        value = request.form.get(key, '').strip()
        if value == "":
            return None
        return value

    def get_boolean_value(key):
        value = request.form.get(key, NAO_DEFINIDO_BOOL).strip()
        if value == NAO_DEFINIDO_BOOL or value == "":
            return None
        return value

    try:
        alunos_ativos_str = request.form.get('alunos_ativos', '0').strip()
        alunos_ativos = int(alunos_ativos_str) if alunos_ativos_str else 0
    except (ValueError, TypeError):
        alunos_ativos = 0

    def get_multiple_value(key):
        """Retorna valores de seleção múltipla como string separada por vírgula."""
        values = request.form.getlist(key)
        # Remover valores vazios e "Selecione..."
        values = [v.strip() for v in values if v and v.strip() and v.strip() != "Selecione..."]
        return ','.join(values) if values else None
    
    seguimento_val = get_multiple_value('seguimento')
    tipos_planos_val = get_multiple_value('tipos_planos')
    modalidades_val = get_multiple_value('modalidades')
    horarios_val = get_multiple_value('horarios_func')
    formas_pagamento_val = get_multiple_value('formas_pagamento')
    
    cargo_responsavel_val = get_form_value('cargo_responsavel')
    nivel_receita_val = get_form_value('nivel_receita')
    sistema_anterior_val = get_form_value('sistema_anterior')
    recorrencia_usa_val = get_form_value('recorrencia_usa')

    try:
        def normalize_date_str(s):
            """Converte DD/MM/AAAA para YYYY-MM-DD ou retorna None"""
            try:
                if not s:
                    return None

                s = str(s).strip()
                if not s or s == '':
                    return None

                if len(s) == 10 and s[4] == '-' and s[7] == '-':
                    try:
                        datetime.strptime(s, "%Y-%m-%d")
                        return s
                    except:
                        pass

                if '/' in s:
                    parts = s.split('/')
                    if len(parts) == 3:
                        day = parts[0].strip().zfill(2)
                        month = parts[1].strip().zfill(2)
                        year = parts[2].strip()

                        result = f"{year}-{month}-{day}"

                        try:
                            datetime.strptime(result, "%Y-%m-%d")
                            return result
                        except:
                            return None

                return None

            except Exception as e:
                app_logger.error(f"ERRO ao normalizar data '{s}': {e}")
                return None

        valor_raw = get_form_value('valor_atribuido')
        if valor_raw is not None:
            v = valor_raw.replace('R$', '').strip()
            try:
                # Tenta converter direto (formato padrão do input type="number": 1234.56)
                v_float = float(v)
                valor_raw = f"{v_float:.2f}"
            except ValueError:
                # Fallback para formato BR (1.234,56) caso venha como texto
                try:
                    v_br = v.replace('.', '').replace(',', '.')
                    v_float = float(v_br)
                    valor_raw = f"{v_float:.2f}"
                except ValueError:
                    pass

        data_inicio_producao = normalize_date_str(get_form_value('data_inicio_producao'))
        data_final_implantacao = normalize_date_str(get_form_value('data_final_implantacao'))
        data_inicio_efetivo = normalize_date_str(get_form_value('data_inicio_efetivo'))

        data_inicio_efetivo_iso = data_inicio_efetivo or None

        telefone_raw = get_form_value('telefone_responsavel')
        telefone_validado = None
        if telefone_raw:
            # Remove caracteres não numéricos
            telefone_numeros = ''.join(filter(str.isdigit, telefone_raw))
            # Valida: deve ter 10 ou 11 dígitos
            if len(telefone_numeros) >= 10 and len(telefone_numeros) <= 11:
                # Formata: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
                if len(telefone_numeros) == 11:
                    telefone_validado = f"({telefone_numeros[:2]}) {telefone_numeros[2:7]}-{telefone_numeros[7:]}"
                else:
                    telefone_validado = f"({telefone_numeros[:2]}) {telefone_numeros[2:6]}-{telefone_numeros[6:]}"
            else:
                flash('Telefone inválido. Use o formato (XX) XXXXX-XXXX ou (XX) XXXX-XXXX', 'warning')
                return redirect(dest_url)

        campos = {
            'responsavel_cliente': get_form_value('responsavel_cliente'),
            'cargo_responsavel': cargo_responsavel_val,
            'telefone_responsavel': telefone_validado,
            'email_responsavel': get_form_value('email_responsavel'),
            'data_inicio_producao': data_inicio_producao,
            'data_final_implantacao': data_final_implantacao,
            'data_inicio_efetivo': data_inicio_efetivo_iso,
            'id_favorecido': get_form_value('id_favorecido'),
            'nivel_receita': nivel_receita_val,
            'chave_oamd': get_form_value('chave_oamd'),
            'tela_apoio_link': get_form_value('tela_apoio_link'),
            'seguimento': seguimento_val,
            'tipos_planos': tipos_planos_val,
            'modalidades': modalidades_val,
            'horarios_func': horarios_val,
            'formas_pagamento': formas_pagamento_val,
            'diaria': get_boolean_value('diaria'),
            'freepass': get_boolean_value('freepass'),
            'alunos_ativos': alunos_ativos,
            'sistema_anterior': sistema_anterior_val,
            'importacao': get_boolean_value('importacao'),
            'recorrencia_usa': recorrencia_usa_val,
            'boleto': get_boolean_value('boleto'),
            'nota_fiscal': get_boolean_value('nota_fiscal'),
            'catraca': get_boolean_value('catraca'),
            'modelo_catraca': get_form_value('modelo_catraca') if get_boolean_value('catraca') == 'Sim' else None,
            'facial': get_boolean_value('facial'),
            'modelo_facial': get_form_value('modelo_facial') if get_boolean_value('facial') == 'Sim' else None,
            'wellhub': get_boolean_value('wellhub'),
            'totalpass': get_boolean_value('totalpass'),
            'valor_atribuido': valor_raw,
            'resp_estrategico_nome': get_form_value('resp_estrategico_nome'),
            'resp_onb_nome': get_form_value('resp_onb_nome'),
            'resp_estrategico_obs': get_form_value('resp_estrategico_obs'),
            'contatos': get_form_value('contatos'),
        }
        set_clauses = [f"{k} = %s" for k in campos.keys()]
        query = f"UPDATE implantacoes SET {', '.join(set_clauses)} WHERE id = %s"
        args = list(campos.values())
        args.append(implantacao_id)

        final_args = []
        for arg in args:
            if arg is None:
                final_args.append(None)
            elif isinstance(arg, str):
                final_args.append(arg)
            elif isinstance(arg, (datetime, date)):
                try:
                    final_args.append(arg.strftime('%Y-%m-%d'))
                except Exception:
                    final_args.append(str(arg))
            else:
                final_args.append(arg)

        try:
            execute_db(query, tuple(final_args))
        except Exception as e:
            app_logger.error(f"ERRO NO execute_db: {e}")
            raise

        try:
            logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', 'Detalhes da empresa/cliente foram atualizados.')
        except Exception as e:
            app_logger.error(f"ERRO NO logar_timeline: {e}")
            raise

        flash('Detalhes da implantação atualizados com sucesso!', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            if impl and impl.get('usuario_cs'):
                clear_user_cache(impl.get('usuario_cs'))
            clear_implantacao_cache(implantacao_id)
        except Exception as ex:
            app_logger.error(f"Erro ao limpar cache: {ex}")
            pass

    except AttributeError as e:
        if 'isoformat' in str(e):
            app_logger.error(f"ERRO: Tentativa de chamar .isoformat() em string: {e}")
            flash('Erro ao processar data. Verifique o formato (DD/MM/AAAA).', 'error')
        else:
            raise
    except Exception as e:
        app_logger.error(f"ERRO COMPLETO ao atualizar detalhes (Impl. ID {implantacao_id}): {e}")
        flash(f'Erro ao atualizar detalhes: {str(e)}', 'error')
    return redirect(dest_url)


@implantacao_actions_bp.route('/remover_plano_implantacao', methods=['POST'])
@login_required
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def remover_plano_implantacao():
    """Remove o plano de sucesso de uma implantação, limpando todas as fases/ações/tarefas associadas."""
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    user_perfil_acesso = g.perfil.get('perfil_acesso') if g.perfil else None

    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    impl = query_db("SELECT id, usuario_cs, nome_empresa FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    if not impl:
        flash('Implantação não encontrada.', 'error')
        return redirect(url_for('main.dashboard'))

    is_owner = impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO

    if not (is_owner or is_manager):
        flash('Permissão negada.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        execute_db("DELETE FROM checklist_items WHERE implantacao_id = %s", (implantacao_id,))

        execute_db(
            "UPDATE implantacoes SET plano_sucesso_id = NULL, data_atribuicao_plano = NULL, data_previsao_termino = NULL WHERE id = %s",
            (implantacao_id,)
        )

        logar_timeline(
            implantacao_id,
            usuario_cs_email,
            'plano_removido',
            f'Plano de sucesso removido da implantação por {usuario_cs_email}.'
        )

        flash('Plano de sucesso removido com sucesso!', 'success')

        try:
            clear_implantacao_cache(implantacao_id)
        except:
            pass

    except Exception as e:
        app_logger.error(f"Erro ao remover plano da implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao remover plano: {e}', 'error')

    return redirect(dest_url)


@implantacao_actions_bp.route('/transferir_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
@limiter.limit("30 per minute", key_func=lambda: g.user_email or get_remote_address())
def transferir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    novo_usuario_cs = request.form.get('novo_usuario_cs')
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)
    if not novo_usuario_cs or not implantacao_id:
        flash('Dados inválidos para transferência.', 'error')
        return redirect(dest_url)
    try:
        impl = query_db("SELECT nome_empresa, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
        if not impl:
            flash('Implantação não encontrada.', 'error')
            return redirect(url_for('main.dashboard'))
        antigo_usuario_cs = impl.get('usuario_cs', 'Ninguém')
        execute_db("UPDATE implantacoes SET usuario_cs = %s WHERE id = %s", (novo_usuario_cs, implantacao_id))
        logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', f'Implantação "{impl.get("nome_empresa")}" transferida de {antigo_usuario_cs} para {novo_usuario_cs} por {usuario_cs_email}.')
        flash(f'Implantação transferida para {novo_usuario_cs} com sucesso!', 'success')
        if antigo_usuario_cs == usuario_cs_email:
            return redirect(url_for('main.dashboard'))
    except Exception as e:
        app_logger.error(f"Erro ao transferir implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao transferir implantação: {e}', 'error')
    return redirect(dest_url)


@implantacao_actions_bp.route('/excluir_implantacao', methods=['POST'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def excluir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    user_perfil_acesso = g.perfil.get('perfil_acesso') if g.perfil else None
    impl = query_db("SELECT id, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)
    is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
    is_manager = user_perfil_acesso in PERFIS_COM_GESTAO
    if not (is_owner or is_manager):
        flash('Permissão negada.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        comentarios_img = query_db(
            """ SELECT DISTINCT c.imagem_url 
                FROM comentarios_h c 
                WHERE EXISTS (
                    SELECT 1 FROM checklist_items ci 
                    WHERE c.checklist_item_id = ci.id
                    AND ci.implantacao_id = %s
                )
                AND c.imagem_url IS NOT NULL AND c.imagem_url != '' """, 
            (implantacao_id,)
        )
        public_url_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
        bucket_name = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
        if r2_client and public_url_base and bucket_name:
            for c in comentarios_img:
                imagem_url = c.get('imagem_url')
                if imagem_url and imagem_url.startswith(public_url_base):
                    try:
                        object_key = imagem_url.replace(f"{public_url_base}/", "")
                        if object_key:
                            r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                    except ClientError as e_delete:
                        app_logger.warning(f"Falha ao excluir R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
                    except Exception as e_delete:
                        app_logger.warning(f"Falha ao excluir R2 (key: {object_key}). Erro: {e_delete}")
        else:
            app_logger.warning("R2 não configurado ou variáveis ausentes; exclusão seguirá apenas no banco de dados.")
        execute_db("DELETE FROM implantacoes WHERE id = %s", (implantacao_id,))
        flash('Implantação e todos os dados associados foram excluídos com sucesso.', 'success')
        try:
            clear_user_cache(usuario_cs_email)
            clear_implantacao_cache(implantacao_id)
        except Exception:
            pass
    except Exception as e:
        app_logger.error(f"Erro ao excluir implantação ID {implantacao_id}: {e}")
        flash('Erro ao excluir implantação.', 'error')
    return redirect(url_for('main.dashboard'))


@implantacao_actions_bp.route('/adicionar_tarefa', methods=['POST'])
@login_required
def adicionar_tarefa():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    tarefa_filho = request.form.get('tarefa_filho', '').strip()
    tarefa_pai = request.form.get('tarefa_pai', '').strip()
    tag = request.form.get('tag', '').strip()
    user_perfil_acesso = g.perfil.get('perfil_acesso') if g.perfil else None
    anchor = 'pendencias-content' if tarefa_pai == MODULO_PENDENCIAS else 'checklist-treinamentos-content'
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id, _anchor=anchor)
    if not all([implantacao_id, tarefa_filho, tarefa_pai]):
        flash('Dados inválidos para adicionar tarefa (ID, Nome, Módulo).', 'error')
        return redirect(request.referrer or dest_url)
    try:
        impl = query_db(
            "SELECT id, nome_empresa, status, usuario_cs FROM implantacoes WHERE id = %s", (implantacao_id,), one=True
        )
        is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
        is_manager = user_perfil_acesso in PERFIS_COM_GESTAO
        if not (is_owner or is_manager):
            flash('Permissão negada ou implantação não encontrada.', 'error')
            return redirect(url_for('main.dashboard'))
        if impl.get('status') == 'finalizada':
            flash('Não é possível adicionar tarefas a implantações finalizadas.', 'warning')
            return redirect(dest_url)
        flash('A funcionalidade de adicionar tarefas foi migrada para a estrutura hierárquica. Use a interface de hierarquia para adicionar tarefas.', 'warning')
        app_logger.warning(f"Tentativa de usar adicionar_tarefa (deprecated) para impl_id={implantacao_id} user={usuario_cs_email}")
    except Exception as e:
        app_logger.error(f"Erro ao adicionar tarefa para implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao adicionar tarefa: {e}', 'error')
    return redirect(dest_url)


@implantacao_actions_bp.route('/cancelar_implantacao', methods=['POST'])
@login_required
def cancelar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    data_cancelamento = request.form.get('data_cancelamento')
    motivo = request.form.get('motivo_cancelamento', '').strip()

    if not r2_client:
        flash('Erro: Serviço de armazenamento R2 não configurado. Não é possível fazer upload do comprovante obrigatório.', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    if not all([implantacao_id, data_cancelamento, motivo]):
        flash('Todos os campos (Data, Motivo Resumo) são obrigatórios para cancelar.', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    try:
        data_cancel_iso = validate_date(data_cancelamento)
    except ValidationError:
        flash('Data do cancelamento inválida. Formatos aceitos: DD/MM/AAAA, MM/DD/AAAA, AAAA-MM-DD.', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    file = request.files.get('comprovante_cancelamento')
    if not file or file.filename == '':
        flash('O upload do print do e-mail de cancelamento é obrigatório.', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    try:
        impl = query_db("SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s", (implantacao_id,), one=True)

        is_owner = impl and impl.get('usuario_cs') == usuario_cs_email
        is_manager = g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO

        if not (is_owner or is_manager):
            flash('Permissão negada para cancelar esta implantação.', 'error')
            return redirect(url_for('main.dashboard'))

        if impl.get('status') in ['finalizada', 'cancelada']:
            flash(f'Implantação já está {impl.get("status")}.', 'warning')
            return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

        if impl.get('status') == 'nova':
            flash('Ações indisponíveis para implantações "Nova". Inicie a implantação para habilitar cancelamento.', 'warning')
            return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

        comprovante_url = None
        if file and utils.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            _, extensao = os.path.splitext(filename)
            nome_unico = f"cancel_proof_{implantacao_id}_{int(time.time())}{extensao}"
            object_name = f"comprovantes_cancelamento/{nome_unico}"

            bucket_name = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
            public_url = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
            r2_ok = bool(r2_client) and bool(bucket_name) and bool(public_url) and bool(current_app.config.get('R2_CONFIGURADO')) and bool(re.match(r'^[a-zA-Z0-9.\-_]{1,255}$', bucket_name))

            if r2_ok:
                r2_client.upload_fileobj(
                    file,
                    bucket_name,
                    object_name,
                    ExtraArgs={'ContentType': file.content_type}
                )
                comprovante_url = f"{public_url}/{object_name}"
            else:
                base_dir = os.path.join(os.path.dirname(current_app.root_path), 'uploads')
                target_dir = os.path.join(base_dir, 'comprovantes_cancelamento')
                try:
                    os.makedirs(target_dir, exist_ok=True)
                except Exception:
                    pass
                local_path = os.path.join(target_dir, nome_unico)
                file.stream.seek(0)
                with open(local_path, 'wb') as f_out:
                    f_out.write(file.stream.read())
                comprovante_url = url_for('main.serve_upload', filename=f'comprovantes_cancelamento/{nome_unico}')
        else:
            flash('Tipo de arquivo inválido para o comprovante.', 'error')
            return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

        execute_db(
            "UPDATE implantacoes SET status = 'cancelada', data_cancelamento = %s, motivo_cancelamento = %s, comprovante_cancelamento_url = %s, data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s",
            (data_cancel_iso, motivo, comprovante_url, implantacao_id)
        )

        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação CANCELADA.\nMotivo: {motivo}\nData inf.: {utils.format_date_br(data_cancel_iso)}')
        flash('Implantação cancelada com sucesso.', 'success')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        app_logger.error(f"Erro ao cancelar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao cancelar implantação: {e}', 'error')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))
