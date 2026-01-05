"""
Script para executar migration de tag em comentarios_h
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.project import create_app
from backend.project.database.migrations.add_tag_comentarios import run_migration

if __name__ == "__main__":
    app = create_app()
    
    with app.app_context():
        print("🚀 Adicionando coluna 'tag' em comentarios_h...")
        success = run_migration()
        
        if success:
            print("\n✅ Migration executada com sucesso!")
            print("A coluna 'tag' agora está disponível em comentarios_h")
        else:
            print("\n❌ Falha na migration. Verifique os logs.")
            sys.exit(1)
