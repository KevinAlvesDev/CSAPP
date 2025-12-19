"""
Script com JOIN entre empresafinanceiro e planosucesso
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

ID_FAVORECIDO = 11350

with app.app_context():
    print("\n" + "="*80)
    print(f"  CONSULTA COM JOIN - ID FAVORECIDO {ID_FAVORECIDO}")
    print("="*80)
    
    try:
        # Query com LEFT JOIN para pegar dados da empresa E do plano de sucesso
        result = query_external_db("""
            SELECT 
                ef.codigo as empresa_codigo,
                ef.codigofinanceiro,
                ef.nomefantasia,
                ef.cnpj,
                ef.grupofavorecido,
                ef.tipogrupofavorecido,
                ef.datacadastro,
                ef.nicho,
                ef.detalheempresa_codigo,
                
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
            print("Nenhum resultado encontrado!")
            sys.exit(1)
        
        data = result[0]
        
        print("\nRESULTADO DA CONSULTA:")
        print("-"*80)
        
        print("\nDADOS DA EMPRESA:")
        print(f"  Nome: {data['nomefantasia']}")
        print(f"  CNPJ: {data['cnpj']}")
        print(f"  Codigo: {data['empresa_codigo']}")
        print(f"  Codigo Financeiro: {data['codigofinanceiro']}")
        print(f"  Grupo/Status: {data['grupofavorecido']}")
        print(f"  Tipo Grupo: {data['tipogrupofavorecido']}")
        print(f"  Nicho: {data['nicho']}")
        print(f"  Data Cadastro: {data['datacadastro']}")
        
        print("\nDADOS DO PLANO DE SUCESSO:")
        if data['plano_nome']:
            print(f"  Nome Plano: {data['plano_nome']}")
            print(f"  Data Inicio: {data['plano_data_inicio']}")
            print(f"  Data Final: {data['plano_data_final']}")
            print(f"  Data Conclusao: {data['plano_data_conclusao']}")
            print(f"  Duracao: {data['plano_duracao']} dias")
            print(f"  Progresso: {data['plano_progresso']}%")
            print(f"  Responsavel: {data['plano_responsavel']}")
        else:
            print("  (Nenhum plano de sucesso encontrado)")
        
        # Buscar detalhes adicionais se existir
        if data['detalheempresa_codigo']:
            print("\nBUSCANDO DETALHES ADICIONAIS...")
            try:
                detalhe = query_external_db("""
                    SELECT *
                    FROM detalheempresa
                    WHERE codigo = :cod
                """, {'cod': data['detalheempresa_codigo']})
                
                if detalhe:
                    det = detalhe[0]
                    print("\nDETALHE EMPRESA:")
                    for key, value in det.items():
                        if value and any(x in key.lower() for x in ['nivel', 'receita', 'atendimento', 
                                                                      'status', 'mrr', 'classificacao']):
                            print(f"  {key}: {value}")
            except Exception as e:
                print(f"  Erro ao buscar detalhes: {e}")
        
        # Resumo final
        print("\n" + "="*80)
        print("  MAPEAMENTO FINAL")
        print("="*80)
        
        mapeamento = {
            'cnpj': data['cnpj'],
            'status_implantacao': data['grupofavorecido'],
            'data_inicio_implantacao': data['plano_data_inicio'],
            'data_final_implantacao': data['plano_data_final'],
            'data_inicio_producao': None,  # NAO DISPONIVEL
            'nivel_atendimento': None,  # NAO DISPONIVEL
            'nivel_receita': None,  # NAO DISPONIVEL
        }
        
        print("\nCAMPOS DISPONIVEIS:")
        for key, value in mapeamento.items():
            if value:
                print(f"  OK  {key:<30} = {value}")
            else:
                print(f"  --  {key:<30} = (nao disponivel)")
        
        # Salvar
        with open('mapeamento_final_oamd.json', 'w', encoding='utf-8') as f:
            json.dump({k: str(v) if v else None for k, v in data.items()}, f, indent=2, ensure_ascii=False)
        
        print("\nDados completos salvos em: mapeamento_final_oamd.json")
        
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n" + "="*80)
print("  FIM")
print("="*80 + "\n")
