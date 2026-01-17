"""
Migration: Adicionar coluna 'tag' na tabela comentarios_h
Data: 2026-01-05
Objetivo: Sincronizar schema local com produção
"""

import logging

from ...database.db_pool import get_db_connection

logger = logging.getLogger(__name__)


def run_migration():
    """
    Adiciona a coluna 'tag' na tabela comentarios_h se não existir.
    """
    conn, db_type = get_db_connection()
    cursor = conn.cursor()

    try:
        logger.info("Verificando se coluna 'tag' existe em comentarios_h...")

        # Verificar se a coluna já existe
        if db_type == "postgres":
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='comentarios_h' AND column_name='tag'
            """)
            exists = cursor.fetchone() is not None
        else:
            # SQLite
            cursor.execute("PRAGMA table_info(comentarios_h)")
            columns = [row[1] for row in cursor.fetchall()]
            exists = "tag" in columns

        if exists:
            logger.info("✅ Coluna 'tag' já existe em comentarios_h")
            return True

        # Adicionar a coluna
        logger.info("Adicionando coluna 'tag' em comentarios_h...")
        cursor.execute("ALTER TABLE comentarios_h ADD COLUMN tag TEXT")

        conn.commit()
        logger.info("✅ Coluna 'tag' adicionada com sucesso!")
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erro ao adicionar coluna 'tag': {e}", exc_info=True)
        return False

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    success = run_migration()
    if success:
        print("✅ Migration executada com sucesso!")
    else:
        print("❌ Falha na migration. Verifique os logs.")
