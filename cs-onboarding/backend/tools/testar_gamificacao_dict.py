#!/usr/bin/env python3
"""
Script para testar a função _get_gamification_rules_as_dict().
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project import create_app
from project.domain.gamification_service import _get_gamification_rules_as_dict
from project.db import query_db

def testar():
    """Testa a função de buscar regras."""
    app = create_app()
    with app.app_context():
        print("🔍 Testando _get_gamification_rules_as_dict()...\n")
        
        # Testar query direta
        print("1. Query direta:")
        try:
            regras_raw = query_db("SELECT regra_id, valor_pontos FROM gamificacao_regras")
            print(f"   Resultado: {regras_raw}")
            print(f"   Tipo: {type(regras_raw)}")
            print(f"   Tamanho: {len(regras_raw) if regras_raw else 0}")
            if regras_raw:
                print(f"   Primeiro item: {regras_raw[0]}")
                print(f"   Tipo do primeiro item: {type(regras_raw[0])}")
                if isinstance(regras_raw[0], dict):
                    print(f"   Chaves: {list(regras_raw[0].keys())}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        
        print("\n2. Função _get_gamification_rules_as_dict():")
        try:
            result = _get_gamification_rules_as_dict()
            print(f"   Resultado: {result}")
            print(f"   Tipo: {type(result)}")
            print(f"   Tamanho: {len(result) if result else 0}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    testar()

