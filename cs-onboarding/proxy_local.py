import socket, threading, struct

def handle_client(connection):
    try:
        greeting = connection.recv(2)
        if not greeting or greeting[0] != 0x05: return
        connection.sendall(b"\x05\x00")
        header = connection.recv(4)
        if not header or header[1] != 0x01: return
        atyp = header[3]
        if atyp == 0x01: dest_addr = socket.inet_ntoa(connection.recv(4))
        elif atyp == 0x03: dest_addr = connection.recv(connection.recv(1)[0]).decode()
        else: return
        dest_port = struct.unpack("!H", connection.recv(2))[0]
        remote = socket.create_connection((dest_addr, dest_port), timeout=10)
        connection.sendall(struct.pack("!BBBBIH", 0x05, 0x00, 0x00, 0x01, 0, 0))
        def forward(src, dst):
            try:
                while True:
                    data = src.recv(4096)
                    if not data: break
                    dst.sendall(data)
            except: pass
            finally: src.close(); dst.close()
        threading.Thread(target=forward, args=(connection, remote)).start()
        threading.Thread(target=forward, args=(remote, connection)).start()
    except: connection.close()

def run_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 1080))
    server.listen(10)
    print("✅ Proxy SOCKS5 ONLINE na porta 1080")
    print("Mantenha esta janela aberta para o site funcionar!")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn,)).start()

if __name__ == "__main__":
    run_proxy()