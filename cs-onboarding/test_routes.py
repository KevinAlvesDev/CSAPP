"""Script para verificar rotas registradas no Flask"""
import os
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['USE_SQLITE_LOCALLY'] = 'True'
os.environ['DEBUG'] = 'True'
os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key'

from backend.project import create_app

app = create_app()

print("\n=== ROTAS RELACIONADAS A OAMD ===\n")
oamd_routes = [rule for rule in app.url_map.iter_rules() if 'oamd' in str(rule).lower()]

if oamd_routes:
    for rule in oamd_routes:
        print(f"Endpoint: {rule.endpoint}")
        print(f"Rota: {rule.rule}")
        print(f"Métodos: {', '.join(rule.methods - {'HEAD', 'OPTIONS'})}")
        print("-" * 50)
else:
    print("❌ NENHUMA ROTA OAMD ENCONTRADA!")

print("\n=== TODAS AS ROTAS API V1 ===\n")
api_v1_routes = [rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/api/v1')]

for rule in api_v1_routes:
    print(f"{rule.rule} -> {', '.join(rule.methods - {'HEAD', 'OPTIONS'})}")
