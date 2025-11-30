"""
Blueprint para health checks e monitoramento.
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime
from botocore.exceptions import ClientError

health_bp = Blueprint('health', __name__)


def check_database_connection():
    """
    Verifica se a conexão com o banco de dados está funcionando.
    Retorna (status: bool, message: str, response_time_ms: float)
    """
    start_time = datetime.now()
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)

    try:
        from ..db import query_db

        result = query_db("SELECT 1 as test", one=True)

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        if result and result.get('test') == 1:
            db_type = 'SQLite' if use_sqlite else 'PostgreSQL'
            return True, f"{db_type} connection OK", response_time
        else:
            return False, "Database query returned unexpected result", response_time

    except Exception as e:
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000
        return False, f"Database connection failed: {str(e)}", response_time


def check_r2_connection():
    """
    Verifica se a conexão com o Cloudflare R2 está configurada.
    Retorna (status: bool, message: str)
    """
    try:
        from ..core.extensions import r2_client

        if r2_client is None:
            return False, "R2 client not initialized"

        if current_app.config.get('R2_CONFIGURADO', False):
            try:
                bucket = current_app.config.get('CLOUDFLARE_BUCKET_NAME')
                if bucket:
                    r2_client.list_objects_v2(Bucket=bucket, MaxKeys=1)
                    return True, "R2 operational"
                return True, "R2 configured"
            except ClientError as e:
                code = getattr(e, 'response', {}).get('Error', {}).get('Code')
                return False, f"R2 operation failed: {code}"
            except Exception as e:
                return False, f"R2 operation failed: {str(e)}"
        else:
            return False, "R2 not configured"

    except Exception as e:
        return False, f"R2 check failed: {str(e)}"


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint de health check para monitoramento.
    Retorna status da aplicação, banco de dados e serviços externos.
    """

    db_status, db_message, db_response_time = check_database_connection()

    r2_status, r2_message = check_r2_connection()

    overall_status = "healthy" if db_status else "unhealthy"

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {
            "database": {
                "status": "up" if db_status else "down",
                "message": db_message,
                "response_time_ms": round(db_response_time, 2)
            },
            "r2_storage": {
                "status": "up" if r2_status else "down",
                "message": r2_message
            }
        },
        "environment": {
            "use_sqlite": current_app.config.get('USE_SQLITE_LOCALLY', False),
            "debug_mode": current_app.debug
        }
    }

    status_code = 200 if overall_status == "healthy" else 503

    return jsonify(response), status_code


@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """
    Endpoint de readiness check (para Kubernetes/Railway).
    Verifica se a aplicação está pronta para receber tráfego.
    """
    db_status, _, _ = check_database_connection()

    if db_status:
        return jsonify({"status": "ready"}), 200
    else:
        return jsonify({"status": "not ready", "reason": "database unavailable"}), 503


@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """
    Endpoint de liveness check (para Kubernetes/Railway).
    Verifica se a aplicação está viva (não travada).
    """
    return jsonify({"status": "alive"}), 200
