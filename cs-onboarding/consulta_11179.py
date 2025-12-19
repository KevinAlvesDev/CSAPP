"""
Consulta completa para ID Favorecido 11179
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

ID_FAVORECIDO = 11179

with app.app_context():
    print("\n" + "="*80)
    print(f"  CONSULTA COMPLETA - ID FAVORECIDO {ID_FAVORECIDO}")
    print("="*80)
    
    try:
        # Query com JOIN
        result = query_external_db("""
            SELECT 
                ef.*,
                ps.datainicio as plano_data_inicio,
                ps.datafinal as plano_data_final,
                ps.dataconclusao as plano_data_conclusao,
                ps.duracao as plano_duracao,
                ps.porcentagemconcluida as plano_progresso,
                ps.nomeresponsavel as plano_responsavel,
                ps.nome as plano_nome
            FROM empresafinanceiro ef
            LEFT JOIN planosucesso ps ON ps.empresafinanceiro_codigo = ef.codigo
            WHERE ef.codigofinanceiro = :id
            ORDER BY ps.criadoem DESC
            LIMIT 1
        """, {'id': ID_FAVORECIDO})
        
        if not result:
            print(f"ID {ID_FAVORECIDO} nao encontrado!")
            sys.exit(1)
        
        data = result[0]
        
        print(f"\nEmpresa: {data['nomefantasia']}")
        print("\nTODOS OS CAMPOS:")
        print("-"*80)
        
        # Salvar tudo
        with open(f'consulta_completa_{ID_FAVORECIDO}.json', 'w', encoding='utf-8') as f:
            json.dump({k: str(v) if v else None for k, v in data.items()}, f, indent=2, ensure_ascii=False)
        
        print(f"\nDados salvos em: consulta_completa_{ID_FAVORECIDO}.json")
        
        # Mostrar campos importantes
        print("\nCAMPOS IMPORTANTES ENCONTRADOS:")
        print("-"*80)
        
        campos_importantes = {
            'CNPJ': data.get('cnpj'),
            'Status/Grupo': data.get('grupofavorecido'),
            'Tipo Grupo': data.get('tipogrupofavorecido'),
            'Nicho': data.get('nicho'),
            'Data Cadastro': data.get('datacadastro'),
            'Plano - Data Inicio': data.get('plano_data_inicio'),
            'Plano - Data Final': data.get('plano_data_final'),
            'Plano - Conclusao': data.get('plano_data_conclusao'),
            'Plano - Responsavel': data.get('plano_responsavel'),
        }
        
        for nome, valor in campos_importantes.items():
            if valor:
                print(f"  OK  {nome:<25} = {valor}")
            else:
                print(f"  --  {nome:<25} = (vazio)")
        
        # Buscar em detalheempresa se existir
        if data.get('detalheempresa_codigo'):
            print("\n" + "="*80)
            print("  BUSCANDO EM DETALHEEMPRESA")
            print("="*80)
            
            detalhe = query_external_db("""
                SELECT *
                FROM detalheempresa
                WHERE codigo = :cod
            """, {'cod': data['detalheempresa_codigo']})
            
            if detalhe:
                det = detalhe[0]
                print("\nCampos encontrados:")
                for key, value in sorted(det.items()):
                    if value:
                        print(f"  {key:<40} = {value}")
                
                # Salvar
                with open(f'detalheempresa_{ID_FAVORECIDO}.json', 'w', encoding='utf-8') as f:
                    json.dump({k: str(v) if v else None for k, v in det.items()}, f, indent=2, ensure_ascii=False)
                
                print(f"\nDetalhes salvos em: detalheempresa_{ID_FAVORECIDO}.json")
        
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n" + "="*80)
print("  FIM")
print("="*80 + "\n")
