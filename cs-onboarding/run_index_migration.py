"""
Script para executar migration de índices com contexto Flask
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.project import create_app
from backend.project.database.migrations.add_performance_indexes import run_migration

if __name__ == "__main__":
    app = create_app()
    
    with app.app_context():
        print("🚀 Executando migration de índices de performance...")
        success = run_migration()
        
        if success:
            print("\n✅ Migration executada com sucesso!")
            print("\n📊 Impacto esperado:")
            print("  • Checklist: 60-80% mais rápido")
            print("  • Dashboard: 40-60% mais rápido")
            print("  • Timeline: 30-50% mais rápido")
        else:
            print("\n❌ Falha na migration. Verifique os logs.")
            sys.exit(1)
