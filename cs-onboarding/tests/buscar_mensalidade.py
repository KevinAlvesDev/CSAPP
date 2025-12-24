"""
Script para buscar informações de mensalidade/contrato no OAMD.
"""
import os
import sys

# Configurar variáveis de ambiente ANTES de importar
os.environ['EXTERNAL_DB_URL'] = 'postgresql://cs_pacto:pacto@db@oamd.pactosolucoes.com.br:5432/OAMD'
os.environ['EXTERNAL_DB_PROXY_URL'] = 'socks5://localhost:50022'
os.environ['EXTERNAL_DB_TIMEOUT'] = '10'

# Adicionar o diretório raiz ao path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)

from backend.project import create_app
from backend.project.database.external_db import query_external_db

app = create_app({
    'TESTING': True,
    'DEBUG': True,
    'USE_SQLITE_LOCALLY': True,
    'AUTH0_ENABLED': False,
    'SECRET_KEY': 'test-secret',
    'EXTERNAL_DB_URL': os.environ['EXTERNAL_DB_URL'],
    'WTF_CSRF_ENABLED': False,
})

def buscar_mensalidade(id_favorecido=11287):
    """Busca informações de mensalidade para uma empresa"""
    with app.app_context():
        print(f"\n=== BUSCANDO MENSALIDADE PARA ID {id_favorecido} ===\n")
        
        # Buscar tabelas que podem conter informações de contrato
        query_tabelas = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name LIKE '%contrat%'
            ORDER BY table_name
        """
        tabelas = query_external_db(query_tabelas)
        
        print("Tabelas encontradas com 'contrat':")
        for t in tabelas:
            print(f"  - {t['table_name']}")
        
        # Tentar buscar em cada tabela
        for t in tabelas:
            tabela = t['table_name']
            print(f"\n--- Explorando {tabela} ---")
            
            # Listar colunas
            query_colunas = f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{tabela}'
                ORDER BY ordinal_position
            """
            colunas = query_external_db(query_colunas)
            col_names = [c['column_name'] for c in colunas]
            print(f"Colunas: {', '.join(col_names)}")
            
            # Procurar por colunas que podem referenciar a empresa
            colunas_empresa = [c for c in col_names if any(x in c.lower() for x in ['empresa', 'favorecido', 'cliente', 'codigo'])]
            
            if colunas_empresa:
                for col in colunas_empresa:
                    try:
                        query_dados = f"SELECT * FROM {tabela} WHERE {col} = :id ORDER BY criadoem DESC LIMIT 5"
                        dados = query_external_db(query_dados, {'id': id_favorecido})
                        if dados:
                            print(f"\n  OK Encontrado {len(dados)} registro(s) em {tabela}.{col}:")
                            for i, row in enumerate(dados, 1):
                                print(f"\n  Registro {i}:")
                                for k, v in row.items():
                                    if v and str(v).strip():
                                        print(f"    {k}: {v}")
                    except Exception as e:
                        # Tentar sem ORDER BY se não tiver criadoem
                        try:
                            query_dados = f"SELECT * FROM {tabela} WHERE {col} = :id LIMIT 5"
                            dados = query_external_db(query_dados, {'id': id_favorecido})
                            if dados:
                                print(f"\n  OK Encontrado {len(dados)} registro(s) em {tabela}.{col}:")
                                for i, row in enumerate(dados, 1):
                                    print(f"\n  Registro {i}:")
                                    for k, v in row.items():
                                        if v and str(v).strip():
                                            print(f"    {k}: {v}")
                        except Exception as e2:
                            pass

if __name__ == '__main__':
    print("=" * 60)
    print("BUSCA DE MENSALIDADE - BANCO OAMD")
    print("=" * 60)
    
    buscar_mensalidade(11287)  # ID do exemplo que você deu
    
    print("\n" + "=" * 60)
    print("BUSCA CONCLUIDA")
    print("=" * 60)
