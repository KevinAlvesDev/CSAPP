"""
Blueprint de Perfis de Acesso
Rotas para gerenciar perfis e permissões (RBAC)
"""

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

from ..__init__ import csrf
from ..blueprints.auth import login_required
from ..common.exceptions import ValidationError
from ..config.logging_config import get_logger
from ..domain import perfis_service

perfis_bp = Blueprint("perfis", __name__, url_prefix="/perfis")
logger = get_logger("perfis")


def _get_dashboard_redirect():
    """Detecta o contexto atual e retorna o redirect apropriado para o dashboard."""
    # Primeiro tenta pegar do g.modulo_atual (se disponível)
    if hasattr(g, "modulo_atual"):
        if g.modulo_atual == "grandes_contas":
            return redirect(url_for("grandes_contas.dashboard"))
        elif g.modulo_atual == "ongoing":
            return redirect(url_for("ongoing.dashboard"))

    # Fallback: verifica o referer
    referer = request.headers.get("Referer", "")
    if "/grandes-contas/" in referer:
        return redirect(url_for("grandes_contas.dashboard"))
    elif "/ongoing/" in referer:
        return redirect(url_for("ongoing.dashboard"))

    # Default: onboarding
    return redirect(url_for("onboarding.dashboard"))


@perfis_bp.before_request
def set_module_context():
    """Define o contexto do módulo atual baseado no referer."""
    referer = request.headers.get("Referer", "")

    if "/grandes-contas/" in referer:
        g.modulo_atual = "grandes_contas"
    elif "/ongoing/" in referer:
        g.modulo_atual = "ongoing"
    else:
        g.modulo_atual = "onboarding"


@perfis_bp.route("/", methods=["GET"])
@login_required
def listar_perfis():
    """Lista todos os perfis de acesso"""
    try:
        perfis = perfis_service.listar_perfis()
        return render_template("pages/perfis_lista.html", perfis=perfis)
    except Exception as e:
        logger.error(f"Erro ao listar perfis: {e}", exc_info=True)
        flash(f"Erro ao carregar perfis: {e!s}", "error")
        return _get_dashboard_redirect()


@perfis_bp.route("/novo", methods=["GET"])
@login_required
def novo_perfil():
    """Formulário para criar novo perfil"""
    try:
        categorias = perfis_service.obter_categorias()
        recursos = perfis_service.listar_recursos()

        # Agrupar recursos por categoria
        recursos_agrupados = {}
        for recurso in recursos:
            cat = recurso["categoria"]
            if cat not in recursos_agrupados:
                recursos_agrupados[cat] = []
            recursos_agrupados[cat].append(recurso)

        return render_template(
            "pages/perfis_editor.html",
            perfil=None,
            categorias=categorias,
            recursos_agrupados=recursos_agrupados,
            modo="criar",
        )
    except Exception as e:
        logger.error(f"Erro ao abrir formulário de novo perfil: {e}", exc_info=True)
        flash(f"Erro: {e!s}", "error")
        return redirect(url_for("perfis.listar_perfis"))


@perfis_bp.route("/<int:perfil_id>/editar", methods=["GET"])
@login_required
def editar_perfil(perfil_id):
    """Editor de permissões do perfil"""
    try:
        perfil = perfis_service.obter_perfil_completo(perfil_id)
        if not perfil:
            flash("Perfil não encontrado", "error")
            return redirect(url_for("perfis.listar_perfis"))

        categorias = perfis_service.obter_categorias()

        return render_template("pages/perfis_editor.html", perfil=perfil, categorias=categorias, modo="editar")
    except Exception as e:
        logger.error(f"Erro ao editar perfil {perfil_id}: {e}", exc_info=True)
        flash(f"Erro: {e!s}", "error")
        return redirect(url_for("perfis.listar_perfis"))


@perfis_bp.route("/", methods=["POST"])
@login_required
@csrf.exempt
def criar_perfil():
    """Cria novo perfil"""
    try:
        data = request.get_json() if request.is_json else request.form

        nome = data.get("nome", "").strip()
        descricao = data.get("descricao", "").strip()
        cor = data.get("cor", "#667eea")
        icone = data.get("icone", "bi-person-badge")
        permissoes = data.getlist("permissoes") if hasattr(data, "getlist") else data.get("permissoes", [])

        if not nome:
            raise ValidationError("Nome do perfil é obrigatório")

        # Criar perfil
        perfil_id = perfis_service.criar_perfil(nome, descricao, cor, icone)

        # Atualizar permissões se fornecidas
        if permissoes:
            permissoes_ids = [int(p) for p in permissoes if p]
            perfis_service.atualizar_permissoes(perfil_id, permissoes_ids)

        if request.is_json:
            return jsonify({"ok": True, "message": "Perfil criado com sucesso!", "perfil_id": perfil_id}), 201

        flash("Perfil criado com sucesso!", "success")
        return redirect(url_for("perfis.editar_perfil", perfil_id=perfil_id))

    except ValidationError as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 400
        flash(str(e), "error")
        return redirect(url_for("perfis.novo_perfil"))
    except Exception as e:
        logger.error(f"Erro ao criar perfil: {e}", exc_info=True)
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        flash(f"Erro ao criar perfil: {e!s}", "error")
        return redirect(url_for("perfis.novo_perfil"))


@perfis_bp.route("/<int:perfil_id>", methods=["PUT", "POST"])
@login_required
@csrf.exempt
def atualizar_perfil(perfil_id):
    """Atualiza dados do perfil"""
    try:
        data = request.get_json() if request.is_json else request.form

        perfis_service.atualizar_perfil(perfil_id, dict(data))

        if request.is_json:
            return jsonify({"ok": True, "message": "Perfil atualizado com sucesso!"}), 200

        flash("Perfil atualizado com sucesso!", "success")
        return redirect(url_for("perfis.editar_perfil", perfil_id=perfil_id))

    except ValidationError as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 400
        flash(str(e), "error")
        return redirect(url_for("perfis.editar_perfil", perfil_id=perfil_id))
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil {perfil_id}: {e}", exc_info=True)
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        flash(f"Erro: {e!s}", "error")
        return redirect(url_for("perfis.editar_perfil", perfil_id=perfil_id))


@perfis_bp.route("/<int:perfil_id>/permissoes", methods=["POST"])
@login_required
@csrf.exempt
def atualizar_permissoes(perfil_id):
    """Atualiza permissões do perfil"""
    try:
        data = request.get_json() if request.is_json else request.form

        permissoes = data.getlist("permissoes") if hasattr(data, "getlist") else data.get("permissoes", [])
        permissoes_ids = [int(p) for p in permissoes if p]

        perfis_service.atualizar_permissoes(perfil_id, permissoes_ids)

        if request.is_json:
            return jsonify({"ok": True, "message": "Permissões atualizadas com sucesso!"}), 200

        flash("Permissões atualizadas com sucesso!", "success")
        return redirect(url_for("perfis.editar_perfil", perfil_id=perfil_id))

    except ValidationError as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 400
        flash(str(e), "error")
        return redirect(url_for("perfis.editar_perfil", perfil_id=perfil_id))
    except Exception as e:
        logger.error(f"Erro ao atualizar permissões do perfil {perfil_id}: {e}", exc_info=True)
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        flash(f"Erro: {e!s}", "error")
        return redirect(url_for("perfis.editar_perfil", perfil_id=perfil_id))


@perfis_bp.route("/<int:perfil_id>", methods=["DELETE"])
@login_required
def excluir_perfil(perfil_id):
    """Exclui um perfil"""
    try:
        perfis_service.excluir_perfil(perfil_id)

        if request.is_json:
            return jsonify({"ok": True, "message": "Perfil excluído com sucesso!"}), 200

        flash("Perfil excluído com sucesso!", "success")
        return redirect(url_for("perfis.listar_perfis"))

    except ValidationError as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 400
        flash(str(e), "error")
        return redirect(url_for("perfis.listar_perfis"))
    except Exception as e:
        logger.error(f"Erro ao excluir perfil {perfil_id}: {e}", exc_info=True)
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        flash(f"Erro: {e!s}", "error")
        return redirect(url_for("perfis.listar_perfis"))


@perfis_bp.route("/<int:perfil_id>/clonar", methods=["POST"])
@login_required
@csrf.exempt
def clonar_perfil(perfil_id):
    """Clona um perfil existente"""
    try:
        data = request.get_json() if request.is_json else request.form

        novo_nome = data.get("nome", "").strip()
        if not novo_nome:
            raise ValidationError("Nome do novo perfil é obrigatório")

        novo_perfil_id = perfis_service.clonar_perfil(perfil_id, novo_nome)

        if request.is_json:
            return jsonify({"ok": True, "message": "Perfil clonado com sucesso!", "perfil_id": novo_perfil_id}), 201

        flash("Perfil clonado com sucesso!", "success")
        return redirect(url_for("perfis.editar_perfil", perfil_id=novo_perfil_id))

    except ValidationError as e:
        if request.is_json:
            return jsonify({"error": str(e)}), 400
        flash(str(e), "error")
        return redirect(url_for("perfis.listar_perfis"))
    except Exception as e:
        logger.error(f"Erro ao clonar perfil {perfil_id}: {e}", exc_info=True)
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        flash(f"Erro: {e!s}", "error")
        return redirect(url_for("perfis.listar_perfis"))


@perfis_bp.route("/api/recursos", methods=["GET"])
@login_required
def api_recursos():
    """API: Lista recursos agrupados por categoria"""
    try:
        categoria = request.args.get("categoria")
        recursos = perfis_service.listar_recursos(categoria)

        # Agrupar por categoria
        agrupados = {}
        for recurso in recursos:
            cat = recurso["categoria"]
            if cat not in agrupados:
                agrupados[cat] = []
            agrupados[cat].append(recurso)

        return jsonify({"ok": True, "recursos": agrupados}), 200
    except Exception as e:
        logger.error(f"Erro ao listar recursos: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
