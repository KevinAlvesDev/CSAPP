"""Script para listar implantações disponíveis"""
import os
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['USE_SQLITE_LOCALLY'] = 'True'
os.environ['DEBUG'] = 'True'
os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key'

from backend.project import create_app
from backend.project.db import query_db

app = create_app()

with app.app_context():
    print("\n=== IMPLANTAÇÕES DISPONÍVEIS ===\n")
    
    implantacoes = query_db("SELECT id, nome_empresa, usuario_cs, id_favorecido FROM implantacoes ORDER BY id DESC LIMIT 20")
    
    if implantacoes:
        print(f"{'ID':<6} {'Nome da Empresa':<40} {'Usuário CS':<30} {'ID Favorecido':<15}")
        print("-" * 100)
        for impl in implantacoes:
            print(f"{impl['id']:<6} {(impl['nome_empresa'] or 'N/A')[:40]:<40} {(impl['usuario_cs'] or 'N/A')[:30]:<30} {impl.get('id_favorecido') or 'N/A':<15}")
    else:
        print("❌ Nenhuma implantação encontrada no banco de dados!")
    
    # Verificar se ID 54 existe
    print("\n=== VERIFICANDO ID 54 ===\n")
    impl_54 = query_db("SELECT * FROM implantacoes WHERE id = 54", one=True)
    
    if impl_54:
        print("✅ Implantação ID 54 encontrada:")
        for key, value in impl_54.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Implantação ID 54 NÃO EXISTE no banco de dados!")
        print("\nIsso explica o erro 404. O frontend está tentando acessar uma implantação que não existe.")
