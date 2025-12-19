"""
Script para listar todas as tabelas do banco OAMD e procurar dados de implantacao
"""
import os
import sys
import json

os.environ['SECRET_KEY'] = 'dev-secret-key'
os.environ['DEBUG'] = 'True'
os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key'

from backend.project import create_app
from backend.project.database.external_db import query_external_db

app = create_app()

with app.app_context():
    print("\n" + "="*80)
    print("  LISTANDO TODAS AS TABELAS DO BANCO OAMD")
    print("="*80)
    
    try:
        # 1. Listar todas as tabelas
        tables = query_external_db("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        print(f"\nTotal de tabelas: {len(tables)}")
        print("\nTabelas relacionadas a implantacao/cliente/contrato:")
        print("-"*80)
        
        impl_tables = []
        for t in tables:
            name = t['table_name']
            if any(x in name.lower() for x in ['implant', 'cliente', 'contrato', 'atendimento', 
                                                 'producao', 'status', 'plano', 'sucesso']):
                impl_tables.append(name)
                print(f"  * {name}")
        
        # 2. Para cada tabela relacionada, ver campos
        print("\n" + "="*80)
        print("  CAMPOS DAS TABELAS RELACIONADAS")
        print("="*80)
        
        for table in impl_tables[:10]:  # Limitar a 10 tabelas
            print(f"\n--- Tabela: {table} ---")
            
            cols = query_external_db(f"""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY ordinal_position
            """)
            
            # Destacar campos de data/status/nivel
            important_cols = []
            for col in cols:
                name = col['column_name']
                if any(x in name.lower() for x in ['data', 'inicio', 'final', 'status', 
                                                     'nivel', 'receita', 'atendimento', 'producao']):
                    important_cols.append(col)
            
            if important_cols:
                print(f"Campos importantes ({len(important_cols)}):")
                for col in important_cols:
                    print(f"  - {col['column_name']:<40} ({col['data_type']})")
            else:
                print(f"Total de campos: {len(cols)} (nenhum campo de data/status)")
        
        # 3. Tentar buscar dados do ID 11350 em tabelas relacionadas
        print("\n" + "="*80)
        print("  BUSCANDO DADOS DO ID 11350 EM OUTRAS TABELAS")
        print("="*80)
        
        for table in impl_tables[:5]:
            try:
                # Tentar buscar por diferentes campos
                for field in ['codigofinanceiro', 'codigo', 'empresa_id', 'favorecido_id']:
                    try:
                        result = query_external_db(f"""
                            SELECT *
                            FROM {table}
                            WHERE {field} = :id
                            LIMIT 1
                        """, {'id': 11350})
                        
                        if result:
                            print(f"\n*** ENCONTRADO em {table} (campo: {field}) ***")
                            data = result[0]
                            
                            # Salvar em arquivo
                            filename = f"oamd_{table}_11350.json"
                            with open(filename, 'w', encoding='utf-8') as f:
                                json.dump({k: str(v) for k, v in data.items()}, f, indent=2, ensure_ascii=False)
                            
                            print(f"Dados salvos em: {filename}")
                            print(f"Total de campos: {len(data)}")
                            
                            # Mostrar campos importantes
                            for key, value in data.items():
                                if any(x in key.lower() for x in ['data', 'inicio', 'final', 'status', 
                                                                    'nivel', 'receita', 'atendimento']):
                                    print(f"  {key:<40} = {value}")
                            break
                    except:
                        pass
            except Exception as e:
                pass
        
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n" + "="*80)
print("  FIM")
print("="*80 + "\n")
