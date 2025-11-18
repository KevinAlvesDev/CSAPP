
"""
Módulo de Connection Pooling para PostgreSQL.
Melhora performance e evita esgotamento de conexões.
"""

import sqlite3
import psycopg2
from psycopg2 import pool
from psycopg2.extras import DictCursor
from flask import current_app, g
import os
from threading import Lock

_pg_pool = None
_pool_lock = Lock()


def init_connection_pool(app):
    """
    Inicializa o pool de conexões PostgreSQL.
    Chamado durante a inicialização da aplicação.
    """
    global _pg_pool

    if not app.config.get('USE_SQLITE_LOCALLY', False):
        database_url = app.config.get('DATABASE_URL')
        if database_url:
            try:
                with _pool_lock:
                    if _pg_pool is None:

                        _pg_pool = pool.ThreadedConnectionPool(
                            minconn=5,
                            maxconn=20,
                            dsn=database_url,
                            cursor_factory=DictCursor
                        )
                        app.logger.info("PostgreSQL connection pool initialized (5-20 connections)")
            except Exception as e:
                app.logger.error(f"Failed to initialize connection pool: {e}")
                raise


def get_db_connection():
    """
    Retorna uma conexão do pool (PostgreSQL) ou cria nova (SQLite).
    Para PostgreSQL, a conexão é armazenada em g.db e reutilizada durante a requisição.
    """
    use_sqlite = current_app.config.get('USE_SQLITE_LOCALLY', False)
    
    if use_sqlite:
        try:
            base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            is_testing = current_app.config.get('TESTING', False)
            db_filename = 'dashboard_simples_test.db' if is_testing else 'dashboard_simples.db'
            db_path = os.path.join(base_dir, db_filename)
            conn = sqlite3.connect(db_path, isolation_level=None)
            conn.row_factory = sqlite3.Row
            return conn, 'sqlite'
        except sqlite3.Error as e:
            current_app.logger.error(f"SQLite connection error: {e}")
            raise
    else:
        try:
            if _pg_pool is None:
                raise RuntimeError("Connection pool not initialized")
            if 'db_conn' not in g:
                g.db_conn = _pg_pool.getconn()
                g.db_type = 'postgres'
            else:
                try:
                    if getattr(g.db_conn, 'closed', 1) != 0:
                        g.db_conn = _pg_pool.getconn()
                        g.db_type = 'postgres'
                except Exception:
                    g.db_conn = _pg_pool.getconn()
                    g.db_type = 'postgres'
        except Exception as e:
            current_app.logger.error(f"Failed to get connection from pool: {e}")
            raise

        return g.db_conn, g.db_type


def close_db_connection(error=None):
    """
    Retorna a conexão ao pool (PostgreSQL) ou fecha (SQLite).
    Deve ser chamado no teardown da requisição.
    """
    db_conn = g.pop('db_conn', None)
    db_type = g.pop('db_type', None)
    
    if db_conn is not None:
        if db_type == 'postgres' and _pg_pool is not None:
            try:
                is_closed = getattr(db_conn, 'closed', 1) != 0
                _pg_pool.putconn(db_conn, close=is_closed)
            except Exception:
                try:
                    db_conn.close()
                except Exception:
                    pass
        elif db_type == 'sqlite':
            db_conn.close()


def close_all_connections():
    """
    Fecha todas as conexões do pool.
    Deve ser chamado no shutdown da aplicação.
    """
    global _pg_pool
    
    if _pg_pool is not None:
        with _pool_lock:
            _pg_pool.closeall()
            _pg_pool = None

