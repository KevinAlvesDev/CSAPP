"""
Script para listar TODAS as implantações em produção
Execute em produção: python listar_implantacoes_prod.py
"""
import os
import sys

# Configurar ambiente
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['DEBUG'] = 'False'
os.environ['FLASK_SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

from backend.project import create_app
from backend.project.db import query_db

app = create_app()

with app.app_context():
    print("\n" + "="*100)
    print("  LISTAGEM DE TODAS AS IMPLANTAÇÕES EM PRODUÇÃO")
    print("="*100)
    
    # Buscar TODAS as implantações (sem filtro de usuário)
    implantacoes = query_db("""
        SELECT 
            id, 
            nome_empresa, 
            usuario_cs, 
            status, 
            tipo,
            id_favorecido,
            data_criacao,
            data_inicio_efetivo
        FROM implantacoes
        ORDER BY id
    """)
    
    if not implantacoes:
        print("\n⚠️  NENHUMA implantação encontrada no banco!")
        sys.exit(0)
    
    print(f"\n📊 Total de implantações: {len(implantacoes)}")
    print("\n" + "-"*100)
    print(f"{'ID':<6} {'Nome Empresa':<30} {'Usuário CS':<30} {'Status':<15} {'ID Fav':<10}")
    print("-"*100)
    
    for impl in implantacoes:
        id_val = impl['id']
        nome = (impl['nome_empresa'] or 'N/A')[:30]
        usuario = (impl['usuario_cs'] or 'N/A')[:30]
        status = (impl['status'] or 'N/A')[:15]
        id_fav = impl['id_favorecido'] or 'N/A'
        
        print(f"{id_val:<6} {nome:<30} {usuario:<30} {status:<15} {id_fav:<10}")
    
    print("-"*100)
    
    # Estatísticas por status
    print("\n📈 Estatísticas por Status:")
    print("-"*50)
    
    stats = query_db("""
        SELECT status, COUNT(*) as total
        FROM implantacoes
        GROUP BY status
        ORDER BY total DESC
    """)
    
    for stat in stats:
        print(f"   {stat['status']:<20} = {stat['total']} implantações")
    
    # Verificar se ID 57 existe
    print("\n" + "="*100)
    print("  VERIFICAÇÃO ESPECÍFICA: ID 57")
    print("="*100)
    
    impl_57 = query_db("SELECT * FROM implantacoes WHERE id = 57", one=True)
    
    if impl_57:
        print("\n✅ Implantação ID 57 EXISTE!")
        print("-"*50)
        print(f"Nome: {impl_57['nome_empresa']}")
        print(f"Usuário CS: {impl_57['usuario_cs']}")
        print(f"Status: {impl_57['status']}")
        print(f"ID Favorecido: {impl_57['id_favorecido'] or 'NÃO INFORMADO'}")
        print(f"Data Criação: {impl_57['data_criacao']}")
    else:
        print("\n❌ Implantação ID 57 NÃO EXISTE no banco!")
        print("\nPossíveis causas:")
        print("   1. Foi excluída")
        print("   2. Nunca foi criada")
        print("   3. Você está olhando o banco errado")
    
    # Verificar maior ID
    maior_id = query_db("SELECT MAX(id) as max_id FROM implantacoes", one=True)
    print(f"\n📌 Maior ID no banco: {maior_id['max_id'] if maior_id else 'N/A'}")
    
    print("\n" + "="*100)
    print("  FIM DA LISTAGEM")
    print("="*100 + "\n")
