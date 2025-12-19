"""
Script para Investigar Schema do Banco Externo OAMD
COM CREDENCIAIS CONFIGURADAS

Uso: python investigar_schema_oamd_configured.py
"""
import os
import sys

# Configurar ambiente COM credenciais do banco externo
os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['DEBUG'] = 'True'
os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key'
os.environ['EXTERNAL_DB_URL'] = 'postgresql://cs_pacto:pacto@db@oamd.pactosolucoes.com.br:5432/OAMD'

from backend.project import create_app
from backend.project.database.external_db import query_external_db

app = create_app()

with app.app_context():
    print("\n" + "="*100)
    print("  INVESTIGAÇÃO DO SCHEMA DO BANCO EXTERNO OAMD")
    print("="*100)
    
    try:
        # 1. Listar todas as tabelas
        print("\n📊 TABELAS DISPONÍVEIS:")
        print("-"*100)
        
        tables = query_external_db("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        if not tables:
            print("⚠️  Nenhuma tabela encontrada!")
            sys.exit(1)
        
        table_names = [t['table_name'] for t in tables]
        print(f"\nTotal de tabelas: {len(table_names)}")
        for i, name in enumerate(table_names, 1):
            print(f"  {i}. {name}")
        
        # 2. Focar na tabela empresafinanceiro (que já usamos)
        print("\n" + "="*100)
        print("  CAMPOS DA TABELA: empresafinanceiro")
        print("="*100)
        
        columns = query_external_db("""
            SELECT 
                column_name, 
                data_type,
                character_maximum_length,
                is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'empresafinanceiro'
            ORDER BY ordinal_position
        """)
        
        print(f"\nTotal de campos: {len(columns)}")
        print("\n" + "-"*100)
        print(f"{'Campo':<40} {'Tipo':<20} {'Tamanho':<10} {'Nulo?':<10}")
        print("-"*100)
        
        for col in columns:
            nome = col['column_name']
            tipo = col['data_type']
            tamanho = col['character_maximum_length'] or '-'
            nulo = col['is_nullable']
            print(f"{nome:<40} {tipo:<20} {str(tamanho):<10} {nulo:<10}")
        
        # 3. Buscar campos que parecem ser de implantação/datas
        print("\n" + "="*100)
        print("  CAMPOS RELACIONADOS A DATAS/IMPLANTAÇÃO")
        print("="*100)
        
        date_fields = [c for c in columns if any(x in c['column_name'].lower() for x in 
                      ['data', 'inicio', 'final', 'producao', 'implantacao', 'cadastro', 'status', 'nivel', 'receita', 'atendimento'])]
        
        if date_fields:
            print(f"\nEncontrados {len(date_fields)} campos relevantes:")
            print("-"*100)
            for col in date_fields:
                print(f"  📅 {col['column_name']:<40} ({col['data_type']})")
        else:
            print("\n⚠️  Nenhum campo de data/implantação encontrado em empresafinanceiro")
        
        # 4. Testar query com ID Favorecido 11350
        print("\n" + "="*100)
        print("  TESTE COM ID FAVORECIDO 11350")
        print("="*100)
        
        test_result = query_external_db("""
            SELECT *
            FROM empresafinanceiro
            WHERE codigofinanceiro = %s
        """, (11350,))
        
        if test_result:
            empresa = test_result[0]
            print(f"\n✅ Empresa encontrada!")
            print(f"Nome: {empresa.get('nomefantasia')}")
            print(f"\nTODOS OS CAMPOS RETORNADOS:")
            print("-"*100)
            
            for key in sorted(empresa.keys()):
                value = empresa[key]
                # Destacar campos importantes
                if any(x in key.lower() for x in ['data', 'inicio', 'final', 'status', 'nivel', 'cnpj']):
                    print(f"  ⭐ {key:<40} = {value}")
                else:
                    print(f"     {key:<40} = {value}")
        else:
            print("\n❌ Empresa não encontrada!")
        
        # 5. Verificar se há outras tabelas relacionadas
        print("\n" + "="*100)
        print("  PROCURANDO TABELAS RELACIONADAS A IMPLANTAÇÃO")
        print("="*100)
        
        impl_tables = [t for t in table_names if any(x in t.lower() for x in 
                      ['implant', 'cliente', 'contrato', 'atendimento', 'producao'])]
        
        if impl_tables:
            print(f"\nEncontradas {len(impl_tables)} tabelas relacionadas:")
            for table in impl_tables:
                print(f"  📋 {table}")
                
                # Mostrar campos de cada tabela
                cols = query_external_db(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """)
                
                print(f"     Campos ({len(cols)}):")
                for col in cols[:10]:  # Mostrar apenas primeiros 10
                    print(f"       - {col['column_name']} ({col['data_type']})")
                if len(cols) > 10:
                    print(f"       ... e mais {len(cols) - 10} campos")
                print()
        else:
            print("\n⚠️  Nenhuma tabela relacionada encontrada")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n" + "="*100)
print("  FIM DA INVESTIGAÇÃO")
print("="*100 + "\n")
