"""Script para verificar a estrutura do banco de dados e dados das implantações."""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Carrega variáveis de ambiente
load_dotenv()

def get_db_connection():
    """Cria conexão com o banco de dados."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def check_implantacoes_structure():
    """Verifica a estrutura da tabela implantacoes."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verifica colunas da tabela
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'implantacoes'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            
            print("=" * 80)
            print("ESTRUTURA DA TABELA IMPLANTACOES")
            print("=" * 80)
            for col in columns:
                print(f"Coluna: {col['column_name']}")
                print(f"  Tipo: {col['data_type']}")
                print(f"  Nullable: {col['is_nullable']}")
                print(f"  Default: {col['column_default']}")
                print()
            
            # Verifica dados das implantações
            cursor.execute("""
                SELECT id, nome_empresa, status, tipo, valor_atribuido, 
                       data_criacao, usuario_cs
                FROM implantacoes
                ORDER BY id DESC
                LIMIT 10;
            """)
            implantacoes = cursor.fetchall()
            
            print("=" * 80)
            print("ÚLTIMAS 10 IMPLANTAÇÕES")
            print("=" * 80)
            for impl in implantacoes:
                print(f"ID: {impl['id']}")
                print(f"  Empresa: {impl['nome_empresa']}")
                print(f"  Status: {impl['status']}")
                print(f"  Tipo: {impl['tipo']}")
                print(f"  Valor: {impl['valor_atribuido']}")
                print(f"  Data Criação: {impl['data_criacao']}")
                print(f"  CS: {impl['usuario_cs']}")
                print()
            
            # Conta implantações por status
            cursor.execute("""
                SELECT status, COUNT(*) as total
                FROM implantacoes
                GROUP BY status
                ORDER BY total DESC;
            """)
            status_counts = cursor.fetchall()
            
            print("=" * 80)
            print("CONTAGEM POR STATUS")
            print("=" * 80)
            for status in status_counts:
                print(f"{status['status']}: {status['total']}")
            print()
            
            # Verifica se há implantações canceladas
            cursor.execute("""
                SELECT id, nome_empresa, status, tipo
                FROM implantacoes
                WHERE status = 'cancelada'
                LIMIT 5;
            """)
            canceladas = cursor.fetchall()
            
            print("=" * 80)
            print("IMPLANTAÇÕES CANCELADAS (até 5)")
            print("=" * 80)
            if canceladas:
                for impl in canceladas:
                    print(f"ID: {impl['id']} - {impl['nome_empresa']} - Status: {impl['status']} - Tipo: {impl['tipo']}")
            else:
                print("Nenhuma implantação cancelada encontrada!")
            print()
            
    finally:
        conn.close()

if __name__ == '__main__':
    try:
        check_implantacoes_structure()
    except Exception as e:
        print(f"Erro ao verificar banco de dados: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
