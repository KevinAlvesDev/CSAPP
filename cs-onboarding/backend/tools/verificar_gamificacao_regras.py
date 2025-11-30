#!/usr/bin/env python3
"""
Script para verificar se a tabela gamificacao_regras tem dados.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project import create_app
from project.db import query_db

def verificar_regras():
    """Verifica se há regras na tabela gamificacao_regras."""
    app = create_app()
    with app.app_context():
        try:
            regras = query_db("SELECT * FROM gamificacao_regras")
            print(f"\n📊 Total de regras encontradas: {len(regras) if regras else 0}\n")
            
            if regras:
                print("✅ Regras encontradas:")
                for regra in regras[:10]:  # Mostrar apenas as primeiras 10
                    print(f"  - {regra.get('regra_id', 'N/A')}: {regra.get('valor_pontos', 'N/A')} pontos")
                if len(regras) > 10:
                    print(f"  ... e mais {len(regras) - 10} regras")
            else:
                print("❌ Nenhuma regra encontrada na tabela!")
                print("   A tabela pode estar vazia ou não ter sido inicializada.")
                print("   Execute o init_db() para inserir as regras padrão.")
            
        except Exception as e:
            print(f"❌ Erro ao verificar regras: {e}")
            print("   A tabela pode não existir ainda.")

if __name__ == '__main__':
    print("🔍 Verificando regras de gamificação...")
    verificar_regras()

