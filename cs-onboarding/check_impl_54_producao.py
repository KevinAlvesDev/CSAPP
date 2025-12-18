"""
Script para verificar se a implantação ID 54 existe no banco de produção
Execute este script conectado ao banco de produção (PostgreSQL)
"""
import os

# Configurar para usar o banco de PRODUÇÃO
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['DEBUG'] = 'False'
os.environ['FLASK_SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

# IMPORTANTE: Certifique-se de que DATABASE_URL está configurado para o banco de produção
# Se não estiver, descomente e configure abaixo:
# os.environ['DATABASE_URL'] = 'postgresql://...'

from backend.project import create_app
from backend.project.db import query_db

app = create_app()

with app.app_context():
    print("\n" + "="*80)
    print("VERIFICANDO IMPLANTAÇÃO ID 54 NO BANCO DE PRODUÇÃO")
    print("="*80 + "\n")
    
    # Verificar qual banco está sendo usado
    db_url = os.environ.get('DATABASE_URL', 'SQLite Local')
    print(f"🔗 Banco de dados: {db_url[:50]}...")
    print()
    
    # Verificar se ID 54 existe
    impl_54 = query_db("SELECT * FROM implantacoes WHERE id = %s", (54,), one=True)
    
    if impl_54:
        print("✅ IMPLANTAÇÃO ID 54 ENCONTRADA!")
        print("-" * 80)
        print(f"ID: {impl_54['id']}")
        print(f"Nome da Empresa: {impl_54.get('nome_empresa', 'N/A')}")
        print(f"Usuário CS: {impl_54.get('usuario_cs', 'N/A')}")
        print(f"ID Favorecido: {impl_54.get('id_favorecido', 'N/A')}")
        print(f"Chave OAMD: {impl_54.get('chave_oamd', 'N/A')}")
        print(f"Status: {impl_54.get('status', 'N/A')}")
        print("-" * 80)
        print("\n✅ A implantação existe. O erro 404 pode ser causado por:")
        print("   1. Problema de permissão (usuário não tem acesso)")
        print("   2. Erro na função consultar_dados_oamd")
        print("   3. Problema com o banco externo OAMD")
    else:
        print("❌ IMPLANTAÇÃO ID 54 NÃO ENCONTRADA!")
        print("-" * 80)
        print("\nIsso confirma que o erro 404 é legítimo.")
        print("A implantação foi deletada ou nunca existiu neste banco.")
        print()
        print("📋 Implantações próximas ao ID 54:")
        print()
        
        # Listar implantações próximas
        proximas = query_db(
            "SELECT id, nome_empresa, usuario_cs FROM implantacoes WHERE id BETWEEN %s AND %s ORDER BY id",
            (50, 60)
        )
        
        if proximas:
            print(f"{'ID':<6} {'Nome da Empresa':<50} {'Usuário CS':<30}")
            print("-" * 90)
            for impl in proximas:
                nome = (impl['nome_empresa'] or 'N/A')[:50]
                usuario = (impl['usuario_cs'] or 'N/A')[:30]
                print(f"{impl['id']:<6} {nome:<50} {usuario:<30}")
        else:
            print("Nenhuma implantação encontrada neste intervalo.")
    
    print("\n" + "="*80)
    print("FIM DA VERIFICAÇÃO")
    print("="*80 + "\n")
