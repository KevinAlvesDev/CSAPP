from flask import Blueprint, jsonify, request

from ..blueprints.auth import login_required
from ..config.logging_config import api_logger
from ..domain import config_service
from ..security.api_security import validate_api_origin

config_api = Blueprint("config_api", __name__, url_prefix="/api/config")


@config_api.before_request
def _config_api_guard():
    return validate_api_origin(lambda: None)()


@config_api.route("/tags", methods=["GET"])
@login_required
def get_tags():
    try:
        tipo = request.args.get("tipo", "ambos")
        tags = config_service.listar_tags(tipo=tipo)
        return jsonify({"ok": True, "tags": tags})
    except Exception as e:
        api_logger.error(f"Erro ao buscar tags: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao buscar tags"}), 500


@config_api.route("/status", methods=["GET"])
@login_required
def get_status():
    try:
        status_list = config_service.listar_status_implantacao()
        return jsonify({"ok": True, "status": status_list})
    except Exception as e:
        api_logger.error(f"Erro ao buscar status: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao buscar status"}), 500


@config_api.route("/niveis", methods=["GET"])
@login_required
def get_niveis():
    try:
        niveis = config_service.listar_niveis_atendimento()
        return jsonify({"ok": True, "niveis": niveis})
    except Exception as e:
        api_logger.error(f"Erro ao buscar níveis: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao buscar níveis"}), 500


@config_api.route("/eventos", methods=["GET"])
@login_required
def get_eventos():
    try:
        eventos = config_service.listar_tipos_evento()
        return jsonify({"ok": True, "eventos": eventos})
    except Exception as e:
        api_logger.error(f"Erro ao buscar tipos de evento: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao buscar eventos"}), 500


@config_api.route("/motivos-parada", methods=["GET"])
@login_required
def get_motivos_parada():
    try:
        motivos = config_service.listar_motivos_parada()
        return jsonify({"ok": True, "motivos": motivos})
    except Exception as e:
        api_logger.error(f"Erro ao buscar motivos de parada: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao buscar motivos de parada"}), 500


@config_api.route("/motivos-cancelamento", methods=["GET"])
@login_required
def get_motivos_cancelamento():
    try:
        motivos = config_service.listar_motivos_cancelamento()
        return jsonify({"ok": True, "motivos": motivos})
    except Exception as e:
        api_logger.error(f"Erro ao buscar motivos de cancelamento: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Erro ao buscar motivos de cancelamento"}), 500
