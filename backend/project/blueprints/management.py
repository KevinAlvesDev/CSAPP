# testo/CSAPP/backend/project/blueprints/management.py
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, g, jsonify, current_app
)
from ..blueprints.auth import admin_required
from ..db import query_db, execute_db
from ..logging_config import management_logger, security_logger
from ..constants import ADMIN_EMAIL, PERFIL_ADMIN
from ..extensions import r2_client

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
        # Compatível com testes: lê usuários direto via query_db
        users_data = query_db(
            "SELECT usuario as usuario, nome, perfil_acesso FROM perfil_usuario ORDER BY nome"
        ) or []

        perfis_disponiveis = current_app.config.get(
            'PERFIS_DE_ACESSO', ['Visitante', 'Implantador', 'Gestor', 'Administrador']
        )

        return render_template(
            'manage_users.html',
            users=users_data,
            perfis_list=perfis_disponiveis
        )
    except Exception as e:
        # Compatível com testes: retorna tupla (mensagem, 500) e loga via management_logger
        management_logger.error(f"Erro ao carregar a lista de usuários: {e}")
        return ("Erro ao carregar a lista de usuários", 500)

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
        management_logger.info(f"Admin {g.user_email} atualizou o perfil de {usuario_alvo} para {novo_perfil}")
        return jsonify({'ok': True})

    except Exception as e:
        management_logger.error(f"Erro ao atualizar perfil de {usuario_alvo} por {g.user_email}: {e}")
        return jsonify({'ok': False, 'error': f'Erro de banco de dados: {e}'}), 500

@management_bp.route('/users/update_perfil', methods=['POST'])
def update_user_perfil():
    """Atualiza o perfil via formulário HTML (compatível com manage_users.html)."""
    # Valida campos do formulário
    usuario_alvo = request.form.get('usuario_email')
    novo_perfil = request.form.get('new_perfil')

    if usuario_alvo is None:
        flash('Usuário não especificado.', 'error')
        return redirect(url_for('management.manage_users'))

    # Tratar opção "Nenhum" como None
    if novo_perfil == "":
        novo_perfil = None

    # Regra de segurança: não pode alterar o próprio perfil por esta rota
    if usuario_alvo == g.user_email:
        security_logger.warning(f"Admin {g.user_email} tentou alterar o próprio perfil via 'update_user_perfil'")
        flash('Você não pode alterar o seu próprio perfil por esta interface.', 'warning')
        return redirect(url_for('management.manage_users'))

    # Regra específica: não permitir rebaixar o administrador principal
    if usuario_alvo == ADMIN_EMAIL and (novo_perfil is None or novo_perfil != PERFIL_ADMIN):
        security_logger.warning("Tentativa de rebaixar administrador detectada por " + str(g.user_email))
        # Compat: redireciona com flash
        flash('Não é permitido alterar o perfil do administrador principal.', 'warning')
        return redirect(url_for('management.manage_users'))

    # Valida o perfil (se não for None, deve estar na lista de constantes)
    perfis_disponiveis = current_app.config.get('PERFIS_DE_ACESSO', [])
    if novo_perfil is not None and novo_perfil not in perfis_disponiveis:
        security_logger.warning(
            f"Tentativa de atribuir perfil inválido '{novo_perfil}' para {usuario_alvo} por {g.user_email}"
        )
        flash('Perfil de acesso inválido.', 'error')
        return redirect(url_for('management.manage_users'))

    try:
        # Verifica se o usuário existe
        user_exists = query_db("SELECT 1 FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,), one=True)
        if not user_exists:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('management.manage_users'))

        # Regra: impedir usuário não-admin de alterar admin
        from ..blueprints.auth import security_logger as auth_security_logger  # compat com patch nos testes
        try:
            target_is_admin = query_db(
                "SELECT perfil_acesso FROM perfil_usuario WHERE usuario = %s",
                (usuario_alvo,), one=True
            )
            target_is_admin = target_is_admin and target_is_admin.get('perfil_acesso') == PERFIL_ADMIN
        except Exception:
            target_is_admin = False

        if target_is_admin and (g.perfil or {}).get('perfil_acesso') != PERFIL_ADMIN:
            auth_security_logger.warning("Tentativa de rebaixar administrador detectada por " + str(g.user_email))
            flash('Apenas Administradores podem alterar perfis de Administradores.', 'warning')
            return redirect(url_for('management.manage_users'))

        execute_db(
            "UPDATE perfil_usuario SET perfil_acesso = %s WHERE usuario = %s",
            (novo_perfil, usuario_alvo)
        )
        management_logger.info(f"Admin {g.user_email} atualizou o perfil de {usuario_alvo} para {novo_perfil}")
        flash('Perfil atualizado com sucesso.', 'success')
        return redirect(url_for('management.manage_users'))

    except Exception as e:
        management_logger.error(f"Erro ao atualizar perfil de {usuario_alvo} por {g.user_email}: {e}")
        flash(f'Erro de banco de dados: {e}', 'error')
        return redirect(url_for('management.manage_users'))

@management_bp.route('/users/delete', methods=['POST'])
def delete_user():
    """Exclui um usuário via formulário, com redirecionamento e logs (compatível com testes)."""
    usuario_alvo = request.form.get('usuario_email')
    if not usuario_alvo:
        flash('Usuário não especificado.', 'error')
        return redirect(url_for('management.manage_users'))

    # Regra de segurança: não pode excluir a si mesmo
    if usuario_alvo == g.user_email:
        security_logger.warning(f"Tentativa de exclusão do próprio usuário por {g.user_email}")
        flash('Você não pode excluir a si mesmo.', 'warning')
        return redirect(url_for('management.manage_users'))

    # Regra: não pode excluir o administrador principal
    if usuario_alvo == ADMIN_EMAIL:
        security_logger.warning("Tentativa de exclusão do administrador principal detectada por " + str(g.user_email))
        flash('Não é permitido excluir o administrador principal.', 'warning')
        return redirect(url_for('management.manage_users'))

    try:
        # Se houver foto no R2, remove
        perfil = query_db("SELECT foto_url FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,), one=True)
        public_base = current_app.config.get('CLOUDFLARE_PUBLIC_URL')
        bucket = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
        if perfil and perfil.get('foto_url') and public_base and bucket and r2_client:
            foto_url = perfil['foto_url']
            if foto_url.startswith(public_base):
                key = foto_url[len(public_base):].lstrip('/')
                try:
                    r2_client.delete_object(Bucket=bucket, Key=key)
                except Exception:
                    # Falha ao excluir arquivo não deve impedir exclusão do usuário
                    pass

        # Exclui registros simples (detalhes de cascata dependem do schema real)
        execute_db("DELETE FROM perfil_usuario WHERE usuario = %s", (usuario_alvo,))
        execute_db("DELETE FROM usuarios WHERE usuario = %s", (usuario_alvo,))

        management_logger.info(f"Usuário {usuario_alvo} excluído por {g.user_email}")
        flash('Usuário excluído com sucesso.', 'success')
        return redirect(url_for('management.manage_users'))

    except Exception as e:
        management_logger.error(f"Erro ao excluir usuário {usuario_alvo} por {g.user_email}: {e}")
        flash(f'Erro de banco de dados: {e}', 'error')
        return redirect(url_for('management.manage_users'))