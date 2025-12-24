"""
Script para testar conectividade do proxy SOCKS5 remotamente.
Simula o que a aplicação em produção está tentando fazer.
"""
import socket
import socks
import sys

def test_socks_proxy(proxy_host, proxy_port, target_host, target_port):
    """Testa se consegue conectar através do proxy SOCKS5."""
    print(f"[*] Testando proxy SOCKS5: {proxy_host}:{proxy_port}")
    print(f"[*] Alvo: {target_host}:{target_port}")
    print("-" * 60)
    
    try:
        # Configurar socket SOCKS5
        sock = socks.socksocket()
        sock.set_proxy(socks.SOCKS5, proxy_host, proxy_port)
        sock.settimeout(10)
        
        print(f"[*] Tentando conectar através do proxy...")
        sock.connect((target_host, target_port))
        
        print(f"[OK] SUCESSO! Conectado a {target_host}:{target_port} através do proxy")
        sock.close()
        return True
        
    except socks.ProxyConnectionError as e:
        print(f"[ERRO] Não conseguiu conectar ao proxy SOCKS5")
        print(f"   Detalhes: {e}")
        print(f"\n[INFO] Possíveis causas:")
        print(f"   - Firewall bloqueando a porta {proxy_port}")
        print(f"   - Roteador não está fazendo port forwarding")
        print(f"   - Túnel SSH não está rodando")
        return False
        
    except socket.timeout:
        print(f"[ERRO] Timeout ao conectar")
        print(f"\n[INFO] Possíveis causas:")
        print(f"   - Proxy não está acessível externamente")
        print(f"   - Firewall bloqueando conexões")
        return False
        
    except Exception as e:
        print(f"[ERRO] {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    # Configurações
    PROXY_HOST = "pacto-css.ddns.net"
    PROXY_PORT = 50022
    TARGET_HOST = "oamd.pactosolucoes.com.br"
    TARGET_PORT = 5432
    
    print("=" * 60)
    print("  TESTE DE CONECTIVIDADE DO PROXY SOCKS5")
    print("=" * 60)
    print()
    
    # Teste 1: Conectar ao proxy localmente
    print("[TESTE 1] Proxy Local (localhost)")
    test_socks_proxy("localhost", PROXY_PORT, TARGET_HOST, TARGET_PORT)
    print()
    
    # Teste 2: Conectar ao proxy remotamente (via DDNS)
    print("[TESTE 2] Proxy Remoto (DDNS)")
    success = test_socks_proxy(PROXY_HOST, PROXY_PORT, TARGET_HOST, TARGET_PORT)
    print()
    
    if success:
        print("[OK] Proxy está funcionando corretamente!")
        sys.exit(0)
    else:
        print("[AVISO] Proxy não está acessível externamente")
        print("\n[PROXIMOS PASSOS]:")
        print("   1. Verificar port forwarding no roteador (porta 50022)")
        print("   2. Verificar se o IP público está correto")
        print("   3. Testar com: telnet pacto-css.ddns.net 50022")
        sys.exit(1)

