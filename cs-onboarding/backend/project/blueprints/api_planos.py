from flask import Blueprint, jsonify, request

from ..domain import planos_sucesso_service

api_planos_bp = Blueprint("api_planos", __name__, url_prefix="/api")


@api_planos_bp.route("/planos-sucesso", methods=["GET"])
def api_listar_planos():
    """Endpoint API para listar planos de sucesso filtrando por status e usuario_id."""
    try:
        status = request.args.get("status")
        usuario_id = request.args.get("usuario_id")
        processo_id = request.args.get("processo_id")

        if processo_id:
            try:
                processo_id = int(processo_id)
            except Exception:
                processo_id = None

        planos = planos_sucesso_service.listar_planos_sucesso(
            status=status if status else None, usuario_id=usuario_id if usuario_id else None, processo_id=processo_id
        )

        contagens = planos_sucesso_service.contar_planos_por_status(usuario_id=usuario_id if usuario_id else None)

        return jsonify({"success": True, "planos": planos, "contagens": contagens}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_planos_bp.route("/planos-sucesso/<int:plano_id>/concluir", methods=["PUT"])
def api_concluir_plano(plano_id):
    """Endpoint API para marcar um plano como concluído."""
    try:
        # Buscar processo_id antes de concluir para decidir se oferecer um novo plano
        plano = planos_sucesso_service.obter_plano_completo(plano_id)
        processo_id = plano.get("processo_id") if plano else None

        planos_sucesso_service.concluir_plano_sucesso(plano_id)

        offer_new_plan = bool(processo_id)

        return jsonify({
            "success": True,
            "message": "Plano concluído com sucesso",
            "offer_new_plan": offer_new_plan,
            "processo_id": processo_id,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
