"""
API Blueprint para Checklist Hierárquico Infinito
Endpoints REST para gerenciar checklist com propagação de status e comentários
"""

from flask import Blueprint, request, jsonify, g
from ..blueprints.auth import login_required
from ..domain.checklist_service import (
    toggle_item_status,
    delete_checklist_item,
    get_checklist_tree,
    build_nested_tree,
    get_item_progress_stats
)
from ..common.validation import validate_integer, ValidationError
from ..config.logging_config import api_logger
from flask_limiter.util import get_remote_address
from ..core.extensions import limiter
from ..security.api_security import validate_api_origin

checklist_bp = Blueprint('checklist', __name__, url_prefix='/api/checklist')

@checklist_bp.route('/users', methods=['GET'])
@login_required
@validate_api_origin
def list_users():
    from ..db import query_db
    try:
        rows = query_db("SELECT usuario, COALESCE(nome, usuario) as nome FROM perfil_usuario ORDER BY nome ASC") or []
        return jsonify({'ok': True, 'users': rows})
    except Exception as e:
        api_logger.error(f"Erro ao listar usuários: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro ao listar usuários'}), 500


@checklist_bp.before_request
def _checklist_api_guard():
    """Validação de origem para todos os endpoints do checklist"""
    return validate_api_origin(lambda: None)()


@checklist_bp.route('/toggle/<int:item_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("1000 per minute", key_func=lambda: g.user_email or get_remote_address())
def toggle_item(item_id):
    """
    Alterna o status de um item do checklist (completo/pendente).
    Propaga mudanças para toda a hierarquia (cascata e bolha).

    Body (JSON opcional):
        {
            "completed": true  // boolean - novo status desejado
        }

    Se não fornecido, inverte o status atual.
    """
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    usuario_email = g.user_email if hasattr(g, 'user_email') else None

    try:
        new_status = None
        if request.is_json:
            data = request.get_json() or {}
            completed_param = data.get('completed')
            if completed_param is not None:
                new_status = bool(completed_param)

        if new_status is None:
            from ..db import query_db
            current_item = query_db(
                "SELECT completed FROM checklist_items WHERE id = %s",
                (item_id,),
                one=True
            )
            if not current_item:
                return jsonify({'ok': False, 'error': f'Item {item_id} não encontrado'}), 404
            new_status = not (current_item.get('completed') or False)

        result = toggle_item_status(item_id, new_status, usuario_email)

        return jsonify({
            'ok': True,
            'item_id': item_id,
            'completed': new_status,
            'items_updated': result['items_updated'],
            'progress': result['progress'],
            'downstream_updated': result.get('downstream_updated', 0),
            'upstream_updated': result.get('upstream_updated', 0)
        })

    except ValueError as e:
        api_logger.error(f"Erro de validação ao fazer toggle do item {item_id}: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        api_logger.error(f"Erro ao fazer toggle do item {item_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao alterar status'}), 500


@checklist_bp.route('/comment/<int:item_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("1000 per minute", key_func=lambda: g.user_email or get_remote_address())
def add_comment(item_id):
    """
    Adiciona um novo comentário ao histórico de um item.

    Body (JSON):
        {
            "texto": "texto do comentário...",
            "visibilidade": "interno" ou "externo"
        }
    """
    from datetime import datetime
    from ..db import query_db, execute_db
    from ..common.validation import sanitize_string
    
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    if not request.is_json:
        return jsonify({'ok': False, 'error': 'Content-Type deve ser application/json'}), 400

    data = request.get_json() or {}
    texto = data.get('texto', '') or data.get('comment', '')
    visibilidade = data.get('visibilidade', 'interno')

    if not texto or not texto.strip():
        return jsonify({'ok': False, 'error': 'O texto do comentário é obrigatório'}), 400
    
    texto = sanitize_string(texto.strip(), max_length=8000, min_length=1)
    
    if visibilidade not in ('interno', 'externo'):
        visibilidade = 'interno'

    usuario_email = g.user_email if hasattr(g, 'user_email') else None

    try:
        item = query_db(
            "SELECT id, implantacao_id FROM checklist_items WHERE id = %s",
            (item_id,),
            one=True
        )
        if not item:
            return jsonify({'ok': False, 'error': f'Item {item_id} não encontrado'}), 404
        
        try:
            from project.database.db_pool import get_db_connection
            conn_check, db_type_check = get_db_connection()
            if db_type_check == 'sqlite':
                cursor_check = conn_check.cursor()
                cursor_check.execute("PRAGMA table_info(comentarios_h)")
                colunas_existentes = [row[1] for row in cursor_check.fetchall()]
                if 'checklist_item_id' not in colunas_existentes:
                    cursor_check.execute("ALTER TABLE comentarios_h ADD COLUMN checklist_item_id INTEGER")
                    conn_check.commit()
                conn_check.close()
        except Exception:
            pass
        
        agora = datetime.now()
        execute_db(
            """
            INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, data_criacao, visibilidade)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (item_id, usuario_email, texto, agora, visibilidade)
        )
        
        novo_comentario = query_db(
            """
            SELECT c.id, c.texto, c.usuario_cs, c.data_criacao, c.visibilidade,
                   COALESCE(p.nome, c.usuario_cs) as usuario_nome
            FROM comentarios_h c
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE c.checklist_item_id = %s
            ORDER BY c.id DESC
            LIMIT 1
            """,
            (item_id,),
            one=True
        )
        
        data_criacao = novo_comentario['data_criacao']
        if data_criacao:
            if hasattr(data_criacao, 'isoformat'):
                data_criacao = data_criacao.isoformat()
            else:
                data_criacao = str(data_criacao)
        
        return jsonify({
            'ok': True,
            'item_id': item_id,
            'comentario': {
                'id': novo_comentario['id'],
                'texto': novo_comentario['texto'],
                'usuario_cs': novo_comentario['usuario_cs'],
                'usuario_nome': novo_comentario['usuario_nome'],
                'data_criacao': data_criacao,
                'visibilidade': novo_comentario['visibilidade']
            }
        })
    except ValueError as e:
        api_logger.error(f"Erro de validação ao adicionar comentário ao item {item_id}: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        api_logger.error(f"Erro ao adicionar comentário ao item {item_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao adicionar comentário'}), 500


@checklist_bp.route('/implantacao/<int:impl_id>/comments', methods=['GET'])
@login_required
@validate_api_origin
def get_implantacao_comments(impl_id):
    """
    Retorna todos os comentários das tarefas de uma implantação.
    Ordenados cronologicamente (mais antigo para mais recente).
    Paginação via query params page/per_page.
    """
    from ..db import query_db
    
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        if page < 1: page = 1
        if per_page < 1: per_page = 20
        if per_page > 100: per_page = 100
    except ValueError:
        page = 1
        per_page = 20
        
    offset = (page - 1) * per_page
    
    try:
        # Query total count
        count_query = """
            SELECT COUNT(*) as total
            FROM comentarios_h c
            JOIN checklist_items ci ON c.checklist_item_id = ci.id
            WHERE ci.implantacao_id = %s
        """
        total_res = query_db(count_query, (impl_id,), one=True)
        total = total_res['total'] if total_res else 0
        
        # Query comments
        # Inclui nome da tarefa
        comments_query = """
            SELECT 
                c.id, c.texto, c.usuario_cs, c.data_criacao, c.visibilidade,
                ci.id as item_id, ci.title as item_title,
                COALESCE(p.nome, c.usuario_cs) as usuario_nome
            FROM comentarios_h c
            JOIN checklist_items ci ON c.checklist_item_id = ci.id
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE ci.implantacao_id = %s
            ORDER BY c.data_criacao ASC
            LIMIT %s OFFSET %s
        """
        
        comments = query_db(comments_query, (impl_id, per_page, offset))
        
        # Format dates
        formatted_comments = []
        for c in comments:
            c_dict = dict(c)
            if c_dict.get('data_criacao'):
                 dt = c_dict['data_criacao']
                 c_dict['data_criacao'] = dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
            formatted_comments.append(c_dict)
            
        return jsonify({
            'ok': True,
            'comments': formatted_comments,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        api_logger.error(f"Erro ao buscar comentários da implantação {impl_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao buscar comentários'}), 500


@checklist_bp.route('/comments/<int:item_id>', methods=['GET'])
@login_required
@validate_api_origin
def get_comments(item_id):
    """
    Retorna o histórico de comentários de um item.
    """
    from ..db import query_db
    
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    try:
        comentarios = query_db(
            """
            SELECT c.id, c.texto, c.usuario_cs, c.data_criacao, c.visibilidade, c.imagem_url,
                   COALESCE(p.nome, c.usuario_cs) as usuario_nome
            FROM comentarios_h c
            LEFT JOIN perfil_usuario p ON c.usuario_cs = p.usuario
            WHERE c.checklist_item_id = %s
            ORDER BY c.data_criacao DESC
            """,
            (item_id,)
        ) or []
        
        item_info = query_db(
            """
            SELECT i.email_responsavel
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE ci.id = %s
            """,
            (item_id,),
            one=True
        )
        email_responsavel = item_info.get('email_responsavel', '') if item_info else ''
        
        comentarios_formatados = []
        for c in comentarios:
            data_criacao = c['data_criacao']
            if data_criacao:
                if hasattr(data_criacao, 'isoformat'):
                    data_criacao = data_criacao.isoformat()
                else:
                    data_criacao = str(data_criacao)
            
            comentarios_formatados.append({
                'id': c['id'],
                'texto': c['texto'],
                'usuario_cs': c['usuario_cs'],
                'usuario_nome': c['usuario_nome'],
                'data_criacao': data_criacao,
                'visibilidade': c['visibilidade'],
                'imagem_url': c.get('imagem_url'),
                'email_responsavel': email_responsavel
            })
        
        return jsonify({
            'ok': True,
            'item_id': item_id,
            'comentarios': comentarios_formatados,
            'email_responsavel': email_responsavel
        })
    except Exception as e:
        api_logger.error(f"Erro ao buscar comentários do item {item_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao buscar comentários'}), 500


@checklist_bp.route('/comment/<int:comentario_id>/email', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("10 per minute", key_func=lambda: g.user_email or get_remote_address())
def send_comment_email(comentario_id):
    """
    Envia um comentário externo por email ao responsável da implantação.
    """
    from ..db import query_db
    from ..mail.email_utils import send_external_comment_notification
    
    try:
        comentario_id = validate_integer(comentario_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    try:
        dados = query_db(
            """
            SELECT c.id, c.texto, c.visibilidade, c.usuario_cs,
                   ci.title as tarefa_nome,
                   i.id as impl_id, i.nome_empresa, i.email_responsavel
            FROM comentarios_h c
            JOIN checklist_items ci ON c.checklist_item_id = ci.id
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE c.id = %s
            """,
            (comentario_id,),
            one=True
        )
        
        if not dados:
            return jsonify({'ok': False, 'error': 'Comentário não encontrado'}), 404
        
        if dados['visibilidade'] != 'externo':
            return jsonify({'ok': False, 'error': 'Apenas comentários externos podem ser enviados por email'}), 400
        
        if not dados['email_responsavel']:
            return jsonify({'ok': False, 'error': 'Email do responsável não configurado. Configure em "Editar Detalhes".'}), 400
        
        implantacao = {
            'id': dados['impl_id'],
            'nome_empresa': dados['nome_empresa'],
            'email_responsavel': dados['email_responsavel']
        }
        comentario = {
            'id': dados['id'],
            'texto': dados['texto'],
            'tarefa_filho': dados['tarefa_nome'],
            'usuario_cs': dados['usuario_cs']
        }
        
        result = send_external_comment_notification(implantacao, comentario)
        
        if result:
            return jsonify({'ok': True, 'message': 'Email enviado com sucesso'})
        else:
            return jsonify({'ok': False, 'error': 'Falha ao enviar email'}), 500
            
    except Exception as e:
        api_logger.error(f"Erro ao enviar email do comentário {comentario_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao enviar email'}), 500


@checklist_bp.route('/comment/<int:comentario_id>', methods=['DELETE'])
@login_required
@validate_api_origin
def delete_comment(comentario_id):
    """
    Exclui um comentário (apenas o próprio autor ou gestores).
    """
    from ..db import query_db, execute_db
    from ..constants import PERFIS_COM_GESTAO
    
    try:
        comentario_id = validate_integer(comentario_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    usuario_email = g.user_email if hasattr(g, 'user_email') else None

    try:
        comentario = query_db(
            "SELECT id, usuario_cs FROM comentarios_h WHERE id = %s",
            (comentario_id,),
            one=True
        )
        
        if not comentario:
            return jsonify({'ok': False, 'error': 'Comentário não encontrado'}), 404
        
        is_owner = comentario['usuario_cs'] == usuario_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        if not (is_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada'}), 403
        
        # Buscar contexto para timeline
        item_ctx = query_db(
            """
            SELECT ci.implantacao_id, ci.title AS item_nome
            FROM comentarios_h c
            JOIN checklist_items ci ON c.checklist_item_id = ci.id
            WHERE c.id = %s
            """,
            (comentario_id,),
            one=True
        ) or {}

        execute_db("DELETE FROM comentarios_h WHERE id = %s", (comentario_id,))
        try:
            from ..db import logar_timeline
            impl_id = item_ctx.get('implantacao_id')
            if impl_id:
                detalhe = f"Comentário excluído em '{item_ctx.get('item_nome','')}' (ID {comentario_id})."
                logar_timeline(impl_id, usuario_email, 'comentario_excluido', detalhe)
        except Exception:
            pass
        
        return jsonify({'ok': True, 'message': 'Comentário excluído'})
    except Exception as e:
        api_logger.error(f"Erro ao excluir comentário {comentario_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao excluir comentário'}), 500


@checklist_bp.route('/delete/<int:item_id>', methods=['POST'])
@login_required
@validate_api_origin
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def delete_item(item_id):
    """
    Exclui um item do checklist e toda a sua hierarquia (apenas gestores ou dono da implantação).
    """
    from ..db import query_db
    from ..constants import PERFIS_COM_GESTAO
    
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    usuario_email = g.user_email if hasattr(g, 'user_email') else None

    try:
        # Verificar permissões: Apenas dono da implantação ou gestor pode excluir itens
        item_info = query_db(
            """
            SELECT ci.id, ci.title, ci.implantacao_id, i.usuario_cs, i.status
            FROM checklist_items ci
            JOIN implantacoes i ON ci.implantacao_id = i.id
            WHERE ci.id = %s
            """,
            (item_id,),
            one=True
        )
        
        if not item_info:
            return jsonify({'ok': False, 'error': 'Item não encontrado'}), 404
        
        if item_info.get('status') in ['finalizada', 'parada', 'cancelada']:
            return jsonify({'ok': False, 'error': 'Implantação bloqueada para alterações.'}), 400
        
        is_owner = item_info['usuario_cs'] == usuario_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        if not (is_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada. Apenas o responsável ou gestores podem excluir itens.'}), 403
        
        result = delete_checklist_item(item_id, usuario_email)

        if result.get('ok'):
            # Log to timeline for compatibility with frontend
            from ..core.api import logar_timeline, format_date_iso_for_json
            
            log_details = f"Item '{item_info.get('title', '')}' foi excluído."
            logar_timeline(item_info['implantacao_id'], usuario_email, 'tarefa_excluida', log_details)
            
            # Fetch the log entry to return to frontend
            nome_usuario = g.perfil.get('nome', usuario_email) if g.perfil else usuario_email
            log_exclusao = query_db(
                "SELECT *, %s as usuario_nome FROM timeline_log WHERE implantacao_id = %s AND tipo_evento = 'tarefa_excluida' ORDER BY id DESC LIMIT 1",
                (nome_usuario, item_info['implantacao_id']), one=True
            )
            if log_exclusao:
                log_exclusao['data_criacao'] = format_date_iso_for_json(log_exclusao.get('data_criacao'))
            
            result['log_exclusao'] = log_exclusao
            result['novo_progresso'] = result.get('progress') # Alias for compatibility
        
        return jsonify(result)
        
    except Exception as e:
        api_logger.error(f"Erro ao excluir item {item_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': f'Erro interno ao excluir item: {e}'}), 500


@checklist_bp.route('/tree', methods=['GET'])
@login_required
@validate_api_origin
def get_tree():
    """
    Retorna a árvore completa do checklist.

    Query Parameters:
        implantacao_id (int, opcional): Filtrar por implantação
        root_item_id (int, opcional): Retornar sub-árvore a partir de um item raiz
        format (string, opcional): 'flat' (padrão) ou 'nested' para árvore aninhada

    Returns:
        JSON com lista de itens (flat ou nested) incluindo progresso (X/Y) de cada item
    """
    try:
        implantacao_id = request.args.get('implantacao_id', type=int)
        root_item_id = request.args.get('root_item_id', type=int)
        format_type = request.args.get('format', 'flat').lower()

        if implantacao_id:
            implantacao_id = validate_integer(implantacao_id, min_value=1)
        if root_item_id:
            root_item_id = validate_integer(root_item_id, min_value=1)

        if format_type not in ['flat', 'nested']:
            return jsonify({'ok': False, 'error': 'format deve ser "flat" ou "nested"'}), 400

        flat_items = get_checklist_tree(
            implantacao_id=implantacao_id,
            root_item_id=root_item_id,
            include_progress=True
        )

        global_progress = None
        if implantacao_id:
            from ..db import query_db
            from flask import current_app
            
            is_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
            
            if is_sqlite:
                progress_query = """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
                    FROM checklist_items ci
                    WHERE ci.implantacao_id = ?
                    AND NOT EXISTS (
                        SELECT 1 FROM checklist_items filho 
                        WHERE filho.parent_id = ci.id
                        AND filho.implantacao_id = ?
                    )
                """
                progress_result = query_db(progress_query, (implantacao_id, implantacao_id), one=True)
            else:
                progress_query = """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completed
                    FROM checklist_items ci
                    WHERE ci.implantacao_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM checklist_items filho 
                        WHERE filho.parent_id = ci.id
                        AND filho.implantacao_id = %s
                    )
                """
                progress_result = query_db(progress_query, (implantacao_id, implantacao_id), one=True)
            
            if progress_result:
                total = int(progress_result.get('total', 0) or 0)
                completed = int(progress_result.get('completed', 0) or 0)
                if total > 0:
                    global_progress = round((completed / total) * 100, 2)
                else:
                    global_progress = 100.0

        if format_type == 'nested':
            nested_tree = build_nested_tree(flat_items)
            return jsonify({
                'ok': True,
                'format': 'nested',
                'items': nested_tree,
                'global_progress': global_progress
            })
        else:
            return jsonify({
                'ok': True,
                'format': 'flat',
                'items': flat_items,
                'global_progress': global_progress
            })

    except ValidationError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        api_logger.error(f"Erro ao buscar árvore do checklist: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao buscar checklist'}), 500


@checklist_bp.route('/item/<int:item_id>/progress', methods=['GET'])
@login_required
@validate_api_origin
def get_item_progress(item_id):
    """
    Retorna as estatísticas de progresso de um item específico (X/Y).

    Returns:
        {
            "ok": true,
            "item_id": 1,
            "progress": {
                "total": 6,
                "completed": 0,
                "has_children": true
            },
            "progress_label": "0/6"
        }
    """
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400

    try:
        stats = get_item_progress_stats(item_id)
        return jsonify({
            'ok': True,
            'item_id': item_id,
            'progress': stats,
            'progress_label': f"{stats['completed']}/{stats['total']}" if stats['has_children'] else None
        })
    except Exception as e:
        api_logger.error(f"Erro ao buscar progresso do item {item_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao buscar progresso'}), 500
@checklist_bp.route('/item/<int:item_id>/responsavel', methods=['PATCH'])
@login_required
@validate_api_origin
@limiter.limit("200 per minute", key_func=lambda: g.user_email or get_remote_address())
def update_responsavel(item_id):
    from ..db import db_transaction_with_lock
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    if not request.is_json:
        return jsonify({'ok': False, 'error': 'Content-Type deve ser application/json'}), 400
    data = request.get_json() or {}
    novo_resp = (data.get('responsavel') or '').strip()
    if not novo_resp:
        return jsonify({'ok': False, 'error': 'Responsável é obrigatório'}), 400
    usuario_email = g.user_email if hasattr(g, 'user_email') else None
    from datetime import datetime
    with db_transaction_with_lock() as (conn, cursor, db_type):
        try:
            q = "SELECT responsavel FROM checklist_items WHERE id = %s"
            if db_type == 'sqlite': q = q.replace('%s', '?')
            cursor.execute(q, (item_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'ok': False, 'error': 'Item não encontrado'}), 404
            old_resp = row[0] if not hasattr(row, 'keys') else row['responsavel']
            uq = "UPDATE checklist_items SET responsavel = %s, updated_at = %s WHERE id = %s"
            if db_type == 'sqlite': uq = uq.replace('%s', '?')
            cursor.execute(uq, (novo_resp, datetime.now(), item_id))
            try:
                ih = "INSERT INTO checklist_responsavel_history (checklist_item_id, old_responsavel, new_responsavel, changed_by) VALUES (%s, %s, %s, %s)"
                if db_type == 'sqlite': ih = ih.replace('%s', '?')
                cursor.execute(ih, (item_id, old_resp, novo_resp, usuario_email))
            except Exception:
                pass
            try:
                from ..db import logar_timeline
                # Recuperar impl_id
                qi = "SELECT implantacao_id FROM checklist_items WHERE id = %s"
                if db_type == 'sqlite': qi = qi.replace('%s', '?')
                cursor.execute(qi, (item_id,))
                irow = cursor.fetchone()
                impl_id = irow[0] if not hasattr(irow, 'keys') else irow['implantacao_id']
                detalhe = f"Item {item_id} responsavel_alterado: {old_resp or ''} -> {novo_resp}"
                logar_timeline(impl_id, usuario_email, 'responsavel_alterado', detalhe)
            except Exception:
                pass
            return jsonify({'ok': True, 'item_id': item_id, 'responsavel': novo_resp})
        except Exception as e:
            api_logger.error(f"Erro ao atualizar responsável do item {item_id}: {e}", exc_info=True)
            return jsonify({'ok': False, 'error': 'Erro interno ao atualizar responsável'}), 500


@checklist_bp.route('/item/<int:item_id>/prazos', methods=['PATCH', 'POST'])
@login_required
@validate_api_origin
@limiter.limit("200 per minute", key_func=lambda: g.user_email or get_remote_address())
def update_prazos(item_id):
    from ..db import db_transaction_with_lock
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    if not request.is_json:
        return jsonify({'ok': False, 'error': 'Content-Type deve ser application/json'}), 400
    data = request.get_json() or {}
    nova_prev = (data.get('nova_previsao') or '').strip()
    if not nova_prev:
        return jsonify({'ok': False, 'error': 'Nova Previsão é obrigatória'}), 400
    from datetime import datetime
    try:
        s = nova_prev.strip()
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        nova_dt = datetime.fromisoformat(s)
    except Exception:
        return jsonify({'ok': False, 'error': 'Formato de data inválido (ISO8601)'}), 400
    usuario_email = g.user_email if hasattr(g, 'user_email') else None
    with db_transaction_with_lock() as (conn, cursor, db_type):
        try:
            q = "SELECT implantacao_id, previsao_original FROM checklist_items WHERE id = %s"
            if db_type == 'sqlite': q = q.replace('%s', '?')
            cursor.execute(q, (item_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'ok': False, 'error': 'Item não encontrado'}), 404
            prev_orig = None
            if hasattr(row, 'keys'):
                prev_orig = row['previsao_original']
            else:
                prev_orig = row[1]
            uq = "UPDATE checklist_items SET nova_previsao = %s, updated_at = %s WHERE id = %s"
            if db_type == 'sqlite': uq = uq.replace('%s', '?')
            cursor.execute(uq, (nova_dt, datetime.now(), item_id))
            try:
                from ..db import logar_timeline
                impl_id = row['implantacao_id'] if hasattr(row, 'keys') else row[0]
                detalhe = f"Item {item_id} nova_previsao: {nova_dt.isoformat()}"
                logar_timeline(impl_id, usuario_email, 'prazo_alterado', detalhe)
            except Exception:
                pass
            return jsonify({'ok': True, 'item_id': item_id, 'nova_previsao': nova_dt.isoformat(), 'previsao_original': prev_orig if not hasattr(prev_orig, 'isoformat') else prev_orig.isoformat()})
        except Exception as e:
            api_logger.error(f"Erro ao atualizar prazos do item {item_id}: {e}", exc_info=True)
            return jsonify({'ok': False, 'error': 'Erro interno ao atualizar prazos'}), 500


@checklist_bp.route('/item/<int:item_id>/responsavel/history', methods=['GET'])
@login_required
@validate_api_origin
def get_responsavel_history(item_id):
    from ..db import query_db
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    try:
        entries = query_db(
            """
            SELECT id, old_responsavel, new_responsavel, changed_by, changed_at
            FROM checklist_responsavel_history
            WHERE checklist_item_id = %s
            ORDER BY changed_at DESC
            """,
            (item_id,)
        ) or []
        for e in entries:
            if e.get('changed_at') and hasattr(e['changed_at'], 'isoformat'):
                e['changed_at'] = e['changed_at'].isoformat()
        return jsonify({'ok': True, 'item_id': item_id, 'history': entries})
    except Exception as e:
        api_logger.error(f"Erro ao buscar histórico de responsável do item {item_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao buscar histórico'}), 500

@checklist_bp.route('/item/<int:item_id>/prazos/history', methods=['GET'])
@login_required
@validate_api_origin
def get_prazos_history(item_id):
    from ..db import query_db
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    try:
        impl = query_db("SELECT implantacao_id FROM checklist_items WHERE id = %s", (item_id,), one=True)
        if not impl:
            return jsonify({'ok': False, 'error': 'Item não encontrado'}), 404
        impl_id = impl['implantacao_id']
        logs = query_db(
            """
            SELECT id, usuario_cs, detalhes, data_criacao
            FROM timeline_log
            WHERE implantacao_id = %s AND tipo_evento = 'prazo_alterado'
            ORDER BY id DESC
            """,
            (impl_id,)
        ) or []
        entries = []
        for l in logs:
            det = l.get('detalhes') or ''
            if det.startswith(f"Item {item_id} "):
                entries.append({
                    'usuario_cs': l.get('usuario_cs'),
                    'detalhes': det,
                    'data_criacao': l.get('data_criacao').isoformat() if hasattr(l.get('data_criacao'), 'isoformat') else str(l.get('data_criacao'))
                })
        return jsonify({'ok': True, 'history': entries})
    except Exception as e:
        api_logger.error(f"Erro ao buscar histórico de prazos do item {item_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao buscar histórico de prazos'}), 500
