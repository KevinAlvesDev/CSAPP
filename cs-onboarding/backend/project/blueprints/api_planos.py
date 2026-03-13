from flask import Blueprint, jsonify, request
import logging
logger = logging.getLogger(__name__)

from ..common.context_navigation import detect_current_context, normalize_context
from ..modules.planos.application import planos_sucesso_service

api_planos_bp = Blueprint("api_planos", __name__, url_prefix="/api")


@api_planos_bp.route("/planos-sucesso", methods=["GET"])
def api_listar_planos():
    """Endpoint API para listar planos de sucesso filtrando por status e usuario_id."""
    try:
        context = normalize_context(request.args.get("context")) or detect_current_context()
        status = request.args.get("status")
        usuario_id = request.args.get("usuario_id")
        ativo_arg = request.args.get("ativo")
        ativo: bool | None = True
        if ativo_arg is not None and str(ativo_arg).strip() != "":
            v = str(ativo_arg).strip().lower()
            if v in ("true", "1", "on", "yes", "sim"):
                ativo = True
            elif v in ("false", "0", "off", "no", "nao", "não"):
                ativo = False
            else:
                ativo = None
        processo_id_val = request.args.get("processo_id")
        processo_id_int: int | None = None
        if processo_id_val:
            try:
                processo_id_int = int(processo_id_val)
            except Exception as exc:
                logger.exception("Unhandled exception", exc_info=True)
                processo_id_int = None

        somente_templates = request.args.get("somente_templates", "true").lower() == "true"
        
        planos = planos_sucesso_service.listar_planos_sucesso(
            ativo=ativo,
            context=context,
            status=status if status else None,
            usuario_id=usuario_id if usuario_id else None,
            processo_id=processo_id_int,
            somente_templates=somente_templates,
        )

        contagens = planos_sucesso_service.contar_planos_por_status(
            usuario_id=usuario_id if usuario_id else None,
            context=context,
            somente_templates=somente_templates,
        )

        return jsonify({"success": True, "planos": planos, "contagens": contagens}), 200

    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
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
        logger.exception("Unhandled exception", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500