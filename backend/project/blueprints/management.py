# testo/CSAPP/backend/project/blueprints/management.py
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, jsonify, current_app
)
from ..blueprints.auth import admin_required
from ..utils import load_profiles_list
from ..db import query_db, execute_db
from ..logging_config import app_logger, security_logger

management_bp = Blueprint('management', __name__, url_prefix='/management')

@management_bp.before_request
@admin_required
def before_request():
    """Protege todas as rotas de gerenciamento."""
    pass

@management_bp.route('/users')
def manage_users():
    """Renderiza a página principal de gerenciamento de usuários."""
    try:
        users_data = load_profiles_list(exclude_self=False)
        
        # Garante que 'perfis_acesso' é uma lista (ex: de constants.py)
        perfis_disponiveis = current_app.config.get('PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador'])
        
        return render_template('manage_users.html', 
                               users=users_data, 
                               perfis_disponiveis=perfis_disponiveis)
    except Exception as e:
        app_logger.error(f"Erro ao carregar manage_users: {e}")
        flash("Erro ao carregar dados dos usuários.", "error")
        return redirect(url_for('main.dashboard'))

@management_bp.route('/users/update_profile', methods=['POST'])
def update_user_profile():
    """Atualiza o perfil de acesso de um usuário."""
    data = request.get_json()
    if not data or 'usuario' not in data or 'perfil' not in data:
        return jsonify({'ok': False, 'error': 'Dados incompletos'}), 400

    usuario_alvo = data['usuario']
    novo_perfil = data['perfil']
    
    # Valida o perfil (deve estar na lista de constantes)
    perfis_disponiveis = current_app.config.get('PERFIS_DE_ACESSO', [])
    if novo_perfil not in perfis_disponiveis:
        security_logger.warning(f"Tentativa de atribuir perfil inválido '{novo_perfil}' para {usuario_alvo} por {g.user_email}")
        return jsonify({'ok': False, 'error': 'Perfil de acesso inválido'}), 400

    # Regra de segurança: não pode alterar o próprio perfil por esta rota
    if usuario_alvo == g.user_email:
        security_logger.warning(f"Admin {g.user_email} tentou alterar o próprio perfil via 'update_user_profile'")
        return jsonify({'ok': False, 'error': 'Não pode alterar o seu próprio perfil por esta interface.'}), 403

    try:
        # Verifica se o usuário existe
        user_exists = query_db("SELECT 1 FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,), one=True)
        if not user_exists:
            return jsonify({'ok': False, 'error': 'Usuário não encontrado'}), 404
            
        execute_db(
            "UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s",
            (novo_perfil, usuario_alvo)
        )
        app_logger.info(f"Admin {g.user_email} atualizou o perfil de {usuario_alvo} para {novo_perfil}")
        return jsonify({'ok': True})
        
    except Exception as e:
        app_logger.error(f"Erro ao atualizar perfil de {usuario_alvo} por {g.user_email}: {e}")
        return jsonify({'ok': False, 'error': f'Erro de banco de dados: {e}'}), 500

@management_bp.route('/users/delete', methods=['POST'])
def delete_user():
    """Exclui um usuário (Ação destrutiva)."""
    data = request.get_json()
    if not data or 'usuario' not in data:
        return jsonify({'ok': False, 'error': 'Usuário não especificado'}), 400
        
    usuario_alvo = data['usuario']
    
    # Regra de segurança: não pode excluir a si mesmo
    if usuario_alvo == g.user_email:
        security_logger.warning(f"Admin {g.user_email} tentou se auto-excluir.")
        return jsonify({'ok': False, 'error': 'Não pode excluir a si mesmo.'}), 403

    try:
        # TODO: Lógica de exclusão de arquivos no R2 (fotos, etc)
        
        # Excluir dados em cascata (depende da configuração do BD)
        # Se não houver ON DELETE CASCADE, precisamos excluir manualmente:
        # 1. Comentários, 2. Tarefas (se associadas), 3. Implantações (re-atribuir?), 4. Perfil, 5. Usuário
        
        # Exclusão simples (assumindo que o BD cuida das FKs ou não é crítico)
        execute_db("DELETE FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,))
        execute_db("DELETE FROM usuarios WHERE usuario = %s", (usuario_alvo,))
        
        app_logger.info(f"Admin {g.user_email} EXCLUIU o usuário {usuario_alvo}")
        return jsonify({'ok': True})
        
    except Exception as e:
        app_logger.error(f"Erro ao excluir usuário {usuario_alvo} por {g.user_email}: {e}")
        return jsonify({'ok': False, 'error': f'Erro de banco de dados: {e}'}), 500