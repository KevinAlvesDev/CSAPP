import sys
sys.path.insert(0, 'backend')

from project import create_app
from project.db import query_db

app = create_app()

with app.app_context():
    result = query_db("SELECT id, nome_empresa FROM implantacoes ORDER BY id DESC LIMIT 10")
    if result:
        print(f"Total encontrado: {len(result)}")
        for r in result:
            print(f"ID: {r['id']}, Nome: {r['nome_empresa']}")
    else:
        print("Nenhuma implantação encontrada")

