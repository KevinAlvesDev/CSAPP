from datetime import datetime, timedelta

from flask import current_app

from ..db import execute_db, query_db

ALLOWED_TABLES = [
    'usuarios',
    'perfil_usuario',
    'implantacoes',
    'timeline_log',
    'gamificacao_metricas_mensais',
    'gamificacao_regras',
    'smtp_settings',
    'checklist_items',
    'comentarios_h',
    'planos_sucesso',
]

ALLOWED_ID_COLUMNS = ['id', 'usuario', 'usuario_email']


def _validate_table_name(table: str) -> str:
    """
    Valida nome de tabela contra whitelist.

    Args:
        table: Nome da tabela a validar

    Returns:
        Nome da tabela validado

    Raises:
        ValueError: Se a tabela não estiver na whitelist
    """
    if table not in ALLOWED_TABLES:
        current_app.logger.warning(f"Tentativa de acesso a tabela não permitida: {table}")
        raise ValueError(f"Tabela não permitida: {table}")
    return table


def _validate_id_column(id_column: str) -> str:
    """
    Valida nome de coluna de ID contra whitelist.

    Args:
        id_column: Nome da coluna de ID a validar

    Returns:
        Nome da coluna validado

    Raises:
        ValueError: Se a coluna não estiver na whitelist
    """
    if id_column not in ALLOWED_ID_COLUMNS:
        current_app.logger.warning(f"Tentativa de uso de coluna não permitida: {id_column}")
        raise ValueError(f"Coluna de ID não permitida: {id_column}")
    return id_column


def soft_delete(table: str, record_id: int, id_column: str = 'id') -> bool:
    """
    Marca um registro como excluído (soft delete).

    SEGURANÇA: Valida nome da tabela e coluna contra whitelist para prevenir SQL Injection.

    Args:
        table: Nome da tabela (deve estar em ALLOWED_TABLES)
        record_id: ID do registro
        id_column: Nome da coluna de ID (deve estar em ALLOWED_ID_COLUMNS, padrão: 'id')

    Returns:
        True se sucesso, False se falha

    Raises:
        ValueError: Se tabela ou coluna não estiverem na whitelist

    Exemplo:
        soft_delete('implantacoes', 123)
        soft_delete('tarefas', 456)
    """
    try:
        table = _validate_table_name(table)
        id_column = _validate_id_column(id_column)
        now = datetime.now()
        query = f"UPDATE {table} SET deleted_at = %s WHERE {id_column} = %s AND deleted_at IS NULL"
        rows_affected = execute_db(query, (now, record_id))
        if rows_affected and rows_affected > 0:
            current_app.logger.info(f"Soft deleted {table} ID {record_id}")
            return True
        else:
            current_app.logger.warning(f"No rows affected when soft deleting {table} ID {record_id}")
            return False
    except ValueError as ve:
        current_app.logger.error(f"Validation error in soft_delete: {ve}")
        return False
    except Exception as e:
        current_app.logger.error(f"Error soft deleting {table} ID {record_id}: {e}")
        return False


def restore(table: str, record_id: int, id_column: str = 'id') -> bool:
    """
    Restaura um registro excluído (soft delete).

    SEGURANÇA: Valida nome da tabela e coluna contra whitelist para prevenir SQL Injection.

    Args:
        table: Nome da tabela (deve estar em ALLOWED_TABLES)
        record_id: ID do registro
        id_column: Nome da coluna de ID (deve estar em ALLOWED_ID_COLUMNS, padrão: 'id')

    Returns:
        True se sucesso, False se falha

    Exemplo:
        restore('implantacoes', 123)
    """
    try:
        table = _validate_table_name(table)
        id_column = _validate_id_column(id_column)
        query = f"UPDATE {table} SET deleted_at = NULL WHERE {id_column} = %s AND deleted_at IS NOT NULL"
        rows_affected = execute_db(query, (record_id,))
        if rows_affected and rows_affected > 0:
            current_app.logger.info(f"Restored {table} ID {record_id}")
            return True
        else:
            current_app.logger.warning(f"No rows affected when restoring {table} ID {record_id}")
            return False
    except ValueError as ve:
        current_app.logger.error(f"Validation error in restore: {ve}")
        return False
    except Exception as e:
        current_app.logger.error(f"Error restoring {table} ID {record_id}: {e}")
        return False


def hard_delete(table: str, record_id: int, id_column: str = 'id') -> bool:
    """
    Exclui permanentemente um registro (hard delete).

    ATENÇÃO: Esta operação é irreversível!
    SEGURANÇA: Valida nome da tabela e coluna contra whitelist para prevenir SQL Injection.

    Args:
        table: Nome da tabela (deve estar em ALLOWED_TABLES)
        record_id: ID do registro
        id_column: Nome da coluna de ID (deve estar em ALLOWED_ID_COLUMNS, padrão: 'id')

    Returns:
        True se sucesso, False se falha

    Exemplo:
        hard_delete('implantacoes', 123)
    """
    try:
        table = _validate_table_name(table)
        id_column = _validate_id_column(id_column)
        query = f"DELETE FROM {table} WHERE {id_column} = %s"
        rows_affected = execute_db(query, (record_id,))
        if rows_affected and rows_affected > 0:
            current_app.logger.warning(f"HARD DELETED {table} ID {record_id} - IRREVERSÍVEL!")
            return True
        else:
            current_app.logger.warning(f"No rows affected when hard deleting {table} ID {record_id}")
            return False
    except ValueError as ve:
        current_app.logger.error(f"Validation error in hard_delete: {ve}")
        return False
    except Exception as e:
        current_app.logger.error(f"Error hard deleting {table} ID {record_id}: {e}")
        return False


def get_deleted_records(table: str, limit: int = 100) -> list:
    """
    Retorna registros excluídos (soft delete).

    SEGURANÇA: Valida nome da tabela contra whitelist para prevenir SQL Injection.

    Args:
        table: Nome da tabela (deve estar em ALLOWED_TABLES)
        limit: Limite de registros (padrão: 100)

    Returns:
        Lista de registros excluídos

    Exemplo:
        deleted = get_deleted_records('implantacoes')
    """
    try:
        table = _validate_table_name(table)
        query = f"SELECT * FROM {table} WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT %s"
        records = query_db(query, (limit,))
        return records or []
    except ValueError as ve:
        current_app.logger.error(f"Validation error in get_deleted_records: {ve}")
        return []
    except Exception as e:
        current_app.logger.error(f"Error getting deleted records from {table}: {e}")
        return []


def cleanup_old_deleted_records(table: str, days: int = 30) -> int:
    """
    Remove permanentemente registros excluídos há mais de X dias.

    SEGURANÇA: Valida nome da tabela contra whitelist para prevenir SQL Injection.

    Args:
        table: Nome da tabela (deve estar em ALLOWED_TABLES)
        days: Dias desde a exclusão (padrão: 30)

    Returns:
        Número de registros removidos

    Exemplo:
        # Remove registros excluídos há mais de 30 dias
        cleanup_old_deleted_records('implantacoes', days=30)
    """
    try:
        table = _validate_table_name(table)
        cutoff_date = datetime.now() - timedelta(days=days)
        query = f"DELETE FROM {table} WHERE deleted_at IS NOT NULL AND deleted_at < %s"
        rows_affected = execute_db(query, (cutoff_date,))
        if rows_affected and rows_affected > 0:
            current_app.logger.info(f"Cleaned up {rows_affected} old deleted records from {table}")
            return rows_affected
        else:
            return 0
    except ValueError as ve:
        current_app.logger.error(f"Validation error in cleanup_old_deleted_records: {ve}")
        return 0
    except Exception as e:
        current_app.logger.error(f"Error cleaning up old deleted records from {table}: {e}")
        return 0


def exclude_deleted(query: str) -> str:
    """
    Adiciona filtro WHERE deleted_at IS NULL a uma query.

    Args:
        query: Query SQL

    Returns:
        Query modificada com filtro de soft delete

    Exemplo:
        query = "SELECT * FROM implantacoes WHERE usuario_cs = %s"
        query = exclude_deleted(query)
        # Resultado: "SELECT * FROM implantacoes WHERE usuario_cs = %s AND deleted_at IS NULL"
    """
    if 'WHERE' in query.upper():
        return query + " AND deleted_at IS NULL"
    else:
        return query + " WHERE deleted_at IS NULL"
