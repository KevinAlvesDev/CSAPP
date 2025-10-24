from flask import Blueprint, render_template, request, flash, redirect, url_for, g, jsonify
from ..blueprints.auth import permission_required
from ..db import query_db, execute_db
from ..constants import PERFIS_ACESSO_LIST, PERFIS_COM_GESTAO, PERFIL_ADMIN, ADMIN_EMAIL

management_bp = Blueprint('management', __name__, url_prefix='/management')

@management_bp.route('/users', methods=['GET'])
@permission_required(PERFIS_COM_GESTAO)
def manage_users():
    """Lista todos os usuários para gerenciamento do Perfil de Acesso (Retorna HTML para Modal)."""
    try:
        # Busca todos os perfis de usuário, ordenados pelo Perfil de Acesso
        users = query_db(
            """
            SELECT usuario, nome, cargo, perfil_acesso, 
                   impl_andamento_total, impl_finalizadas, 
                   data_criacao
            FROM perfil_usuario 
            ORDER BY CASE 
                WHEN perfil_acesso = 'Administrador' THEN 1
                WHEN perfil_acesso IS NULL OR perfil_acesso = '' THEN 2
                ELSE 3
            END, nome
            """,
            ()
        )
        
        # Renderiza APENAS o conteúdo que será injetado no Modal do base.html
        return render_template(
            '_manage_users_content.html',
            users=users,
            perfis_list=PERFIS_ACESSO_LIST, 
            user_info=g.user
        )
        
    except Exception as e:
        print(f"ERRO ao carregar lista de usuários: {e}")
        # Retorna erro em texto para o Fetch
        return f'<div class="alert alert-danger">Erro ao carregar dados: {e}</div>', 500

@management_bp.route('/users/update_perfil', methods=['POST'])
@permission_required(PERFIS_COM_GESTAO)
def update_user_perfil():
    """Atualiza o perfil de acesso de um usuário específico (Ação via POST)."""
    target_user_email = request.form.get('usuario_email')
    new_perfil_acesso = request.form.get('new_perfil')
    
    # Validação Básica
    if not target_user_email or new_perfil_acesso not in PERFIS_ACESSO_LIST:
        flash("Dados inválidos para a atualização.", "error")
        return redirect(url_for('management.manage_users'))

    final_perfil = new_perfil_acesso if new_perfil_acesso != 'Nenhum' else None
    
    # Prevenção: Administrador principal não pode ser rebaixado
    if target_user_email == ADMIN_EMAIL and new_perfil_acesso != PERFIL_ADMIN:
        flash("Erro: O perfil de acesso do administrador principal não pode ser rebaixado.", "error")
        return redirect(url_for('management.manage_users'))
        
    # Prevenção: Usuários não-Admin não podem rebaixar um Admin
    target_user_perfil = query_db(
        "SELECT perfil_acesso FROM perfil_usuario WHERE usuario = %s", 
        (target_user_email,), 
        one=True
    )
    if target_user_perfil and target_user_perfil.get('perfil_acesso') == PERFIL_ADMIN and new_perfil_acesso != PERFIL_ADMIN:
        if g.perfil.get('perfil_acesso') != PERFIL_ADMIN:
             flash("Acesso negado. Apenas um Administrador pode rebaixar outro Administrador (operação negada pelo código, apenas redefinição para 'Administrador' é permitida).", "error")
             return redirect(url_for('management.manage_users'))

    try:
        execute_db(
            "UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s",
            (final_perfil, target_user_email)
        )
        flash(f"Perfil de acesso de {target_user_email} atualizado para {final_perfil or 'Nenhum'}.", "success")
    except Exception as e:
        print(f"ERRO ao atualizar perfil para {target_user_email}: {e}")
        flash("Erro interno ao salvar o perfil.", "error")

    # Após o POST do formulário, faz o redirect de volta para a rota GET
    return redirect(url_for('management.manage_users'))