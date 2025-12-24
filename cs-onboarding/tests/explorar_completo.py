"""
Script para buscar tabelas de pagamento/faturamento no OAMD.
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

def listar_todas_tabelas():
    """Lista TODAS as tabelas do banco"""
    with app.app_context():
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        tabelas = query_external_db(query)
        
        print("\n=== TODAS AS TABELAS DO BANCO OAMD ===\n")
        for t in tabelas:
            print(f"  {t['table_name']}")
        
        return [t['table_name'] for t in tabelas]

def buscar_em_tabela_especifica(tabela, id_favorecido=11287):
    """Busca dados em uma tabela específica"""
    with app.app_context():
        print(f"\n=== EXPLORANDO {tabela.upper()} ===")
        
        # Listar colunas
        query_colunas = f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{tabela}'
            ORDER BY ordinal_position
        """
        colunas = query_external_db(query_colunas)
        col_names = [c['column_name'] for c in colunas]
        print(f"Colunas ({len(col_names)}): {', '.join(col_names)}")
        
        # Procurar colunas que podem ter valor/preço
        colunas_valor = [c for c in col_names if any(x in c.lower() for x in ['valor', 'preco', 'price', 'amount', 'total'])]
        if colunas_valor:
            print(f"Colunas de valor encontradas: {', '.join(colunas_valor)}")
        
        # Procurar por colunas que podem referenciar a empresa
        colunas_empresa = [c for c in col_names if any(x in c.lower() for x in ['empresa', 'favorecido', 'cliente', 'codigo'])]
        
        if colunas_empresa:
            for col in colunas_empresa[:3]:  # Limitar a 3 colunas para não demorar muito
                try:
                    query_dados = f"SELECT * FROM {tabela} WHERE {col} = :id LIMIT 3"
                    dados = query_external_db(query_dados, {'id': id_favorecido})
                    if dados:
                        print(f"\n  OK Encontrado {len(dados)} registro(s) em {tabela}.{col}:")
                        for i, row in enumerate(dados, 1):
                            print(f"\n  Registro {i}:")
                            # Mostrar apenas campos relevantes
                            for k, v in row.items():
                                if v and str(v).strip() and any(x in k.lower() for x in ['descri', 'valor', 'preco', 'data', 'nome', 'tipo']):
                                    print(f"    {k}: {v}")
                        return True
                except Exception as e:
                    pass
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("EXPLORADOR COMPLETO - BANCO OAMD")
    print("=" * 60)
    
    # Listar todas as tabelas
    tabelas = listar_todas_tabelas()
    
    # Focar em tabelas que podem ter informações financeiras
    tabelas_interesse = [t for t in tabelas if any(x in t.lower() for x in 
        ['item', 'parcela', 'receb', 'pag', 'fatur', 'financ', 'cobranca', 'mensalidade', 'plano'])]
    
    print(f"\n\n=== TABELAS DE INTERESSE ({len(tabelas_interesse)}) ===")
    for t in tabelas_interesse:
        print(f"  - {t}")
    
    # Explorar cada uma
    print("\n\n=== EXPLORANDO TABELAS ===")
    for tabela in tabelas_interesse:
        buscar_em_tabela_especifica(tabela, 11287)
    
    print("\n" + "=" * 60)
    print("EXPLORACAO CONCLUIDA")
    print("=" * 60)
