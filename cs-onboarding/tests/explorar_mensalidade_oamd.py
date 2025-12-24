"""
Script para explorar o banco OAMD e encontrar informações de mensalidade.
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

def explorar_tabelas():
    """Lista todas as tabelas do banco OAMD"""
    with app.app_context():
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        tabelas = query_external_db(query)
        print("\n=== TABELAS DO BANCO OAMD ===")
        for t in tabelas:
            print(f"  - {t['table_name']}")
        return [t['table_name'] for t in tabelas]

def buscar_mensalidade_por_empresa(id_favorecido):
    """Busca informações de mensalidade para uma empresa específica"""
    with app.app_context():
        # Tentar encontrar em tabelas que podem conter informações de contrato/mensalidade
        tabelas_candidatas = [
            'contrato',
            'contratoitem',
            'financeiro',
            'recebimento',
            'faturamento',
            'mensalidade',
            'cobranca',
            'parcela'
        ]
        
        print(f"\n=== BUSCANDO MENSALIDADE PARA ID FAVORECIDO {id_favorecido} ===\n")
        
        for tabela in tabelas_candidatas:
            try:
                # Tentar listar colunas da tabela
                query_colunas = f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{tabela}'
                    ORDER BY ordinal_position
                """
                colunas = query_external_db(query_colunas)
                
                if colunas:
                    print(f"\nTabela: {tabela}")
                    print(f"   Colunas: {', '.join([c['column_name'] for c in colunas])}")
                    
                    # Tentar buscar dados relacionados ao id_favorecido
                    # Procurar por colunas que podem referenciar a empresa
                    colunas_empresa = [c['column_name'] for c in colunas if any(x in c['column_name'].lower() for x in ['empresa', 'favorecido', 'cliente', 'codigo'])]
                    
                    if colunas_empresa:
                        for col in colunas_empresa:
                            try:
                                query_dados = f"SELECT * FROM {tabela} WHERE {col} = :id LIMIT 5"
                                dados = query_external_db(query_dados, {'id': id_favorecido})
                                if dados:
                                    print(f"\n   OK Encontrado dados em {tabela}.{col}:")
                                    for row in dados:
                                        print(f"      {row}")
                            except Exception as e:
                                pass
            except Exception as e:
                pass

def buscar_por_descricao():
    """Busca tabelas que contenham a palavra 'CONTRATO' ou 'MENSAL' na descrição"""
    with app.app_context():
        print("\n=== BUSCANDO TABELAS COM 'CONTRATO' OU 'MENSAL' ===\n")
        
        # Listar todas as tabelas
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND (table_name LIKE '%contrat%' OR table_name LIKE '%mensal%' OR table_name LIKE '%financ%')
            ORDER BY table_name
        """
        tabelas = query_external_db(query)
        
        for t in tabelas:
            tabela = t['table_name']
            print(f"\nTabela: {tabela}")
            
            # Listar colunas
            query_colunas = f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{tabela}'
                ORDER BY ordinal_position
            """
            colunas = query_external_db(query_colunas)
            print(f"   Colunas: {', '.join([c['column_name'] for c in colunas])}")
            
            # Mostrar alguns registros de exemplo
            try:
                query_exemplo = f"SELECT * FROM {tabela} LIMIT 3"
                exemplos = query_external_db(query_exemplo)
                if exemplos:
                    print(f"   Exemplo de dados:")
                    for ex in exemplos:
                        print(f"      {ex}")
            except Exception as e:
                print(f"   Erro ao buscar exemplos: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("EXPLORADOR DE MENSALIDADE - BANCO OAMD")
    print("=" * 60)
    
    # 1. Explorar estrutura
    # tabelas = explorar_tabelas()
    
    # 2. Buscar por descrição
    buscar_por_descricao()
    
    # 3. Buscar mensalidade para empresa específica (ID Favorecido 11287 do exemplo)
    # buscar_mensalidade_por_empresa(11287)
    
    print("\n" + "=" * 60)
    print("EXPLORAÇÃO CONCLUÍDA")
    print("=" * 60)
