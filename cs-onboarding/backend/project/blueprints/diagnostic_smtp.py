import logging
logger = logging.getLogger(__name__)
"""
Endpoint de diagnóstico para testar SMTP no Railway
Adicione isso temporariamente em algum blueprint para testar
"""

import smtplib
import socket
import ssl

from flask import Blueprint, current_app, g, jsonify

from .auth import login_required

diagnostic_bp = Blueprint("diagnostic", __name__)


@diagnostic_bp.route("/api/diagnostic/smtp-test", methods=["GET"])
@login_required
def test_smtp_connection():
    """
    Endpoint para testar conexão SMTP (use apenas em desenvolvimento/debug)
    Acesse: https://seu-app.railway.app/api/diagnostic/smtp-test
    """
    from typing import Any, Dict

    # Defesa em profundidade: rota acessível apenas em debug ou quando habilitada por env.
    if not (current_app.config.get("DEBUG", False) or current_app.config.get("ENABLE_DIAGNOSTIC_SMTP", False)):
        return jsonify({"ok": False, "error": "Endpoint desabilitado neste ambiente"}), 404

    # Permitir apenas administradores.
    perfil = g.perfil.get("perfil_acesso") if getattr(g, "perfil", None) else None
    if perfil != "Administrador":
        return jsonify({"ok": False, "error": "Acesso negado"}), 403

    results: Dict[str, Any] = {"config": {}, "tests": {}, "errors": []}

    # Pegar configurações
    cfg = current_app.config
    host = cfg.get("SMTP_HOST")
    port = int(cfg.get("SMTP_PORT", 587))
    user = cfg.get("SMTP_USER")
    password = cfg.get("SMTP_PASSWORD")
    use_ssl = cfg.get("SMTP_USE_SSL", False)
    use_tls = cfg.get("SMTP_USE_TLS", True)
 
    if not host:
        results["ok"] = False
        results["errors"].append("SMTP_HOST não configurado")
        return results

    results["config"] = {
        "host": host,
        "port": port,
        "user": user,
        "use_ssl": use_ssl,
        "use_tls": use_tls,
        "has_password": bool(password),
    }

    # Teste 1: Resolver DNS
    try:
        ip = socket.gethostbyname(host)
        results["tests"]["dns_resolution"] = {"status": "success", "ip": ip}
    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        results["tests"]["dns_resolution"] = {"status": "failed", "error": str(e)}
        results["errors"].append(f"DNS resolution failed: {e}")

    # Teste 2: Conectar ao servidor
    server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
    try:
        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=10)
            results["tests"]["connection"] = {"status": "success", "method": "SMTP_SSL", "port": port}
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            results["tests"]["connection"] = {"status": "success", "method": "SMTP", "port": port}

            # Teste 3: STARTTLS (se não for SSL)
            if use_tls:
                try:
                    server.starttls()
                    results["tests"]["starttls"] = {"status": "success"}
                except Exception as e:
                    logger.exception("Unhandled exception", exc_info=True)
                    results["tests"]["starttls"] = {"status": "failed", "error": str(e)}
                    results["errors"].append(f"STARTTLS failed: {e}")

        # Teste 4: Autenticação
        if user and password:
            try:
                server.login(user, password)
                results["tests"]["authentication"] = {"status": "success"}
            except Exception as e:
                logger.exception("Unhandled exception", exc_info=True)
                results["tests"]["authentication"] = {"status": "failed", "error": str(e)}
                results["errors"].append(f"Authentication failed: {e}")

        server.quit()
        results["overall_status"] = "success" if not results["errors"] else "partial"

    except smtplib.SMTPConnectError as e:
        results["tests"]["connection"] = {"status": "failed", "error": str(e), "type": "SMTPConnectError"}
        results["errors"].append(f"Connection failed: {e}")
        results["overall_status"] = "failed"

    except socket.gaierror as e:
        results["tests"]["connection"] = {"status": "failed", "error": str(e), "type": "DNS/Network Error"}
        results["errors"].append(f"Network error: {e}")
        results["overall_status"] = "failed"

    except TimeoutError as e:
        results["tests"]["connection"] = {"status": "failed", "error": str(e), "type": "Timeout"}
        results["errors"].append(f"Connection timeout: {e}")
        results["overall_status"] = "failed"

    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        results["tests"]["connection"] = {"status": "failed", "error": str(e), "type": type(e).__name__}
        results["errors"].append(f"Unexpected error: {e}")
        results["overall_status"] = "failed"

    return jsonify(results), 200 if results.get("overall_status") == "success" else 500