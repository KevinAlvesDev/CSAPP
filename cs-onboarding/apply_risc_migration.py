"""
Script para aplicar a migração da tabela risc_events.
Executa a criação da tabela para armazenar logs de eventos RISC.
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).resolve().parent  # cs-onboarding
sys.path.insert(0, str(root_dir))

from backend.project.database import get_db_connection


def apply_migration():
    """Aplica a migração da tabela risc_events."""
    
    migration_file = root_dir / 'migrations' / 'create_risc_events_table.sql'
    
    if not migration_file.exists():
        print(f"[ERRO] Arquivo de migracao nao encontrado: {migration_file}")
        return False
    
    print(f"[INFO] Lendo migracao: {migration_file}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        # Criar contexto da aplicação Flask
        from backend.project import create_app
        app = create_app()
        
        with app.app_context():
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            
            print(f"[INFO] Aplicando migracao no banco de dados ({db_type})...")
            
            # Executar cada statement SQL
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print("[OK] Migracao aplicada com sucesso!")
            print("[INFO] Tabela 'risc_events' criada.")
            return True
        
    except Exception as e:
        print(f"[ERRO] Erro ao aplicar migracao: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("Migracao: Criar tabela risc_events")
    print("=" * 60)
    
    success = apply_migration()
    
    if success:
        print("\n[OK] Migracao concluida com sucesso!")
        sys.exit(0)
    else:
        print("\n[ERRO] Falha na migracao.")
        sys.exit(1)
