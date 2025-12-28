
import sys
import os
import json
from flask import Flask

# Adiciona o diretório backend ao path
sys.path.insert(0, os.path.abspath('c:/Users/Usuário/Desktop/github4/CSAPP/cs-onboarding/backend'))

from project.domain.planos.crud import obter_plano_completo

app = Flask(__name__)
app.config['USE_SQLITE_LOCALLY'] = True

def test_plano_json():
    with app.app_context():
        print("Buscando plano 1...")
        try:
            plano = obter_plano_completo(1)
            if not plano:
                print("Plano não encontrado.")
                return

            print(f"Plano encontrado: {plano.get('nome')}")
            
            # Tentar extrair apenas o necessário para o JSON
            plano_json = {
                'id': plano.get('id'),
                'nome': plano.get('nome'),
                'descricao': plano.get('descricao'),
                'items': plano.get('items', [])
            }
            
            print("Tentando serializar para JSON...")
            json_str = json.dumps(plano_json, default=str)
            print("Sucesso! JSON gerado (primeiros 200 chars):")
            print(json_str[:200])
            
            # Verificar items
            items = plano.get('items', [])
            print(f"Total de items raiz: {len(items)}")
            if len(items) > 0:
                print(f"Exemplo de item: {items[0].keys()}")
                
        except Exception as e:
            print(f"ERRO: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_plano_json()
