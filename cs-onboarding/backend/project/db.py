from contextlib import contextmanager, suppress
from datetime import datetime

from flask import current_app

from .common.exceptions import DatabaseError
from .database import get_db_connection as get_pooled_connection


def get_db_connection():
    """
    Retorna uma conexão com o banco de dados (SQLite ou PostgreSQL).
    Agora usa connection pooling para PostgreSQL.
    """
    return get_pooled_connection()


@contextmanager
def db_connection():
    """
    Context manager para conexões de banco de dados.
    Garante que a conexão seja fechada corretamente, mesmo em caso de erro.
    """
    conn, db_type = None, None
    use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    try:
        conn, db_type = get_db_connection()
        yield conn, db_type
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if use_sqlite and conn:
            conn.close()


def query_db(query, args=(), one=False, raise_on_error=False):
    """
    Executa uma query SELECT (APENAS LEITURA) e retorna o resultado.
    """
    try:
        from .performance_monitoring import track_query

        track_query()
    except ImportError:
        # Módulo de monitoramento não disponível - ok continuar
        pass

    conn, db_type = None, None
    use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        if db_type == "sqlite":
            query = query.replace("%s", "?")

        cursor.execute(query, args)

        if one:
            result = cursor.fetchone()
            return dict(result) if result else None
        else:
            results = cursor.fetchall()
            return [dict(row) for row in results] if results else []

    except Exception as e:
        current_app.logger.error(f"Database query error: {e}", exc_info=True)
        current_app.logger.debug(f"Query: {query[:100]}...")
        if conn:
            conn.rollback()

        if raise_on_error:
            raise DatabaseError(f"Erro ao executar query: {e}", {"query": query[:100], "args": args}) from e

        return None if one else []
    finally:
        if use_sqlite and conn:
            conn.close()


def execute_db(query, args=(), raise_on_error=False):
    """
    Executa uma query de INSERT, UPDATE ou DELETE no banco de dados.
    """
    try:
        from .performance_monitoring import track_query

        track_query()
    except ImportError:
        # Módulo de monitoramento não disponível - ok continuar
        pass

    conn, db_type = None, None
    use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        if db_type == "sqlite":
            query = query.replace("%s", "?")

        cursor.execute(query, args)
        conn.commit()

        if cursor.lastrowid:
            return cursor.lastrowid
        return True

    except Exception as e:
        current_app.logger.error(f"Database execution error: {e}", exc_info=True)
        current_app.logger.debug(f"Query: {query[:100]}...")
        if conn:
            conn.rollback()

        if raise_on_error:
            raise DatabaseError(f"Erro ao executar query: {e}", {"query": query[:100], "args": args}) from e

        return None
    finally:
        if use_sqlite and conn:
            conn.close()


def execute_and_fetch_one(query, args=()):
    """
    Executa uma query de MUTATION (INSERT/UPDATE) que retorna um
    valor (ex: RETURNING id) e faz commit.
    """
    conn, db_type = None, None
    use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()

        if db_type == "sqlite":
            query = query.replace("%s", "?")

        cursor.execute(query, args)
        result = cursor.fetchone()
        conn.commit()

        return dict(result) if result else None

    except Exception as e:
        current_app.logger.error(f"Database execute_and_fetch error: {e}")
        current_app.logger.debug(f"Query: {query[:100]}...")
        if conn:
            conn.rollback()
        return None
    finally:
        if use_sqlite and conn:
            conn.close()


@contextmanager
def db_transaction_with_lock():
    """
    Context manager para transações com lock de linha.
    Garante atomicidade e previne race conditions.
    """
    conn, db_type = None, None
    use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)

    try:
        conn, db_type = get_db_connection()
        cursor = None

        if db_type == "sqlite":
            conn.execute("BEGIN IMMEDIATE TRANSACTION")
            cursor = conn.cursor()
        else:
            cursor = conn.cursor()

        yield conn, cursor, db_type

        if conn:
            with suppress(Exception):
                conn.commit()

    except Exception:
        if conn:
            with suppress(Exception):
                conn.rollback()
        raise
    finally:
        if use_sqlite and conn:
            with suppress(Exception):
                conn.close()


def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhe):
    conn, db_type = None, None
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO timeline_log (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao) VALUES (%s, %s, %s, %s, %s)"
        if db_type == "sqlite":
            sql = sql.replace("%s", "?")
        cursor.execute(sql, (implantacao_id, usuario_cs, tipo_evento, detalhe, datetime.now()))
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
    finally:
        use_sqlite = current_app.config.get("USE_SQLITE_LOCALLY", False)
        if use_sqlite and conn:
            conn.close()


# Schema initialization logic has been moved to backend/project/database/schema.py
