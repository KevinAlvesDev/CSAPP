"""
API Blueprint para Checklist Hierárquico Infinito
Endpoints REST para gerenciar checklist com propagação de status e comentários
"""

from flask import Blueprint, request, jsonify, g
from ..blueprints.auth import login_required
from ..domain.checklist_service import (
    toggle_item_status,
    update_item_comment,
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
        # Verificar se foi fornecido um novo status no body
        new_status = None
        if request.is_json:
            data = request.get_json() or {}
            completed_param = data.get('completed')
            if completed_param is not None:
                new_status = bool(completed_param)

        # Se não foi fornecido, buscar o status atual e inverter
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

        # Executar toggle com propagação
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
        # Verificar se o item existe
        item = query_db(
            "SELECT id, implantacao_id FROM checklist_items WHERE id = %s",
            (item_id,),
            one=True
        )
        if not item:
            return jsonify({'ok': False, 'error': f'Item {item_id} não encontrado'}), 404
        
        # Garantir que a coluna checklist_item_id existe (para SQLite)
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
        
        # Inserir comentário
        agora = datetime.now()
        execute_db(
            """
            INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, data_criacao, visibilidade)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (item_id, usuario_email, texto, agora, visibilidade)
        )
        
        # Buscar o comentário inserido
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
        
        # Formatar data (pode ser string no SQLite ou datetime no PostgreSQL)
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
        # Buscar comentários
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
        
        # Buscar email do responsável da implantação
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
        
        # Formatar comentários
        comentarios_formatados = []
        for c in comentarios:
            # Formatar data (pode ser string no SQLite ou datetime no PostgreSQL)
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
        # Buscar comentário com dados da implantação
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
        
        # Preparar dados para envio
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
        
        # Enviar email
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
        # Buscar comentário
        comentario = query_db(
            "SELECT id, usuario_cs FROM comentarios_h WHERE id = %s",
            (comentario_id,),
            one=True
        )
        
        if not comentario:
            return jsonify({'ok': False, 'error': 'Comentário não encontrado'}), 404
        
        # Verificar permissão
        is_owner = comentario['usuario_cs'] == usuario_email
        is_manager = g.perfil and g.perfil.get('perfil_acesso') in PERFIS_COM_GESTAO
        
        if not (is_owner or is_manager):
            return jsonify({'ok': False, 'error': 'Permissão negada'}), 403
        
        # Excluir
        execute_db("DELETE FROM comentarios_h WHERE id = %s", (comentario_id,))
        
        return jsonify({'ok': True, 'message': 'Comentário excluído'})
    except Exception as e:
        api_logger.error(f"Erro ao excluir comentário {comentario_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao excluir comentário'}), 500


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

        # Validar parâmetros
        if implantacao_id:
            implantacao_id = validate_integer(implantacao_id, min_value=1)
        if root_item_id:
            root_item_id = validate_integer(root_item_id, min_value=1)

        if format_type not in ['flat', 'nested']:
            return jsonify({'ok': False, 'error': 'format deve ser "flat" ou "nested"'}), 400

        # Buscar árvore (sempre incluir progresso)
        flat_items = get_checklist_tree(
            implantacao_id=implantacao_id,
            root_item_id=root_item_id,
            include_progress=True
        )

        # Calcular progresso global se houver implantacao_id
        global_progress = None
        if implantacao_id:
            from ..db import query_db
            progress_result = query_db(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN completed = true THEN 1 END) as completed
                FROM checklist_items
                WHERE implantacao_id = %s
                """,
                (implantacao_id,),
                one=True
            )
            if progress_result:
                total = progress_result.get('total', 0) or 0
                completed = progress_result.get('completed', 0) or 0
                if total > 0:
                    global_progress = round((completed / total) * 100, 2)
                else:
                    global_progress = 100.0

        # Formatar resposta
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
