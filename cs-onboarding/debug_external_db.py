import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
load_dotenv('.env.local', override=True)

def test_connection():
    db_url = os.environ.get('EXTERNAL_DB_URL') or os.environ.get('DB_EXT_URL')
    
    if not db_url:
        print("❌ ERRO: Nenhuma URL de banco externo encontrada (EXTERNAL_DB_URL ou DB_EXT_URL).")
        return

    print(f"🔍 Testando conexão com: {db_url.split('@')[-1]}")  # Esconde senha
    
    # Tentar conectar ao banco 'postgres' (padrão do sistema) para listar os outros
    base_url = db_url.rsplit('/', 1)[0] + '/postgres'
    
    print(f"🕵️  Tentando descobrir o nome correto do banco conectando em 'postgres'...")
    
    try:
        # Tenta conectar no banco default 'postgres'
        conn = psycopg2.connect(base_url, connect_timeout=10, sslmode='prefer')
        print("✅ Conectado ao banco 'postgres'! Listando bancos disponíveis...")
        
        cur = conn.cursor()
        # Query para listar bancos de dados
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        dbs = cur.fetchall()
        
        print("\n📂 Bancos de Dados Encontrados:")
        found_match = False
        for db in dbs:
            name = db[0]
            print(f"   - {name}")
            if 'cs' in name or 'pacto' in name:
                print(f"     ✨ PROVÁVEL CANDIDATO: {name}")
                found_match = True
        
        cur.close()
        conn.close()
        
        if not found_match:
            print("\n⚠️ Nenhum banco com 'cs' ou 'pacto' no nome foi encontrado.")
            
    except Exception as e:
        print(f"❌ Falha ao listar bancos: {e}")
        print("   Tentando novamente com configuração de SSL legado...")

if __name__ == "__main__":
    # Configurar OpenSSL para aceitar chaves legadas (DH key too small)
    os.environ['OPENSSL_CONF'] = os.path.abspath('legacy_openssl.cnf')
    test_connection()
