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
# logar_timeline importado de db, não services.
from ..db import query_db, execute_db, logar_timeline 
# CORREÇÃO CRÍTICA: Funções auxiliares mantidas aqui.
from ..services import _get_progress
from ..constants import (
    MODULO_OBRIGATORIO, MODULO_PENDENCIAS, TAREFAS_TREINAMENTO_PADRAO,
    JUSTIFICATIVAS_PARADA, CARGOS_RESPONSAVEL, PERFIS_COM_CRIACAO
)
# Garanta que o 'utils' seja importado
from .. import utils

main_bp = Blueprint('main', __name__)

# --- Rotas de Visualização ---

@main_bp.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # SOLUÇÃO PARA QUEBRAR O CICLO: Importar a função crítica aqui.
    from ..services import get_dashboard_data 
    
    user_email = g.user_email
    user_info = g.user
    try:
        # Chama a função após a importação interna
        dashboard_data, metrics = get_dashboard_data(user_email)
        
        perfil_data = g.perfil if g.perfil else {}
        default_metrics = { 'nome': user_info.get('name', user_email), 'impl_andamento': 0, 'impl_finalizadas': 0, 'impl_paradas': 0, 'progresso_medio_carteira': 0, 'impl_andamento_total': 0, 'implantacoes_atrasadas': 0, 'implantacoes_futuras': 0 }
        final_metrics = {**default_metrics, **perfil_data, **metrics}
        return render_template('dashboard.html', user_info=user_info, metrics=final_metrics, implantacoes_andamento=dashboard_data.get('andamento', []), implantacoes_futuras=dashboard_data.get('futuras', []), implantacoes_finalizadas=dashboard_data.get('finalizadas', []), implantacoes_paradas=dashboard_data.get('paradas', []), implantacoes_atrasadas=dashboard_data.get('atrasadas', []), cargos_responsavel=CARGOS_RESPONSAVEL )
    except Exception as e:
        print(f"ERRO ao carregar dashboard para {user_email}: {e}")
        flash("Erro ao carregar dados do dashboard.", "error")
        return render_template('dashboard.html', user_info=user_info, metrics={}, implantacoes_andamento=[], implantacoes_futuras=[], implantacoes_finalizadas=[], implantacoes_paradas=[], implantacoes_atrasadas=[], cargos_responsavel=CARGOS_RESPONSAVEL, error="Falha ao carregar dados." )

@main_bp.route('/implantacao/<int:impl_id>')
@login_required
def ver_implantacao(impl_id):
    usuario_cs_email = g.user_email
    try:
        implantacao = query_db("SELECT * FROM implantacoes WHERE id = %s AND usuario_cs = %s", (impl_id, usuario_cs_email), one=True )
        if not implantacao:
            flash('Implantação não encontrada ou não pertence a você.', 'error')
            return redirect(url_for('main.dashboard'))

        # Formatação de datas
        implantacao['data_criacao_fmt_dt_hr'] = utils.format_date_br(implantacao.get('data_criacao'), True)
        implantacao['data_criacao_fmt_d'] = utils.format_date_br(implantacao.get('data_criacao'), False)
        implantacao['data_finalizacao_fmt_d'] = utils.format_date_br(implantacao.get('data_finalizacao'), False)
        implantacao['data_inicio_producao_fmt_d'] = utils.format_date_br(implantacao.get('data_inicio_producao'), False)
        implantacao['data_final_implantacao_fmt_d'] = utils.format_date_br(implantacao.get('data_final_implantacao'), False)
        implantacao['data_criacao_iso'] = utils.format_date_iso_for_json(implantacao.get('data_criacao'), only_date=True)
        implantacao['data_inicio_producao_iso'] = utils.format_date_iso_for_json(implantacao.get('data_inicio_producao'), only_date=True)
        implantacao['data_final_implantacao_iso'] = utils.format_date_iso_for_json(implantacao.get('data_final_implantacao'), only_date=True)

        progresso, _, _ = _get_progress(impl_id)

        tarefas_raw = query_db("SELECT * FROM tarefas WHERE implantacao_id = %s ORDER BY tarefa_pai, ordem", (impl_id,))
        comentarios_raw = query_db( """ SELECT c.*, COALESCE(p.nome, c.usuario_cs) as usuario_nome FROM comentarios c LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario WHERE c.tarefa_id IN (SELECT id FROM tarefas WHERE implantacao_id = %s) ORDER BY c.data_criacao DESC """, (impl_id,) )

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

        return render_template( 'implantacao_detalhes.html', user_info=g.user, implantacao=implantacao, tarefas_agrupadas_obrigatorio=tarefas_agrupadas_obrigatorio, tarefas_agrupadas_treinamento=ordered_treinamento, tarefas_agrupadas_pendencias=tarefas_agrupadas_pendencias, todos_modulos=todos_modulos_lista, modulo_pendencias_nome=MODULO_PENDENCIAS, progresso_porcentagem=progresso, nome_usuario_logado=nome_usuario_logado, email_usuario_logado=usuario_cs_email, justificativas_parada=JUSTIFICATIVAS_PARADA, logs_timeline=logs_timeline, cargos_responsavel=CARGOS_RESPONSAVEL )
    except Exception as e:
        print(f"ERRO ao carregar detalhes da implantação ID {impl_id}: {e}")
        flash("Erro ao carregar detalhes da implantação.", "error")
        return redirect(url_for('main.dashboard'))

# --- Rotas de Ação (POST de Formulários) ---
@main_bp.route('/criar_implantacao', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_CRIACAO) # Restrição de permissão aplicada aqui
def criar_implantacao():
    # SOLUÇÃO PARA QUEBRAR O CICLO: Importar a função crítica aqui.
    from ..services import _create_default_tasks
    
    usuario_cs_email = g.user_email
    nome_empresa = request.form.get('nome_empresa', '').strip()
    tipo = request.form.get('tipo', 'agora')

    if not nome_empresa or tipo not in ['agora', 'futura']:
        flash('Dados inválidos para criar implantação.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        status = 'futura' if tipo == 'futura' else 'andamento'
        implantacao_id = execute_db(
            "INSERT INTO implantacoes (usuario_cs, nome_empresa, tipo, data_criacao, status) VALUES (%s, %s, %s, %s, %s)",
            (usuario_cs_email, nome_empresa, tipo, datetime.now(), status)
        )
        if not implantacao_id:
            raise Exception("Falha ao obter ID da nova implantação.")

        logar_timeline(implantacao_id, usuario_cs_email, 'implantacao_criada', f'Implantação "{nome_empresa}" ({tipo.capitalize()}) criada.')
        tasks_added = _create_default_tasks(implantacao_id) # Chama a função após importação interna
        flash(f'Implantação "{nome_empresa}" criada com {tasks_added} tarefas padrão.', 'success')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    except Exception as e:
        print(f"ERRO ao criar implantação por {usuario_cs_email}: {e}")
        flash(f'Erro ao criar implantação: {e}.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/iniciar_implantacao', methods=['POST'])
@login_required
def iniciar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, tipo FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('tipo') != 'futura':
            flash('Operação negada. Implantação não é "futura" ou não pertence a você.', 'error')
            return redirect(request.referrer or url_for('main.dashboard'))

        execute_db(
            "UPDATE implantacoes SET tipo = 'agora', status = 'andamento', data_criacao = %s WHERE id = %s",
            (datetime.now(), implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" iniciada.')
        flash('Implantação iniciada com sucesso!', 'success')
        return redirect(url_for('main.ver_implantacao', impl_id=implantacao_id))

    except Exception as e:
        print(f"Erro ao iniciar implantação ID {implantacao_id}: {e}")
        flash('Erro ao iniciar implantação.', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/finalizar_implantacao', methods=['POST'])
@login_required
def finalizar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_target = request.form.get('redirect_to', 'dashboard')
    dest_url = url_for('main.dashboard')
    if redirect_target == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento':
            raise Exception('Operação negada. Implantação não está "em andamento".')

        # Verifica se há tarefas pendentes (exceto do módulo de pendências)
        pending_tasks = query_db(
            "SELECT COUNT(*) as total FROM tarefas WHERE implantacao_id = %s AND concluida = %s AND tarefa_pai != %s",
            (implantacao_id, 0, MODULO_PENDENCIAS), one=True
        )

        if pending_tasks and pending_tasks.get('total', 0) > 0:
            total_pendentes = pending_tasks.get('total')
            flash(f'Não é possível finalizar: {total_pendentes} tarefas obrigatórias/treinamento ainda estão pendentes.', 'error')
            return redirect(dest_url)

        execute_db(
            "UPDATE implantacoes SET status = 'finalizada', data_finalizacao = CURRENT_TIMESTAMP WHERE id = %s",
            (implantacao_id,)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" finalizada manualmente.')
        flash('Implantação finalizada com sucesso!', 'success')

    except Exception as e:
        print(f"Erro ao finalizar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao finalizar implantação: {e}', 'error')

    return redirect(dest_url)

@main_bp.route('/parar_implantacao', methods=['POST'])
@login_required
def parar_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    motivo = request.form.get('motivo_parada', '').strip()
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    if not motivo:
        flash('O motivo da parada é obrigatório.', 'error')
        return redirect(dest_url)

    try:
        impl = query_db(
            "SELECT usuario_cs, nome_empresa, status FROM implantacoes WHERE id = %s",
            (implantacao_id,), one=True
        )
        if not impl or impl.get('usuario_cs') != usuario_cs_email or impl.get('status') != 'andamento':
            raise Exception('Operação negada. Implantação não está "em andamento".')

        execute_db(
            "UPDATE implantacoes SET status = 'parada', data_finalizacao = CURRENT_TIMESTAMP, motivo_parada = %s WHERE id = %s",
            (motivo, implantacao_id)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'status_alterado', f'Implantação "{impl.get("nome_empresa", "N/A")}" parada. Motivo: {motivo}')
        flash('Implantação marcada como "Parada".', 'success')

    except Exception as e:
        print(f"Erro ao parar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao parar implantação: {e}', 'error')

    return redirect(dest_url)

@main_bp.route('/retomar_implantacao', methods=['POST'])
@login_required
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

    except Exception as e:
        print(f"Erro ao retomar implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao retomar implantação: {e}', 'error')

    return redirect(dest_url)

@main_bp.route('/atualizar_detalhes_empresa', methods=['POST'])
@login_required
def atualizar_detalhes_empresa():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    redirect_to = request.form.get('redirect_to', 'dashboard')

    dest_url = url_for('main.dashboard')
    if redirect_to == 'detalhes':
        dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id)

    if not query_db("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, usuario_cs_email), one=True):
        flash('Permissão negada.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        data_inicio_prod = request.form.get('data_inicio_producao') or None
        data_final_impl = request.form.get('data_final_implantacao') or None

        query = """
            UPDATE implantacoes
            SET responsavel_cliente = %s, cargo_responsavel = %s, telefone_responsavel = %s,
                email_responsavel = %s, data_inicio_producao = %s, data_final_implantacao = %s,
                chave_oamd = %s, catraca = %s, facial = %s
            WHERE id = %s AND usuario_cs = %s
        """
        args = (
            request.form.get('responsavel_cliente', '').strip(),
            request.form.get('cargo_responsavel', '').strip(),
            request.form.get('telefone_responsavel', '').strip(),
            request.form.get('email_responsavel', '').strip(),
            data_inicio_prod,
            data_final_impl,
            request.form.get('chave_oamd', '').strip(),
            request.form.get('catraca', '').strip(),
            request.form.get('facial', '').strip(),
            implantacao_id,
            usuario_cs_email
        )
        execute_db(query, args)
        logar_timeline(implantacao_id, usuario_cs_email, 'detalhes_alterados', 'Detalhes da empresa/cliente foram atualizados.')
        flash('Detalhes da implantação atualizados com sucesso!', 'success')

    except Exception as e:
        print(f"Erro ao atualizar detalhes (Impl. ID {implantacao_id}): {e}")
        flash('Erro ao atualizar detalhes.', 'error')

    return redirect(dest_url)

@main_bp.route('/excluir_implantacao', methods=['POST'])
@login_required
def excluir_implantacao():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')

    if not query_db("SELECT id FROM implantacoes WHERE id = %s AND usuario_cs = %s", (implantacao_id, usuario_cs_email), one=True):
        flash('Permissão negada.', 'error')
        return redirect(url_for('main.dashboard'))

    # Importa r2_client aqui, para evitar ciclo se chamado no topo
    from ..extensions import r2_client
    if not r2_client:
        flash("Erro: Serviço de armazenamento R2 não configurado. Não é possível excluir as imagens associadas.", "error")
        return redirect(request.referrer or url_for('main.dashboard'))

    try:
        # Busca imagens de comentários associadas a esta implantação
        comentarios_img = query_db(
            """
            SELECT c.imagem_url
            FROM comentarios c
            JOIN tarefas t ON c.tarefa_id = t.id
            WHERE t.implantacao_id = %s AND c.imagem_url IS NOT NULL AND c.imagem_url != ''
            """, (implantacao_id,)
        )

        public_url_base = current_app.config['CLOUDFLARE_PUBLIC_URL']
        bucket_name = current_app.config['CLOUDFLARE_BUCKET_NAME']

        for c in comentarios_img:
            imagem_url = c.get('imagem_url')
            if imagem_url and public_url_base and imagem_url.startswith(public_url_base):
                try:
                    object_key = imagem_url.replace(f"{public_url_base}/", "")
                    if object_key:
                        r2_client.delete_object(Bucket=bucket_name, Key=object_key)
                        print(f"Objeto R2 (comentário) excluído: {object_key}")
                except ClientError as e_delete:
                    print(f"Aviso: Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete.response['Error']['Code']}")
                except Exception as e_delete:
                    print(f"Aviso: Falha ao excluir imagem R2 (key: {object_key}). Erro: {e_delete}")

        # Exclui a implantação (isso excluirá tarefas e comentários em cascata no DB)
        execute_db("DELETE FROM implantacoes WHERE id = %s", (implantacao_id,))
        flash('Implantação e todos os dados associados foram excluídos com sucesso.', 'success')

    except Exception as e:
        print(f"Erro ao excluir implantação ID {implantacao_id}: {e}")
        flash('Erro ao excluir implantação.', 'error')

    return redirect(url_for('main.dashboard'))

# Rota para adicionar tarefa (Pendências)
@main_bp.route('/adicionar_tarefa', methods=['POST'])
@login_required
def adicionar_tarefa():
    usuario_cs_email = g.user_email
    implantacao_id = request.form.get('implantacao_id')
    tarefa_filho = request.form.get('tarefa_filho', '').strip()
    tarefa_pai = request.form.get('tarefa_pai', '').strip()
    tag = request.form.get('tag', '').strip()
    
    # --- CORREÇÃO: Adiciona a âncora para a aba de pendências ---
    dest_url = url_for('main.ver_implantacao', impl_id=implantacao_id, _anchor='pendencias-tab') 
    # -----------------------------------------------------------

    if not all([implantacao_id, tarefa_filho, tarefa_pai]):
        flash('Dados inválidos para adicionar tarefa (ID, Nome, Módulo).', 'error')
        # Redireciona de volta para a mesma página, mantendo a aba se possível
        return redirect(request.referrer or dest_url) 

    try:
        impl = query_db(
            "SELECT id, nome_empresa, status FROM implantacoes WHERE id = %s AND usuario_cs = %s",
            (implantacao_id, usuario_cs_email), one=True
        )
        if not impl:
            flash('Permissão negada ou implantação não encontrada.', 'error')
            return redirect(url_for('main.dashboard'))

        if impl.get('status') == 'finalizada':
            flash('Não é possível adicionar tarefas a implantações finalizadas.', 'warning')
            return redirect(dest_url) # Redireciona para a aba certa

        # Determina a próxima ordem
        max_ordem = query_db(
            "SELECT MAX(ordem) as max_o FROM tarefas WHERE implantacao_id = %s AND tarefa_pai = %s",
            (implantacao_id, tarefa_pai), one=True
        )
        nova_ordem = (max_ordem.get('max_o') or 0) + 1

        execute_db(
            "INSERT INTO tarefas (implantacao_id, tarefa_pai, tarefa_filho, tag, ordem, concluida) VALUES (%s, %s, %s, %s, %s, %s)",
            (implantacao_id, tarefa_pai, tarefa_filho, tag, nova_ordem, 0)
        )
        logar_timeline(implantacao_id, usuario_cs_email, 'tarefa_adicionada', f"Tarefa '{tarefa_filho}' adicionada ao módulo '{tarefa_pai}'.")
        flash('Tarefa adicionada com sucesso!', 'success')

    except Exception as e:
        print(f"Erro ao adicionar tarefa para implantação ID {implantacao_id}: {e}")
        flash(f'Erro ao adicionar tarefa: {e}', 'error')

    return redirect(dest_url) # Redireciona para a aba de pendências