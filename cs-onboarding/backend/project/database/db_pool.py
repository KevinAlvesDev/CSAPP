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

import os
import sqlite3
import time
from threading import Lock
from typing import TYPE_CHECKING, Any, Optional

from flask import current_app, g

if TYPE_CHECKING:
    from flask import Flask

# Imports condicionais para PostgreSQL
try:
    from psycopg2 import pool, OperationalError as PgOperationalError
    from psycopg2.extras import DictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    pool = None  # type: ignore
    PgOperationalError = Exception  # type: ignore
    DictCursor = None  # type: ignore
    PSYCOPG2_AVAILABLE = False

_pg_pool: Optional[Any] = None
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

    if app.config.get("USE_SQLITE_LOCALLY", False):
        app.logger.info("🗄️  Usando SQLite - pool de conexões não necessário")
        return True
    
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
                        cursor_factory=DictCursor,
                    )
                    
                    app.logger.info(
                        f"✅ Pool de conexões PostgreSQL inicializado "
                        f"({POOL_MIN_CONN}-{POOL_MAX_CONN} conexões)"
                    )
                    return True
                else:
                    # Pool já inicializado
                    return True
                    
        except PgOperationalError as e:
            error_msg = str(e)
            app.logger.warning(
                f"⚠️  Tentativa {attempt}/{POOL_RETRY_ATTEMPTS} falhou: {error_msg}"
            )
            
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
            app.logger.error(f"❌ Erro inesperado ao inicializar pool: {e}")
            if attempt >= POOL_RETRY_ATTEMPTS:
                return False
            time.sleep(POOL_RETRY_DELAY)
    
    return False


def get_db_connection() -> tuple[Any, str]:
    """
    Retorna uma conexão do pool (PostgreSQL) ou cria nova (SQLite).
    Para PostgreSQL, a conexão é armazenada em g.db e reutilizada durante a requisição.
    
    Returns:
        tuple: (connection, db_type) onde db_type é 'postgres' ou 'sqlite'
        
    Raises:
        RuntimeError: Se o pool não estiver inicializado e não for SQLite
    """
    use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    if use_sqlite:
        return _get_sqlite_connection()
    else:
        return _get_postgres_connection()


def _get_sqlite_connection() -> tuple[Any, str]:
    """Obtém conexão SQLite."""
    try:
        database_url = current_app.config.get("DATABASE_URL", "")
        
        if database_url and database_url.startswith("sqlite"):
            db_path = database_url.replace("sqlite:///", "")
            
            if db_path == ":memory:":
                pass
            elif not os.path.isabs(db_path):
                base_dir = os.path.abspath(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                )
                db_path = os.path.join(base_dir, db_path)
        else:
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            is_testing = current_app.config.get("TESTING", False)
            db_filename = "dashboard_simples_test.db" if is_testing else "dashboard_simples.db"
            db_path = os.path.join(base_dir, db_filename)

        conn = sqlite3.connect(db_path, isolation_level=None, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"
        
    except sqlite3.Error as e:
        current_app.logger.error(f"SQLite connection error: {e}")
        raise


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
            except Exception:
                # Erro ao verificar, obter nova conexão
                g.db_conn = _pg_pool.getconn()
                g.db_type = "postgres"
                
    except PgOperationalError as e:
        current_app.logger.error(f"Failed to get connection from pool: {e}")
        raise RuntimeError(f"Database connection error: {e}") from e
    except Exception as e:
        current_app.logger.error(f"Unexpected error getting connection: {e}")
        raise

    return g.db_conn, g.db_type


def close_db_connection(error: Optional[Exception] = None) -> None:
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
            except Exception:
                pass
                
    elif db_type == "sqlite":
        try:
            db_conn.close()
        except Exception:
            pass


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
            except Exception:
                pass
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
    except Exception:
        return {"initialized": True, "error": "Could not get stats"}

