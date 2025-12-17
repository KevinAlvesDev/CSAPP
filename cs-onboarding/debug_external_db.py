import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
load_dotenv('.env.local', override=True)

import socket
import sys

def check_tcp_port(host, port, timeout=5):
    """Testa se a porta TCP está aberta (indica se é firewall ou aplicação)."""
    print(f"\n📡 Testando conectividade TCP com {host}:{port} (Timeout: {timeout}s)...")
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        print("✅ Porta TCP 5432 está ABERTA e acessível!")
        return True
    except socket.timeout:
        print("❌ TIMEOUT TCP: O firewall do servidor está descartando pacotes.")
        print("   -> O IP desta máquina NÃO está na allowlist do servidor de banco.")
        return False
    except socket.error as e:
        print(f"❌ ERRO TCP: {e}")
        return False

def test_connection():
    db_url = os.environ.get('EXTERNAL_DB_URL') or os.environ.get('DB_EXT_URL')
    
    if not db_url:
        print("❌ ERRO: Nenhuma URL de banco externo encontrada (EXTERNAL_DB_URL ou DB_EXT_URL).")
        return

    # Parse da URL para pegar host e porta
    try:
        parsed = urlparse(db_url)
        host = parsed.hostname
        port = parsed.port or 5432
    except Exception:
        print("❌ Erro ao fazer parse da URL do banco.")
        return

    print(f"🔍 URL Configurada (mascarada): {db_url.split('@')[-1]}")
    
    # 1. Teste de TCP/Firewall
    if not check_tcp_port(host, port):
        print("\n⚠️  DIAGNÓSTICO: BLOQUEIO DE REDE DETECTADO")
        print("   A aplicação não consegue nem estabelecer conexão de rede com o banco.")
        print("   SOLUÇÃO: Libere o IP desta máquina no Security Group/Firewall da AWS do banco OAMD.")
        return

    # 2. Teste de Conexão Postgres
    print(f"\n🕵️  Tentando descobrir o nome correto do banco conectando em 'postgres'...")
    
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
