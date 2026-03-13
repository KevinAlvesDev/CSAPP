from contextlib import contextmanager, suppress
from datetime import datetime, timezone
import logging
logger = logging.getLogger(__name__)

from flask import current_app

from .common.exceptions import DatabaseError
from .database import get_db_connection as get_pooled_connection


from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

def get_db_connection():
    """
    Retorna uma conexão com o banco de dados (PostgreSQL).
    Usa connection pooling.
    """
    return get_pooled_connection()

# --- Configuração SQLAlchemy ORM ---
Session = scoped_session(sessionmaker())


def _track_query_safely():
    try:
        from .monitoring.performance_monitoring import track_query

        track_query()
    except ImportError:
        # Módulo de monitoramento não disponível - ok continuar
        pass


def _db_error(prefix: str, query: str, err: Exception, conn=None, raise_on_error: bool = False, args=()):
    current_app.logger.error(f"{prefix}: {err}", exc_info=True)
    current_app.logger.debug(f"Query: {query[:100]}...")
    if conn:
        conn.rollback()
    if raise_on_error:
        raise DatabaseError(f"Erro ao executar query: {err}", {"query": query[:100], "args": args}) from err

def init_db_session(app):
    """Inicializa o engine e a sessão do SQLAlchemy."""
    database_url = app.config.get("DATABASE_URL")
    if not database_url:
        return
    
    # Criar engine com pool compatível com o existente
    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )
    
    Session.configure(bind=engine)
    app.logger.info("✅ SQLAlchemy Scoped Session inicializada")


@contextmanager
def db_connection():
    """
    Context manager para conexões de banco de dados.
    Garante que a conexão seja fechada corretamente, mesmo em caso de erro.
    """
    conn = None

    try:
        conn = get_db_connection()[0]
        yield conn, "postgres"
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        if conn:
            conn.rollback()
        raise


def query_db(query, args=(), one=False, raise_on_error=False):
    """
    Executa uma query SELECT (APENAS LEITURA) e retorna o resultado.
    """
    _track_query_safely()

    conn = None

    try:
        conn = get_db_connection()[0]
        cursor = conn.cursor()

        cursor.execute(query, args)

        if one:
            result = cursor.fetchone()
            return dict(result) if result else None
        else:
            results = cursor.fetchall()
            return [dict(row) for row in results] if results else []

    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        _db_error("Database query error", query, e, conn=conn, raise_on_error=raise_on_error, args=args)
        return None if one else []


def execute_db(query, args=(), raise_on_error=False):
    """
    Executa uma query de INSERT, UPDATE ou DELETE no banco de dados.
    """
    _track_query_safely()

    conn = None

    try:
        conn = get_db_connection()[0]
        cursor = conn.cursor()

        cursor.execute(query, args)

        returned_value = None
        # Apenas queries com RETURNING possuem resultado para fetchone.
        if cursor.description:
            row = cursor.fetchone()
            if row:
                returned_value = row[0]

        conn.commit()

        if returned_value is not None:
            return returned_value

        if cursor.rowcount is not None and cursor.rowcount >= 0:
            return cursor.rowcount

        return True

    except Exception as e:
        logger.exception("Unhandled exception", exc_info=True)
        _db_error("Database execution error", query, e, conn=conn, raise_on_error=raise_on_error, args=args)
        return None


@contextmanager
def db_transaction_with_lock():
    """
    Context manager para transações com lock de linha.
    Garante atomicidade e previne race conditions.
    """
    conn = None

    try:
        conn = get_db_connection()[0]
        cursor = conn.cursor()

        yield conn, cursor, "postgres"

        if conn:
            with suppress(Exception):
                conn.commit()

    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        if conn:
            with suppress(Exception):
                conn.rollback()
        raise


def logar_timeline(implantacao_id, usuario_cs, tipo_evento, detalhe):
    sql = """
        INSERT INTO timeline_log
            (implantacao_id, usuario_cs, tipo_evento, detalhes, data_criacao)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_db(sql, (implantacao_id, usuario_cs, tipo_evento, detalhe, datetime.now(timezone.utc)))


# Schema initialization logic has been moved to backend/project/database/schema.py
