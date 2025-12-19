"""
Script Simples para Investigar Schema OAMD (sem emojis para Windows)
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
    print("  INVESTIGACAO DO SCHEMA DO BANCO EXTERNO OAMD")
    print("="*80)
    
    try:
        # Teste com ID Favorecido 11350
        print("\nTESTE COM ID FAVORECIDO 11350:")
        print("-"*80)
        
        test_result = query_external_db("""
            SELECT *
            FROM empresafinanceiro
            WHERE codigofinanceiro = :id_fav
        """, {'id_fav': 11350})
        
        if test_result:
            empresa = test_result[0]
            print(f"\nEmpresa encontrada: {empresa.get('nomefantasia')}")
            print(f"\nTODOS OS CAMPOS ({len(empresa)} campos):")
            print("-"*80)
            
            # Salvar em arquivo JSON
            output_file = 'campos_oamd_11350.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({k: str(v) for k, v in empresa.items()}, f, indent=2, ensure_ascii=False)
            
            print(f"\nDados salvos em: {output_file}")
            
            # Mostrar campos importantes
            print("\nCAMPOS IMPORTANTES:")
            print("-"*80)
            important_keys = ['cnpj', 'status', 'nivel', 'receita', 'atendimento', 
                            'data', 'inicio', 'final', 'producao', 'implantacao']
            
            for key in sorted(empresa.keys()):
                value = empresa[key]
                if any(x in key.lower() for x in important_keys):
                    print(f"  * {key:<40} = {value}")
        else:
            print("\nEmpresa NAO encontrada!")
        
        # Listar campos da tabela
        print("\n" + "="*80)
        print("CAMPOS DA TABELA empresafinanceiro:")
        print("="*80)
        
        columns = query_external_db("""
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_name = 'empresafinanceiro'
            ORDER BY ordinal_position
        """)
        
        print(f"\nTotal: {len(columns)} campos")
        for col in columns:
            print(f"  - {col['column_name']:<40} ({col['data_type']})")
        
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n" + "="*80)
print("  FIM")
print("="*80 + "\n")
