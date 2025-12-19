"""
Script para entender o relacionamento entre tabelas e buscar TODOS os dados necessarios
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
    print(f"  BUSCANDO TODOS OS DADOS PARA ID FAVORECIDO {ID_FAVORECIDO}")
    print("="*80)
    
    try:
        # 1. Dados da empresa
        print("\n1. DADOS DA EMPRESA (empresafinanceiro):")
        print("-"*80)
        
        empresa = query_external_db("""
            SELECT *
            FROM empresafinanceiro
            WHERE codigofinanceiro = :id
        """, {'id': ID_FAVORECIDO})
        
        if not empresa:
            print("Empresa nao encontrada!")
            sys.exit(1)
        
        empresa = empresa[0]
        codigo_empresa = empresa['codigo']
        
        print(f"Nome: {empresa['nomefantasia']}")
        print(f"Codigo Empresa: {codigo_empresa}")
        print(f"Codigo Financeiro: {empresa['codigofinanceiro']}")
        print(f"CNPJ: {empresa['cnpj']}")
        print(f"Grupo: {empresa['grupofavorecido']}")
        
        # 2. Plano de Sucesso
        print("\n2. PLANO DE SUCESSO (planosucesso):")
        print("-"*80)
        
        plano = query_external_db("""
            SELECT *
            FROM planosucesso
            WHERE empresafinanceiro_codigo = :cod
            ORDER BY criadoem DESC
            LIMIT 1
        """, {'cod': codigo_empresa})
        
        if plano:
            plano = plano[0]
            print(f"Nome Plano: {plano['nome']}")
            print(f"Data Inicio: {plano['datainicio']}")
            print(f"Data Final: {plano['datafinal']}")
            print(f"Data Conclusao: {plano['dataconclusao']}")
            print(f"Duracao: {plano['duracao']} dias")
            print(f"Progresso: {plano['porcentagemconcluida']}%")
            print(f"Responsavel: {plano['nomeresponsavel']}")
        else:
            print("Nenhum plano de sucesso encontrado")
        
        # 3. Tentar buscar em outras tabelas
        print("\n3. OUTRAS TABELAS:")
        print("-"*80)
        
        # Tentar detalheempresa
        try:
            detalhe = query_external_db("""
                SELECT *
                FROM detalheempresa
                WHERE codigo = :cod
            """, {'cod': empresa.get('detalheempresa_codigo')})
            
            if detalhe:
                print("\n*** DETALHE EMPRESA ***")
                detalhe = detalhe[0]
                for key, value in detalhe.items():
                    if any(x in key.lower() for x in ['nivel', 'receita', 'atendimento', 'status']):
                        print(f"  {key}: {value}")
        except:
            pass
        
        # 4. Resumo final
        print("\n" + "="*80)
        print("  RESUMO - DADOS DISPONIVEIS")
        print("="*80)
        
        resultado = {
            'cnpj': empresa.get('cnpj'),
            'status_implantacao': empresa.get('grupofavorecido'),
            'data_inicio_implantacao': plano.get('datainicio') if plano else None,
            'data_final_implantacao': plano.get('datafinal') if plano else None,
            'data_conclusao': plano.get('dataconclusao') if plano else None,
            'duracao_dias': plano.get('duracao') if plano else None,
            'progresso': plano.get('porcentagemconcluida') if plano else None,
            'responsavel': plano.get('nomeresponsavel') if plano else None,
            'nivel_atendimento': None,  # NAO ENCONTRADO
            'nivel_receita': None,  # NAO ENCONTRADO
            'data_inicio_producao': None,  # NAO ENCONTRADO
        }
        
        print("\nDADOS ENCONTRADOS:")
        for key, value in resultado.items():
            status = "OK" if value else "NAO ENCONTRADO"
            print(f"  {key:<30} = {value} [{status}]")
        
        # Salvar resultado
        with open('resumo_dados_oamd.json', 'w', encoding='utf-8') as f:
            json.dump({k: str(v) if v else None for k, v in resultado.items()}, f, indent=2, ensure_ascii=False)
        
        print("\nResumo salvo em: resumo_dados_oamd.json")
        
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\n" + "="*80)
print("  FIM")
print("="*80 + "\n")
