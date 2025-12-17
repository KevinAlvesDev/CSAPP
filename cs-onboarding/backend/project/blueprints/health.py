"""
Blueprint para health checks e monitoramento.
"""

from datetime import datetime

from botocore.exceptions import ClientError
from flask import Blueprint, current_app, jsonify

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


def check_external_database_connection():
    """
    Verifica se a conexão com o banco de dados externo está funcionando.
    Retorna (status: bool, message: str, response_time_ms: float)
    """
    if not current_app.config.get('EXTERNAL_DB_URL'):
        return False, "Not configured", 0.0

    start_time = datetime.now()
    try:
        from ..database.external_db import query_external_db

        # Tenta uma query simples
        # Nota: "SELECT 1" funciona na maioria dos bancos SQL (Postgres, MySQL, SQL Server, SQLite)
        # Para Oracle seria "SELECT 1 FROM DUAL"
        result = query_external_db("SELECT 1 as test")

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        if result and len(result) > 0:
            return True, "External connection OK", response_time
        else:
            return False, "External query returned no result", response_time

    except Exception as e:
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000
        return False, f"External connection failed: {str(e)}", response_time


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


@health_bp.route('/ip', methods=['GET'])
def get_public_ip_route():
    """
    Retorna o IP público do servidor onde a aplicação está rodando.
    Útil para configurar whitelists de banco de dados.
    """
    try:
        import urllib.request
        # Tenta obter IP via serviço externo
        with urllib.request.urlopen('https://api.ipify.org', timeout=5) as response:
            public_ip = response.read().decode('utf8')
        
        return jsonify({
            'status': 'success',
            'public_ip': public_ip,
            'message': 'Use este IP para liberar acesso no firewall do banco de dados.'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Não foi possível determinar o IP público: {str(e)}'
        }), 500


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Endpoint de health check para monitoramento.
    Retorna status da aplicação, banco de dados e serviços externos.
    """

    db_status, db_message, db_response_time = check_database_connection()

    ext_db_status, ext_db_message, ext_db_response_time = check_external_database_connection()
    has_external_db = current_app.config.get('EXTERNAL_DB_URL') is not None

    r2_status, r2_message = check_r2_connection()

    overall_status = "healthy" if db_status else "unhealthy"
    # Se banco externo estiver configurado mas falhando, considera unhealthy?
    # Por enquanto, vamos considerar warning, mas não derrubar o health check principal
    # a menos que seja crítico. Vamos manter "healthy" se o principal estiver ok.

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

    if has_external_db:
        response["checks"]["external_database"] = {
            "status": "up" if ext_db_status else "down",
            "message": ext_db_message,
            "response_time_ms": round(ext_db_response_time, 2)
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
    ext_ok = True
    if current_app.config.get('EXTERNAL_DB_URL'):
        try:
            from .blueprints.health import check_external_database_connection
            ext_ok, _, _ = check_external_database_connection()
        except Exception:
            ext_ok = False
    if db_status and ext_ok:
        return jsonify({"status": "ready"}), 200
    reason = "database unavailable" if not db_status else "external database unavailable"
    return jsonify({"status": "not ready", "reason": reason}), 503


@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """
    Endpoint de liveness check (para Kubernetes/Railway).
    Verifica se a aplicação está viva (não travada).
    """
    return jsonify({"status": "alive"}), 200
