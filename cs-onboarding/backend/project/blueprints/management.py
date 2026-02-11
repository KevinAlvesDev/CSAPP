import contextlib

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, url_for

from ..blueprints.auth import permission_required
from ..config.logging_config import management_logger
from ..constants import PERFIL_ADMIN, PERFIS_GERENCIAR_USUARIOS
from ..core.extensions import r2_client
from ..domain.management_service import (
    atualizar_perfil_usuario_service,
    excluir_usuario_service,
    limpar_implantacoes_orfas_service,
    listar_usuarios_service,
    obter_perfis_disponiveis,
    perform_backup,
)

management_bp = Blueprint("management", __name__, url_prefix="/management")


@management_bp.before_request
@permission_required(PERFIS_GERENCIAR_USUARIOS)
def before_request():
    """Protege todas as rotas de gerenciamento. Acesso: Admin, Gerente, Coordenador."""
    pass


@management_bp.route("/users")
def manage_users():
    """Renderiza a página principal de gerenciamento de usuários."""
    try:
        users_data = listar_usuarios_service()
        perfis_disponiveis = obter_perfis_disponiveis()

        return render_template("pages/manage_users.html", users=users_data, perfis_list=perfis_disponiveis)
    except Exception as e:
        management_logger.error(f"Erro ao carregar a lista de usuários: {e}")
        return ("Erro ao carregar a lista de usuários", 500)


@management_bp.route("/users/modal")
def manage_users_modal():
    """Renderiza somente o conteúdo do modal de gerenciamento de usuários (sem coluna 'Implantações')."""
    try:
        users_data = listar_usuarios_service()
        perfis_disponiveis = obter_perfis_disponiveis()

        return render_template("_manage_users_content.html", users=users_data, perfis_list=perfis_disponiveis)
    except Exception as e:
        management_logger.error(f"Erro ao carregar conteúdo do modal de usuários: {e}")
        return ("Erro ao carregar usuários", 500)


@management_bp.route("/backup/db", methods=["POST"])
def backup_database():
    """Gera um backup do banco de dados atual.
    - SQLite: copia o arquivo .db para backend/backups com timestamp
    - PostgreSQL: exporta tabelas principais para CSV dentro de um ZIP
    Retorna JSON com caminho relativo do backup.
    """
    try:
        result = perform_backup()
        return jsonify({"ok": True, **result})
    except Exception as e:
        management_logger.error(f"Erro ao gerar backup do banco: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@management_bp.route("/users/update_profile", methods=["POST"])
def update_user_profile():
    """Atualiza o perfil de acesso de um usuário."""
    data = request.get_json()
    if not data or "usuario" not in data or "perfil" not in data:
        return jsonify({"ok": False, "error": "Dados incompletos"}), 400

    usuario_alvo = data["usuario"]
    novo_perfil = data["perfil"]

    try:
        atualizar_perfil_usuario_service(usuario_alvo, novo_perfil, g.user_email)
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400 if "não encontrado" in str(e) else 403
    except Exception as e:
        management_logger.error(f"Erro ao atualizar perfil de {usuario_alvo} por {g.user_email}: {e}")
        return jsonify({"ok": False, "error": f"Erro de banco de dados: {e}"}), 500


@management_bp.route("/users/update_perfil", methods=["POST"])
def update_user_perfil():
    """Atualiza o perfil via formulário HTML (compatível com manage_users.html)."""

    usuario_alvo = request.form.get("usuario_email")
    novo_perfil = request.form.get("new_perfil")

    def render_users_list():
        """Helper para renderizar lista de usuários."""
        users_data = listar_usuarios_service()
        perfis_disponiveis = obter_perfis_disponiveis()
        return render_template("_manage_users_content.html", users=users_data, perfis_list=perfis_disponiveis)

    if usuario_alvo is None:
        flash("Usuário não especificado.", "error")
        if request.headers.get("HX-Request") == "true":
            return render_users_list()
        return redirect(url_for("management.manage_users"))

    if novo_perfil == "":
        novo_perfil = None

    try:
        atualizar_perfil_usuario_service(usuario_alvo, novo_perfil, g.user_email)
        flash("Perfil atualizado com sucesso.", "success")
        if request.headers.get("HX-Request") == "true":
            return render_users_list()
        return redirect(url_for("management.manage_users"))

    except ValueError as e:
        flash(str(e), "warning" if "próprio perfil" in str(e) or "administrador" in str(e) else "error")
        if request.headers.get("HX-Request") == "true":
            return render_users_list()
        return redirect(url_for("management.manage_users"))
    except Exception as e:
        management_logger.error(f"Erro ao atualizar perfil de {usuario_alvo} por {g.user_email}: {e}")
        flash(f"Erro de banco de dados: {e}", "error")
        if request.headers.get("HX-Request") == "true":
            return render_users_list()
        return redirect(url_for("management.manage_users"))


@management_bp.route("/users/delete", methods=["POST"])
def delete_user():
    """Exclui um usuário via formulário, com redirecionamento e logs (compatível com testes)."""
    usuario_alvo = request.form.get("usuario_email")

    def render_users_list():
        """Helper para renderizar lista de usuários."""
        users_data = listar_usuarios_service()
        perfis_disponiveis = obter_perfis_disponiveis()
        return render_template("_manage_users_content.html", users=users_data, perfis_list=perfis_disponiveis)

    if not usuario_alvo:
        flash("Usuário não especificado.", "error")
        if request.headers.get("HX-Request") == "true":
            return render_users_list()
        return redirect(url_for("management.manage_users"))

    try:
        result = excluir_usuario_service(usuario_alvo, g.user_email)

        # Deletar foto do R2 se houver
        foto_url = result.get("foto_url")
        if foto_url:
            public_base = current_app.config.get("CLOUDFLARE_PUBLIC_URL")
            bucket = current_app.config.get("CLOUDFLARE_BUCKET_NAME")
            if public_base and bucket and r2_client and foto_url.startswith(public_base):
                key = foto_url[len(public_base) :].lstrip("/")
                with contextlib.suppress(Exception):
                    r2_client.delete_object(Bucket=bucket, Key=key)

        flash(f"Usuário e {result['implantacoes_excluidas']} implantações vinculadas excluídos.", "success")
        if request.headers.get("HX-Request") == "true":
            return render_users_list()
        return redirect(url_for("management.manage_users"))

    except ValueError as e:
        flash(str(e), "warning")
        if request.headers.get("HX-Request") == "true":
            return render_users_list()
        return redirect(url_for("management.manage_users"))
    except Exception as e:
        management_logger.error(f"Erro ao excluir usuário {usuario_alvo} por {g.user_email}: {e}")
        flash(f"Erro de banco de dados: {e}", "error")
        if request.headers.get("HX-Request") == "true":
            return render_users_list()
        return redirect(url_for("management.manage_users"))


@management_bp.route("/cleanup/orphan-implantacoes", methods=["POST"])
def cleanup_orphan_implantacoes():
    """Remove implantações órfãs (sem usuário proprietário). Admin-only."""
    try:
        count = limpar_implantacoes_orfas_service(g.user_email)
        flash(f"{count} implantações órfãs removidas.", "success")
        return redirect(url_for("management.manage_users"))
    except Exception as e:
        management_logger.error(f"Erro ao remover implantações órfãs por {g.user_email}: {e}")
        flash(f"Erro ao remover implantações órfãs: {e}", "error")
        return redirect(url_for("management.manage_users"))


@management_bp.route("/cache/clear", methods=["POST"])
@permission_required([PERFIL_ADMIN])
def clear_cache():
    """
    Limpa o cache do sistema (Redis/Flask-Caching).
    Útil para forçar atualização de dados cacheados.
    Admin-only.
    """
    try:
        from ..config.cache_config import cache

        if cache:
            cache.clear()
            management_logger.info(f"Cache limpo por {g.user_email}")
            return jsonify({"ok": True, "message": "Cache limpo com sucesso"})
        else:
            return jsonify({"ok": False, "message": "Cache não configurado"}), 503
    except Exception as e:
        management_logger.error(f"Erro ao limpar cache: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
