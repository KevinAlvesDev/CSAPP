"""
Módulo de Connection Pooling para PostgreSQL.
Melhora performance e evita esgotamento de conexões.

Inclui:
- Retry logic para conexões instáveis (Railway, Render, etc.)
- Configurações conservadoras para planos com limites
- Timeouts configuráveis
- Fallback gracioso em caso de falha
"""

from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

import os
import time
from threading import Lock
from typing import TYPE_CHECKING, Any

from flask import current_app, g

if TYPE_CHECKING:
    from flask import Flask

# Imports condicionais para PostgreSQL
try:
    from psycopg2 import (
        OperationalError as PgOperationalError,
        pool,
    )
    from psycopg2.extras import DictCursor

    PSYCOPG2_AVAILABLE = True
except ImportError:
    pool = None  # type: ignore
    PgOperationalError = Exception  # type: ignore
    DictCursor = None  # type: ignore
    PSYCOPG2_AVAILABLE = False

_pg_pool: Any | None = None
_pool_lock = Lock()

# Configurações do pool (podem ser sobrescritas via env vars)
POOL_MIN_CONN = int(os.environ.get("DB_POOL_MIN", "2"))  # Reduzido de 10 para 2
POOL_MAX_CONN = int(os.environ.get("DB_POOL_MAX", "10"))  # Reduzido de 50 para 10
POOL_RETRY_ATTEMPTS = int(os.environ.get("DB_POOL_RETRIES", "3"))
POOL_RETRY_DELAY = float(os.environ.get("DB_POOL_RETRY_DELAY", "2.0"))
CONNECTION_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "10"))


def init_connection_pool(app: Flask) -> bool:
    """
    Inicializa o pool de conexões PostgreSQL com retry logic.
    Chamado durante a inicialização da aplicação.

    Returns:
        bool: True se inicializado com sucesso, False caso contrário
    """
    global _pg_pool

    if not PSYCOPG2_AVAILABLE:
        app.logger.warning("⚠️  psycopg2 não disponível - usando fallback")
        return False

    database_url = app.config.get("DATABASE_URL")
    if not database_url:
        app.logger.warning("⚠️  DATABASE_URL não configurado")
        return False

    # Adicionar parâmetros de conexão para robustez
    if "?" not in database_url:
        database_url += f"?connect_timeout={CONNECTION_TIMEOUT}"
    elif "connect_timeout" not in database_url:
        database_url += f"&connect_timeout={CONNECTION_TIMEOUT}"

    for attempt in range(1, POOL_RETRY_ATTEMPTS + 1):
        try:
            with _pool_lock:
                if _pg_pool is None:
                    app.logger.info(
                        f"🔄 Tentando inicializar pool de conexões (tentativa {attempt}/{POOL_RETRY_ATTEMPTS})..."
                    )

                    _pg_pool = pool.ThreadedConnectionPool(
                        minconn=POOL_MIN_CONN,
                        maxconn=POOL_MAX_CONN,
                        dsn=database_url,
                        options="-c search_path=public",
                        cursor_factory=DictCursor,
                    )

                    app.logger.info(
                        f"✅ Pool de conexões PostgreSQL inicializado ({POOL_MIN_CONN}-{POOL_MAX_CONN} conexões)"
                    )
                    return True
                else:
                    # Pool já inicializado
                    return True

        except PgOperationalError as e:
            error_msg = str(e)
            app.logger.warning(f"⚠️  Tentativa {attempt}/{POOL_RETRY_ATTEMPTS} falhou: {error_msg}", exc_info=True)

            if attempt < POOL_RETRY_ATTEMPTS:
                app.logger.info(f"⏳ Aguardando {POOL_RETRY_DELAY}s antes de tentar novamente...")
                time.sleep(POOL_RETRY_DELAY)
            else:
                app.logger.error(
                    f"❌ Falha ao inicializar pool após {POOL_RETRY_ATTEMPTS} tentativas. "
                    f"Verifique se o banco de dados está online e acessível."
                )
                # Não levantar exceção - permitir que a app inicie mesmo sem DB
                # Isso permite health checks e outras rotas funcionarem
                return False

        except Exception as e:
            app.logger.error(f"❌ Erro inesperado ao inicializar pool: {e}", exc_info=True)
            if attempt >= POOL_RETRY_ATTEMPTS:
                return False
            time.sleep(POOL_RETRY_DELAY)

    return False


def get_db_connection() -> tuple[Any, str]:
    """
    Retorna uma conexão do pool PostgreSQL.
    A conexão é armazenada em g.db e reutilizada durante a requisição.

    Returns:
        tuple: (connection, db_type) onde db_type é 'postgres'

    Raises:
        RuntimeError: Se o pool não estiver inicializado
    """
    return _get_postgres_connection()





def _get_postgres_connection() -> tuple[Any, str]:
    """Obtém conexão PostgreSQL do pool."""
    if _pg_pool is None:
        raise RuntimeError(
            "Connection pool not initialized. "
            "Verifique se o banco de dados está online e DATABASE_URL está configurado."
        )

    try:
        if "db_conn" not in g:
            g.db_conn = _pg_pool.getconn()
            g.db_type = "postgres"
        else:
            # Verificar se a conexão ainda está válida
            try:
                if getattr(g.db_conn, "closed", 1) != 0:
                    # Conexão fechada, obter nova
                    g.db_conn = _pg_pool.getconn()
                    g.db_type = "postgres"
            except Exception as exc:
                logger.exception("Unhandled exception", exc_info=True)
                # Erro ao verificar, obter nova conexão
                g.db_conn = _pg_pool.getconn()
                g.db_type = "postgres"

    except PgOperationalError as e:
        current_app.logger.error(f"Failed to get connection from pool: {e}", exc_info=True)
        raise RuntimeError(f"Database connection error: {e}") from e
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting connection: {e}", exc_info=True)
        raise

    return g.db_conn, g.db_type


def close_db_connection(error: Exception | None = None) -> None:
    """
    Retorna a conexão ao pool (PostgreSQL) ou fecha (SQLite).
    Deve ser chamado no teardown da requisição.
    """
    db_conn = g.pop("db_conn", None)
    db_type = g.pop("db_type", None)

    if db_conn is None:
        return

    if db_type == "postgres" and _pg_pool is not None:
        try:
            is_closed = getattr(db_conn, "closed", 1) != 0
            _pg_pool.putconn(db_conn, close=is_closed)
        except Exception as e:
            # Log mas não falhe - a conexão pode já estar inválida
            try:
                current_app.logger.debug(f"Error returning connection to pool: {e}")
                db_conn.close()
            except Exception as e:
                current_app.logger.warning(f"Falha ao fechar conexão após erro no pool: {e}", exc_info=True)


def close_all_connections() -> None:
    """
    Fecha todas as conexões do pool.
    Deve ser chamado no shutdown da aplicação.
    """
    global _pg_pool

    if _pg_pool is not None:
        with _pool_lock:
            try:
                _pg_pool.closeall()
            except Exception as e:
                logger.exception("Unhandled exception", exc_info=True)
                import logging
                logging.getLogger(__name__).warning(f"Falha ao fechar todas as conexões do pool: {e}", exc_info=True)
            finally:
                _pg_pool = None


def is_pool_initialized() -> bool:
    """Verifica se o pool está inicializado."""
    return _pg_pool is not None


def get_pool_stats() -> dict[str, Any]:
    """
    Retorna estatísticas do pool de conexões.
    Útil para monitoramento e debugging.
    """
    if _pg_pool is None:
        return {"initialized": False}

    try:
        return {
            "initialized": True,
            "min_connections": POOL_MIN_CONN,
            "max_connections": POOL_MAX_CONN,
            # ThreadedConnectionPool não expõe estatísticas detalhadas
            # mas podemos adicionar contadores customizados se necessário
        }
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        return {"initialized": True, "error": "Could not get stats"}