"""Script para testar a rota OAMD consulta"""
import os
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['USE_SQLITE_LOCALLY'] = 'True'
os.environ['DEBUG'] = 'True'
os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key'
os.environ['EXTERNAL_DB_URL'] = 'postgresql+psycopg2://cs_pacto:pacto%40db@oamd.pactosolucoes.com.br:5432/OAMD'

from backend.project import create_app
from flask import g

app = create_app()

# Testar a rota com ID 54
impl_id = 54

with app.test_client() as client:
    with app.app_context():
        # Simular login
        with client.session_transaction() as sess:
            sess['user'] = {
                'email': 'suporte01.cs@gmail.com',
                'name': 'Admin',
                'sub': 'test|123'
            }
        
        print(f"\n=== TESTANDO ROTA: /api/v1/oamd/implantacoes/{impl_id}/consulta ===\n")
        
        # Fazer requisição
        response = client.get(f'/api/v1/oamd/implantacoes/{impl_id}/consulta')
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.content_type}")
        
        if response.status_code == 404:
            print("\n❌ ERRO 404 - Rota não encontrada!")
            print("\nPossíveis causas:")
            print("1. A implantação ID 54 não existe no banco de dados")
            print("2. Problema de autenticação/autorização")
            print("3. Blueprint não registrado corretamente")
        
        try:
            data = response.get_json()
            print(f"\nResposta JSON:")
            import json
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"\nErro ao parsear JSON: {e}")
            print(f"Resposta raw: {response.data.decode('utf-8')}")
