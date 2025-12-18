import socket, threading, struct, sys

def handle_client(connection, addr):
    try:
        # 1. Greeting
        data = connection.recv(262)
        if not data: return
        connection.sendall(b"\x05\x00")
        
        # 2. Connection Request
        data = connection.recv(4)
        if not data: return
        atyp = data[3]
        if atyp == 0x01: dest_addr = socket.inet_ntoa(connection.recv(4))
        elif atyp == 0x03: dest_addr = connection.recv(connection.recv(1)[0]).decode()
        else: return
        dest_port = struct.unpack("!H", connection.recv(2))[0]
        
        print(f"🚢 Conectando ao Banco OAMD via PC: {dest_addr}:{dest_port}")
        
        # 3. Establish Connection
        remote = socket.create_connection((dest_addr, dest_port), timeout=15)
        connection.sendall(struct.pack("!BBBBIH", 0x05, 0x00, 0x00, 0x01, 0, 0))
        
        def pipe(src, dst):
            try:
                while True:
                    d = src.recv(8192)
                    if not d: break
                    dst.sendall(d)
            except: pass
            finally: 
                try: src.close()
                except: pass
                try: dst.close()
                except: pass

        threading.Thread(target=pipe, args=(connection, remote), daemon=True).start()
        threading.Thread(target=pipe, args=(remote, connection), daemon=True).start()
        
    except Exception as e:
        print(f"❌ Falha no túnel: {e}")
        try: connection.close()
        except: pass

def run_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("0.0.0.0", 1080))
        server.listen(50)
        print("✅ PROXY SOCKS5 ROBUSTO ONLINE na porta 1080")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except Exception as e:
        print(f"CRÍTICO: Não conseguiu abrir a porta 1080: {e}")

if __name__ == "__main__":
    run_proxy()