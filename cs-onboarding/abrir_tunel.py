"""
Túnel SSH para acesso ao banco de dados OAMD
Mantém conexão ativa para consultas ao banco externo
"""
import subprocess
import sys
import time
from pathlib import Path

# Configurações do túnel SSH
SSH_USER = "pacto"
SSH_HOST = "pactosolucoes.com.br"
SSH_PORT = 22
LOCAL_PORT = 5433  # Porta local onde o PostgreSQL será acessível
REMOTE_HOST = "localhost"  # Host do banco no servidor remoto
REMOTE_PORT = 5432  # Porta do PostgreSQL no servidor remoto

# Caminho para a chave SSH (ajuste conforme necessário)
SSH_KEY_PATH = Path.home() / ".ssh" / "id_rsa"

def abrir_tunel():
    """
    Abre túnel SSH para o banco de dados OAMD
    Mantém conexão ativa até ser interrompida
    """
    print("=" * 60)
    print("🔐 TÚNEL SSH - BANCO OAMD")
    print("=" * 60)
    print(f"\n📡 Conectando ao servidor: {SSH_USER}@{SSH_HOST}")
    print(f"🔌 Porta local: {LOCAL_PORT}")
    print(f"🎯 Destino: {REMOTE_HOST}:{REMOTE_PORT}")
    print("\n⚠️  Mantenha esta janela aberta enquanto usar o banco!")
    print("⏹️  Pressione Ctrl+C para encerrar o túnel\n")
    print("=" * 60)
    
    # Comando SSH para criar o túnel
    cmd = [
        "ssh",
        "-N",  # Não executar comando remoto
        "-L", f"{LOCAL_PORT}:{REMOTE_HOST}:{REMOTE_PORT}",  # Port forwarding
        f"{SSH_USER}@{SSH_HOST}",
        "-p", str(SSH_PORT)
    ]
    
    # Adicionar chave SSH se existir
    if SSH_KEY_PATH.exists():
        cmd.insert(1, "-i")
        cmd.insert(2, str(SSH_KEY_PATH))
    
    try:
        print(f"\n🚀 Iniciando túnel...\n")
        
        # Executar comando SSH
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Aguardar alguns segundos para estabelecer conexão
        time.sleep(2)
        
        # Verificar se o processo ainda está rodando
        if process.poll() is None:
            print("✅ Túnel SSH estabelecido com sucesso!")
            print(f"\n📊 Você pode conectar ao banco usando:")
            print(f"   Host: localhost")
            print(f"   Port: {LOCAL_PORT}")
            print(f"   Database: oamd")
            print(f"   User: pacto")
            print("\n⏳ Aguardando... (Ctrl+C para sair)\n")
            
            # Manter processo rodando
            process.wait()
        else:
            stderr = process.stderr.read().decode('utf-8', errors='ignore')
            print(f"❌ Erro ao estabelecer túnel:")
            print(stderr)
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Encerrando túnel SSH...")
        if process:
            process.terminate()
            process.wait()
        print("✅ Túnel encerrado com sucesso!")
        return 0
        
    except FileNotFoundError:
        print("❌ ERRO: Comando 'ssh' não encontrado!")
        print("\n💡 Soluções:")
        print("   1. Instale o OpenSSH Client no Windows")
        print("   2. Ou use PuTTY para criar o túnel manualmente")
        return 1
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(abrir_tunel())
