"""
Script para executar migration e adicionar coluna plano_id à tabela checklist_items.
Este script pode ser executado manualmente se a migration Alembic não funcionar.
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.project.db import db_connection
from backend.project import create_app

def executar_migration():
    """Executa a migration para adicionar coluna plano_id."""
    
    print("🔄 Executando migration para adicionar coluna plano_id...")
    
    with db_connection() as (conn, db_type):
        cursor = conn.cursor()
        
        try:
            if db_type == 'postgres':
                # PostgreSQL
                print("📊 Banco de dados: PostgreSQL")
                
                # Verificar se coluna já existe
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='checklist_items' AND column_name='plano_id'
                """)
                
                if cursor.fetchone():
                    print("✅ Coluna plano_id já existe na tabela checklist_items")
                else:
                    # Adicionar coluna
                    cursor.execute("""
                        ALTER TABLE checklist_items 
                        ADD COLUMN plano_id INTEGER REFERENCES planos_sucesso(id) ON DELETE CASCADE
                    """)
                    print("✅ Coluna plano_id adicionada")
                
                # Criar índices
                indices = [
                    ("idx_checklist_plano_id", "ON checklist_items(plano_id)"),
                    ("idx_checklist_plano_ordem", "ON checklist_items(plano_id, ordem)"),
                    ("idx_checklist_plano_parent", "ON checklist_items(plano_id, parent_id)")
                ]
                
                for idx_name, idx_def in indices:
                    try:
                        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} {idx_def}")
                        print(f"✅ Índice {idx_name} criado")
                    except Exception as e:
                        print(f"⚠️ Índice {idx_name} pode já existir: {e}")
                
                conn.commit()
                print("✅ Migration executada com sucesso!")
                
            else:
                # SQLite
                print("📊 Banco de dados: SQLite")
                
                # Verificar se coluna já existe
                cursor.execute("PRAGMA table_info(checklist_items)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'plano_id' in columns:
                    print("✅ Coluna plano_id já existe na tabela checklist_items")
                else:
                    # Adicionar coluna
                    cursor.execute("ALTER TABLE checklist_items ADD COLUMN plano_id INTEGER")
                    print("✅ Coluna plano_id adicionada")
                
                # Criar índices
                indices = [
                    ("idx_checklist_plano_id", "ON checklist_items(plano_id)"),
                    ("idx_checklist_plano_ordem", "ON checklist_items(plano_id, ordem)"),
                    ("idx_checklist_plano_parent", "ON checklist_items(plano_id, parent_id)")
                ]
                
                for idx_name, idx_def in indices:
                    try:
                        cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} {idx_def}")
                        print(f"✅ Índice {idx_name} criado")
                    except Exception as e:
                        print(f"⚠️ Índice {idx_name} pode já existir: {e}")
                
                conn.commit()
                print("✅ Migration executada com sucesso!")
                
        except Exception as e:
            conn.rollback()
            print(f"❌ Erro ao executar migration: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Migration: Adicionar coluna plano_id à checklist_items")
    print("=" * 60)
    print()
    
    # Criar aplicação Flask para ter contexto
    app = create_app()
    
    with app.app_context():
        sucesso = executar_migration()
    
    print()
    print("=" * 60)
    if sucesso:
        print("✅ Migration concluída com sucesso!")
    else:
        print("❌ Migration falhou. Verifique os erros acima.")
    print("=" * 60)

