from flask import Blueprint, render_template, request, flash, redirect, url_for, g, jsonify, current_app
# Importe o r2_client e ClientError do extensions, se estiver usando um módulo dedicado
# Assumindo que você usa from ..extensions import r2_client (como em main.py/api.py)
from ..extensions import r2_client
from botocore.exceptions import ClientError
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
            ADMIN_EMAIL=ADMIN_EMAIL
        )
    except Exception as e:
        print(f"ERRO ao carregar manage_users: {e}")
        return f"<div class=\"alert alert-danger\">Erro ao carregar a lista: {e}</div>", 500

@management_bp.route('/users/update_perfil', methods=['POST'])
@permission_required(PERFIS_COM_GESTAO)
def update_user_perfil():
    """Atualiza o perfil de acesso de um usuário."""
    target_user_email = request.form.get('usuario_email')
    new_perfil = request.form.get('new_perfil', '').strip()

    if not target_user_email:
        flash("Erro: E-mail do usuário não fornecido.", "error")
        return redirect(url_for('main.dashboard', open_users_modal='true')) 

    final_perfil = new_perfil if new_perfil else None

    if target_user_email == ADMIN_EMAIL and final_perfil != PERFIL_ADMIN and final_perfil is not None:
        flash("Erro: O perfil de acesso do administrador principal não pode ser rebaixado.", "error")
        return redirect(url_for('main.dashboard', open_users_modal='true')) 
        
    target_user_perfil = query_db(
        "SELECT perfil_acesso FROM perfil_usuario WHERE usuario = %s", 
        (target_user_email,), 
        one=True
    )
    if target_user_perfil and target_user_perfil.get('perfil_acesso') == PERFIL_ADMIN and final_perfil != PERFIL_ADMIN:
        if g.perfil.get('perfil_acesso') != PERFIL_ADMIN:
             flash("Acesso negado. Apenas um Administrador pode tentar alterar o perfil de outro Administrador.", "error")
             return redirect(url_for('main.dashboard', open_users_modal='true'))
        flash("Operação negada: Administradores não podem rebaixar outros Administradores.", "error")
        return redirect(url_for('main.dashboard', open_users_modal='true'))

    try:
        execute_db(
            "UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s",
            (final_perfil, target_user_email)
        )
        flash(f"Perfil de acesso de {target_user_email} atualizado para {final_perfil or 'Nenhum'}. A lista abaixo foi atualizada.", "success")
    except Exception as e:
        print(f"ERRO ao atualizar perfil para {target_user_email}: {e}")
        flash(f"Erro ao atualizar perfil de acesso.", "error")
        
    return redirect(url_for('main.dashboard', open_users_modal='true')) 


@management_bp.route('/users/delete_user', methods=['POST'])
@permission_required([PERFIL_ADMIN])
def delete_user():
    """Exclui um usuário do sistema (usuários e perfil_usuario). Apenas ADMIN."""
    target_user_email = request.form.get('usuario_email')
    
    if not target_user_email:
        flash("Erro: E-mail do usuário não fornecido.", "error")
        return redirect(url_for('main.dashboard', open_users_modal='true'))

    if target_user_email == g.user_email:
        flash("Erro: Você não pode excluir sua própria conta.", "error")
        return redirect(url_for('main.dashboard', open_users_modal='true'))
    
    if target_user_email == ADMIN_EMAIL:
        flash("Erro: O administrador principal do sistema não pode ser excluído.", "error")
        return redirect(url_for('main.dashboard', open_users_modal='true'))

    try:
        # Pega a foto_url antes de deletar o perfil
        perfil = query_db("SELECT foto_url FROM perfil_usuario WHERE usuario = %s", (target_user_email,), one=True)
        foto_url = perfil.get('foto_url') if perfil else None
        
        # Ação CRÍTICA: Anula referências para evitar falha por Foreign Key
        execute_db(
            "UPDATE implantacoes SET usuario_cs = NULL WHERE usuario_cs = %s",
            (target_user_email,)
        )
        execute_db(
            "UPDATE timeline_log SET usuario_cs = NULL WHERE usuario_cs = %s",
            (target_user_email,)
        )
        execute_db(
            "UPDATE comentarios SET usuario_cs = NULL WHERE usuario_cs = %s",
            (target_user_email,)
        )

        # 1. Deleta o perfil e o usuário
        # O DELETE em 'usuarios' deve estar em CASCADE para 'perfil_usuario'
        execute_db(
            "DELETE FROM perfil_usuario WHERE usuario = %s",
            (target_user_email,)
        )
        execute_db(
            "DELETE FROM usuarios WHERE usuario = %s",
            (target_user_email,)
        )
        
        # 2. Limpeza do R2
        if foto_url and r2_client and current_app.config['CLOUDFLARE_PUBLIC_URL']:
            try:
                # Extrai o nome do arquivo da URL pública
                key_to_delete = foto_url.split(current_app.config['CLOUDFLARE_PUBLIC_URL'] + '/')[1]
                r2_client.delete_object(
                    Bucket=current_app.config['CLOUDFLARE_BUCKET_NAME'],
                    Key=key_to_delete
                )
                print(f"Foto de perfil {key_to_delete} deletada do R2 para {target_user_email}.")
            except ClientError as e_r2:
                # Loga o erro, mas não interrompe a exclusão do usuário
                print(f"AVISO R2: Falha ao deletar foto antiga do R2. {e_r2}")
            except Exception as e_r2:
                print(f"AVISO: Falha ao deletar foto do R2 para {target_user_email}: {e_r2}")

        flash(f"Usuário {target_user_email} excluído com sucesso. Todos os seus registros foram removidos.", "success")
        
    except Exception as e:
        print(f"ERRO ao excluir usuário {target_user_email}: {e}")
        flash(f"Erro CRÍTICO ao excluir usuário: {e}.", "error")
        
    return redirect(url_for('main.dashboard', open_users_modal='true'))