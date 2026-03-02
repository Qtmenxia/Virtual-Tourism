import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('0.0.0.0', 5566))
server.listen(5)

while True:
    client_socket, client_address = server.accept()
    print(f"Connection from {client_address}")
    data = client_socket.recv(1024)
    print(f"Received data: {data.decode('utf-8')}")
    client_socket.close()
