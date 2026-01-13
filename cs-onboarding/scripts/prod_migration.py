
import os
import sys
import logging
from datetime import datetime

# Add root folder to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.project import create_app
from backend.project.db import get_db_connection

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    app = create_app()
    
    with app.app_context():
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        logger.info(f"Connected to database: {db_type}")
        
        try:
            # =========================================================
            # 1. Structure Migration (Columns)
            # =========================================================
            logger.info("Checking schema structure...")
            
            # Helper to check and add column
            def ensure_column(table, column, definition_pg, definition_sqlite):
                exists = False
                if db_type == 'postgres':
                    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{column}'")
                    exists = cursor.fetchone() is not None
                else:
                    cursor.execute(f"PRAGMA table_info({table})")
                    exists = any(row[1] == column for row in cursor.fetchall())
                
                if not exists:
                    logger.info(f"Adding column {column} to {table}...")
                    definition = definition_pg if db_type == 'postgres' else definition_sqlite
                    try:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                        conn.commit()
                        logger.info(f" -> {column} added.")
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"Failed to add {column}: {e}")
                else:
                    logger.info(f" -> {column} exists.")

            # Columns for comentarios_h
            ensure_column('comentarios_h', 'checklist_item_id', 'INTEGER REFERENCES checklist_items(id)', 'INTEGER REFERENCES checklist_items(id)')
            ensure_column('comentarios_h', 'tag', 'VARCHAR(50)', 'TEXT')
            ensure_column('comentarios_h', 'visibilidade', "VARCHAR(20) DEFAULT 'interno'", "TEXT DEFAULT 'interno'")
            ensure_column('comentarios_h', 'noshow', "INTEGER DEFAULT 0", "INTEGER DEFAULT 0") # Boolean in PG often mapped to 0/1 or BOOL, keeping INT for compat
            ensure_column('comentarios_h', 'imagem_url', 'TEXT', 'TEXT')

            # =========================================================
            # 1.0.1 Implantacoes Columns (Contexto, Carteira)
            # =========================================================
            logger.info("Checking implantacoes columns...")
            ensure_column('implantacoes', 'contexto', 'TEXT', 'TEXT')
            ensure_column('implantacoes', 'definicao_carteira', 'TEXT', 'TEXT')
            
            # =========================================================
            # 1.1 Planos Sucesso Columns
            # =========================================================
            logger.info("Checking planos_sucesso columns...")
            ensure_column('planos_sucesso', 'data_atualizacao', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
            ensure_column('planos_sucesso', 'dias_duracao', 'INTEGER', 'INTEGER')

            # =========================================================
            # 1.2 Jira Links Table
            # =========================================================
            logger.info("Checking implants_jira_links table...")
            table_jira = 'implantacao_jira_links'
            exists_jira = False
            if db_type == 'postgres':
                cursor.execute(f"SELECT to_regclass('{table_jira}')")
                exists_jira = cursor.fetchone()[0] is not None
            else:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_jira}'")
                exists_jira = cursor.fetchone() is not None

            if not exists_jira:
                logger.info(f"Creating table {table_jira}...")
                create_jira_sql_pg = """
                    CREATE TABLE implantacao_jira_links (
                        id SERIAL PRIMARY KEY,
                        implantacao_id INTEGER NOT NULL REFERENCES implantacoes(id) ON DELETE CASCADE,
                        jira_key VARCHAR(20) NOT NULL,
                        data_vinculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        vinculado_por TEXT,
                        UNIQUE(implantacao_id, jira_key)
                    );
                """
                create_jira_sql_sqlite = """
                    CREATE TABLE implantacao_jira_links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        implantacao_id INTEGER NOT NULL,
                        jira_key VARCHAR(20) NOT NULL,
                        data_vinculo DATETIME DEFAULT CURRENT_TIMESTAMP,
                        vinculado_por TEXT,
                        FOREIGN KEY (implantacao_id) REFERENCES implantacoes(id) ON DELETE CASCADE,
                        UNIQUE(implantacao_id, jira_key)
                    );
                """
                cursor.execute(create_jira_sql_pg if db_type == 'postgres' else create_jira_sql_sqlite)
                conn.commit()
                logger.info(f" -> {table_jira} created.")
            else:
                logger.info(f" -> {table_jira} exists.")

            # =========================================================
            # 2. Data Backfill (Legacy Comments -> History)
            # =========================================================
            logger.info("Checking for legacy comments to backfill...")
            
            # Select items with comments
            query_items = "SELECT id, title, responsavel, comment, updated_at, created_at FROM checklist_items WHERE comment IS NOT NULL AND comment != ''"
            cursor.execute(query_items)
            items_with_comments = cursor.fetchall()
            
            backfilled_count = 0
            
            for item in items_with_comments:
                # Handle tuple/dict result depending on factory
                item_id = item[0] if isinstance(item, tuple) else item['id']
                item_title = item[1] if isinstance(item, tuple) else item['title']
                item_resp = item[2] if isinstance(item, tuple) else item['responsavel']
                item_comment = item[3] if isinstance(item, tuple) else item['comment']
                item_date = item[4] or item[5] or datetime.now() # updated_at or created_at or now
                if isinstance(item, tuple): pass # already unpacked
                else:
                    item_date = item['updated_at'] or item['created_at']

                # Check if has history
                cursor.execute("SELECT COUNT(*) FROM comentarios_h WHERE checklist_item_id = %s" % ('%s' if db_type == 'postgres' else '?'), (item_id,))
                count = cursor.fetchone()[0]
                
                if count == 0:
                    # Insert legacy comment as history
                    logger.info(f"Backfilling history for item {item_id}...")
                    insert_sql = """
                        INSERT INTO comentarios_h (checklist_item_id, usuario_cs, texto, data_criacao, visibilidade, tag)
                        VALUES (%s, %s, %s, %s, 'interno', 'Simples registro')
                    """
                    if db_type == 'sqlite': insert_sql = insert_sql.replace('%s', '?')
                    
                    # Ensure user or default
                    user_log = item_resp if item_resp and '@' in item_resp else 'Sistema'
                    
                    cursor.execute(insert_sql, (item_id, user_log, item_comment, item_date))
                    backfilled_count += 1
            
            conn.commit()
            logger.info(f"Backfill complete. {backfilled_count} comments migrated.")
            
            logger.info("Migration finished successfully.")
            
        except Exception as e:
            logger.error(f"Critical error during migration: {e}", exc_info=True)
            if conn: conn.rollback()
        finally:
            if conn: conn.close()

if __name__ == '__main__':
    run_migration()
