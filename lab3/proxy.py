import socket
import threading
import select

BUFFER_SIZE = 4096
HTTP_VERSION = "HTTP/1.0"

class HTTPProxy:
    def __init__(self, host='0.0.0.0', port=1234):
        self.host = host
        self.port = port
        self.server_socket = None

    def start(self):
        client_socket, client_address = self.server_socket.accept()
        threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        try:
            request = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            first_line = request.split('\r\n')[0]
            print(f"Received request: {first_line}")
            if first_line.startswith("CONNECT"):
                self.handle_connect_request(client_socket, request)
            else:
                self.handle_non_connect_request(client_socket, request)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()
            
    def handle_connect_request(self, client_socket, request):


    def handle_non_connect_request(self, client_socket, request):
        try:
            # parse host and port from headers
            lines = request.split('\r\n')
            host_line = [line for line in lines if line.lower().startswith("host:")][0]
            host = host_line.split(":")[1].strip()
            port = 80   # default HTTP port

            # connect to origin server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.connect((host, port))     # accepts tuple as argument

                # modify HTTP headers
                modified_request = request.replace("HTTP/1.1", "HTTP/1.0")
                modified_request = modified_request.replace("Connection: keep-alive", "Connection: close")

                # send modified request to server
                server_socket.sendall(modified_request.encode('utf-8'))

                # relay response back to client
                while True:
                    data = server_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    client_socket.sendall(data)

        except Exception as e:
            print(f"error handling non-connect request: {e}")

    