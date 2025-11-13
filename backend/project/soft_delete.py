# project/soft_delete.py
# Utilitários para soft delete (exclusão lógica)

from datetime import datetime
from flask import current_app
from .db import execute_db, query_db


def soft_delete(table: str, record_id: int, id_column: str = 'id') -> bool:
    """
    Marca um registro como excluído (soft delete).
    
    Args:
        table: Nome da tabela
        record_id: ID do registro
        id_column: Nome da coluna de ID (padrão: 'id')
    
    Returns:
        True se sucesso, False se falha
    
    Exemplo:
        soft_delete('implantacoes', 123)
        soft_delete('tarefas', 456)
    """
    try:
        now = datetime.now()
        
        query = f"UPDATE {table} SET deleted_at = %s WHERE {id_column} = %s AND deleted_at IS NULL"
        rows_affected = execute_db(query, (now, record_id))
        
        if rows_affected and rows_affected > 0:
            current_app.logger.info(f"Soft deleted {table} ID {record_id}")
            return True
        else:
            current_app.logger.warning(f"No rows affected when soft deleting {table} ID {record_id}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error soft deleting {table} ID {record_id}: {e}")
        return False


def restore(table: str, record_id: int, id_column: str = 'id') -> bool:
    """
    Restaura um registro excluído (soft delete).
    
    Args:
        table: Nome da tabela
        record_id: ID do registro
        id_column: Nome da coluna de ID (padrão: 'id')
    
    Returns:
        True se sucesso, False se falha
    
    Exemplo:
        restore('implantacoes', 123)
    """
    try:
        query = f"UPDATE {table} SET deleted_at = NULL WHERE {id_column} = %s AND deleted_at IS NOT NULL"
        rows_affected = execute_db(query, (record_id,))
        
        if rows_affected and rows_affected > 0:
            current_app.logger.info(f"Restored {table} ID {record_id}")
            return True
        else:
            current_app.logger.warning(f"No rows affected when restoring {table} ID {record_id}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error restoring {table} ID {record_id}: {e}")
        return False


def hard_delete(table: str, record_id: int, id_column: str = 'id') -> bool:
    """
    Exclui permanentemente um registro (hard delete).
    
    ATENÇÃO: Esta operação é irreversível!
    
    Args:
        table: Nome da tabela
        record_id: ID do registro
        id_column: Nome da coluna de ID (padrão: 'id')
    
    Returns:
        True se sucesso, False se falha
    
    Exemplo:
        hard_delete('implantacoes', 123)
    """
    try:
        query = f"DELETE FROM {table} WHERE {id_column} = %s"
        rows_affected = execute_db(query, (record_id,))
        
        if rows_affected and rows_affected > 0:
            current_app.logger.warning(f"HARD DELETED {table} ID {record_id} - IRREVERSÍVEL!")
            return True
        else:
            current_app.logger.warning(f"No rows affected when hard deleting {table} ID {record_id}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error hard deleting {table} ID {record_id}: {e}")
        return False


def get_deleted_records(table: str, limit: int = 100) -> list:
    """
    Retorna registros excluídos (soft delete).
    
    Args:
        table: Nome da tabela
        limit: Limite de registros (padrão: 100)
    
    Returns:
        Lista de registros excluídos
    
    Exemplo:
        deleted = get_deleted_records('implantacoes')
    """
    try:
        query = f"SELECT * FROM {table} WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT %s"
        records = query_db(query, (limit,))
        return records or []
    except Exception as e:
        current_app.logger.error(f"Error getting deleted records from {table}: {e}")
        return []


def cleanup_old_deleted_records(table: str, days: int = 30) -> int:
    """
    Remove permanentemente registros excluídos há mais de X dias.
    
    Args:
        table: Nome da tabela
        days: Dias desde a exclusão (padrão: 30)
    
    Returns:
        Número de registros removidos
    
    Exemplo:
        # Remove registros excluídos há mais de 30 dias
        cleanup_old_deleted_records('implantacoes', days=30)
    """
    try:
        # Calcula data limite
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = f"DELETE FROM {table} WHERE deleted_at IS NOT NULL AND deleted_at < %s"
        rows_affected = execute_db(query, (cutoff_date,))
        
        if rows_affected and rows_affected > 0:
            current_app.logger.info(f"Cleaned up {rows_affected} old deleted records from {table}")
            return rows_affected
        else:
            return 0
            
    except Exception as e:
        current_app.logger.error(f"Error cleaning up old deleted records from {table}: {e}")
        return 0


# Decorador para adicionar filtro de soft delete automaticamente
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
    # Detecta se já tem WHERE
    if 'WHERE' in query.upper():
        return query + " AND deleted_at IS NULL"
    else:
        return query + " WHERE deleted_at IS NULL"

