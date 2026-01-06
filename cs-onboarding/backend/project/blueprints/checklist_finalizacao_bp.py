"""
API Blueprint para Checklist de Finalização
Endpoints REST para gerenciar checklist de pré-finalização
"""
from flask import Blueprint, g, jsonify, request
from flask_limiter.util import get_remote_address

from ..blueprints.auth import login_required
from ..config.logging_config import get_logger
from ..core.extensions import limiter
from ..domain.checklist_finalizacao_service import (
    criar_checklist_para_implantacao,
    marcar_item_checklist,
    obter_checklist_implantacao,
    obter_templates_checklist,
    validar_checklist_completo
)

checklist_finalizacao_bp = Blueprint('checklist_finalizacao', __name__, url_prefix='/api/checklist-finalizacao')
logger = get_logger('checklist_finalizacao')


@checklist_finalizacao_bp.route('/implantacao/<int:impl_id>', methods=['GET'])
@login_required
@limiter.limit("100 per minute", key_func=lambda: g.user_email or get_remote_address())
def get_checklist(impl_id):
    """
    Retorna o checklist de finalização de uma implantação.
    Se não existir, cria automaticamente baseado nos templates.
    """
    try:
        # Buscar checklist existente
        checklist = obter_checklist_implantacao(impl_id)
        
        # Se não existe, criar
        if checklist['total'] == 0:
            logger.info(f"Criando checklist para implantação {impl_id}")
            criar_checklist_para_implantacao(impl_id)
            checklist = obter_checklist_implantacao(impl_id)
        
        return jsonify({
            'ok': True,
            'checklist': checklist
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter checklist da implantação {impl_id}: {e}", exc_info=True)
        return jsonify({
            'ok': False,
            'error': 'Erro ao carregar checklist'
        }), 500


@checklist_finalizacao_bp.route('/item/<int:item_id>/toggle', methods=['POST'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def toggle_item(item_id):
    """
    Marca/desmarca um item do checklist como concluído.
    """
    try:
        data = request.get_json() or {}
        concluido = data.get('concluido', False)
        evidencia_tipo = data.get('evidencia_tipo')
        evidencia_url = data.get('evidencia_url')
        evidencia_conteudo = data.get('evidencia_conteudo')
        observacoes = data.get('observacoes')
        
        usuario = g.user_email
        
        success = marcar_item_checklist(
            item_id=item_id,
            concluido=concluido,
            usuario=usuario,
            evidencia_tipo=evidencia_tipo,
            evidencia_conteudo=evidencia_conteudo,
            evidencia_url=evidencia_url,
            observacoes=observacoes
        )
        
        if success:
            # AUDITORIA: Registrar a ação
            try:
                from ..domain.audit_service import log_action
                log_action(
                    action='CHECKLIST_TOGGLE',
                    target_type='checklist_item',
                    target_id=str(item_id),
                    changes={'concluido': concluido},
                    user_email=usuario
                )
            except Exception:
                pass

            return jsonify({
                'ok': True,
                'message': f'Item marcado como {"concluído" if concluido else "pendente"}'
            }), 200
        else:
            return jsonify({
                'ok': False,
                'error': 'Erro ao atualizar item'
            }), 500
            
    except Exception as e:
        logger.error(f"Erro ao marcar item {item_id}: {e}", exc_info=True)
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@checklist_finalizacao_bp.route('/implantacao/<int:impl_id>/validar', methods=['GET'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def validar_checklist(impl_id):
    """
    Valida se o checklist está completo (todos obrigatórios concluídos).
    """
    try:
        validado, mensagem = validar_checklist_completo(impl_id)
        
        return jsonify({
            'ok': True,
            'validado': validado,
            'mensagem': mensagem
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao validar checklist da implantação {impl_id}: {e}", exc_info=True)
        return jsonify({
            'ok': False,
            'error': 'Erro ao validar checklist'
        }), 500


@checklist_finalizacao_bp.route('/templates', methods=['GET'])
@login_required
@limiter.limit("50 per minute", key_func=lambda: g.user_email or get_remote_address())
def get_templates():
    """
    Retorna todos os templates de checklist disponíveis.
    """
    try:
        templates = obter_templates_checklist()
        
        return jsonify({
            'ok': True,
            'templates': templates
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao obter templates: {e}", exc_info=True)
        return jsonify({
            'ok': False,
            'error': 'Erro ao carregar templates'
        }), 500


@checklist_finalizacao_bp.route('/implantacao/<int:impl_id>/criar', methods=['POST'])
@login_required
@limiter.limit("10 per minute", key_func=lambda: g.user_email or get_remote_address())
def criar_checklist(impl_id):
    """
    Cria o checklist de finalização para uma implantação (forçado).
    """
    try:
        success = criar_checklist_para_implantacao(impl_id)
        
        if success:
            return jsonify({
                'ok': True,
                'message': 'Checklist criado com sucesso'
            }), 200
        else:
            return jsonify({
                'ok': False,
                'error': 'Erro ao criar checklist'
            }), 500
            
    except Exception as e:
        logger.error(f"Erro ao criar checklist para implantação {impl_id}: {e}", exc_info=True)
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500
