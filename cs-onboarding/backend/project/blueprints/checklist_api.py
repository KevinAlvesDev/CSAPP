"""
API Blueprint para Checklist Hierárquico Infinito
Endpoints REST para gerenciar checklist com propagação de status e comentários
"""

from flask import Blueprint, request, jsonify, g, current_app
from datetime import datetime
import logging

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
def update_comment(item_id):
    """
    Atualiza o comentário de um item específico.
    
    Body (JSON):
        {
            "comment": "texto do comentário..."  // string - pode ser vazio para limpar
        }
    """
    try:
        item_id = validate_integer(item_id, min_value=1)
    except ValidationError as e:
        return jsonify({'ok': False, 'error': f'ID inválido: {str(e)}'}), 400
    
    if not request.is_json:
        return jsonify({'ok': False, 'error': 'Content-Type deve ser application/json'}), 400
    
    data = request.get_json() or {}
    comment_text = data.get('comment', '')
    
    # Comentário pode ser vazio (para limpar)
    if comment_text is None:
        comment_text = ''
    else:
        comment_text = str(comment_text).strip()
    
    usuario_email = g.user_email if hasattr(g, 'user_email') else None
    
    try:
        result = update_item_comment(item_id, comment_text, usuario_email)
        return jsonify({
            'ok': True,
            'item_id': result['item_id'],
            'comment': comment_text
        })
    except ValueError as e:
        api_logger.error(f"Erro de validação ao atualizar comentário do item {item_id}: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception as e:
        api_logger.error(f"Erro ao atualizar comentário do item {item_id}: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': 'Erro interno ao atualizar comentário'}), 500


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

