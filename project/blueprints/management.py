from flask import (
    Blueprint, request, g, jsonify
)

from ..db import query_db, execute_db
from ..blueprints.auth import login_required, permission_required
from ..constants import PERFIS_COM_GESTAO, PERFIS_DE_ACESSO, CARGOS_LISTA_COMPLETA

management_bp = Blueprint('management', __name__)

@management_bp.route('/manage_users', methods=['GET'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
def manage_users():
    """Retorna a lista de usuários e constantes para gerenciamento."""
    try:
        users = query_db("SELECT * FROM perfil_usuario ORDER BY nome")
        
        return jsonify(
            success=True,
            all_users=users,
            constants={
                'PERFIS_DE_ACESSO': PERFIS_DE_ACESSO,
                'CARGOS_LISTA_COMPLETA': CARGOS_LISTA_COMPLETA
            }
        )
    except Exception as e:
        print(f"Erro ao carregar lista de usuários: {e}")
        return jsonify(success=False, error=f"Erro ao carregar lista de usuários: {e}"), 500


@management_bp.route('/manage_users/update_profile', methods=['POST'])
@login_required
@permission_required(PERFIS_COM_GESTAO)
def update_user_profile():
    """Atualiza o perfil de um usuário (feito por um Admin/Gestor)."""
    
    data = request.json
    target_usuario_email = data.get('usuario_email')
    perfil_acesso = data.get('perfil_acesso')
    cargo = data.get('cargo')

    if not target_usuario_email or perfil_acesso not in PERFIS_DE_ACESSO or cargo not in CARGOS_LISTA_COMPLETA:
        return jsonify(success=False, error="Dados inválidos. Verifique o email, perfil e cargo."), 400
        
    try:
        execute_db(
            "UPDATE perfil_usuario SET perfil_acesso = %s, cargo = %s WHERE usuario = %s",
            (perfil_acesso, cargo, target_usuario_email)
        )
        
        updated_user = query_db("SELECT * FROM perfil_usuario WHERE usuario = %s", (target_usuario_email,), one=True)
        
        return jsonify(
            success=True, 
            message="Perfil do usuário atualizado com sucesso!",
            updated_user=updated_user
        )
        
    except Exception as e:
        print(f"Erro ao atualizar perfil de {target_usuario_email} por {g.user_email}: {e}")
        return jsonify(success=False, error=f"Erro ao atualizar perfil: {e}"), 500