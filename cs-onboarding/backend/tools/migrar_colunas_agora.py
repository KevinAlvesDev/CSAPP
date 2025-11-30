#!/usr/bin/env python3
"""Script para executar migração de colunas no banco SQLite existente."""
import sys
import os
from pathlib import Path

# Adicionar backend ao path
root_path = Path(__file__).parent.parent.parent
backend_path = root_path / 'backend'
sys.path.insert(0, str(backend_path))

from project.db import init_db
from project import create_app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("Executando migração de colunas...")
        init_db()
        print("✅ Migração concluída!")

