import socket
import threading
import select
import time

BUFFER_SIZE = 4096
HTTP_VERSION = "HTTP/1.0"

class HTTPProxy:
    def __init__(self, host='127.0.0.1', port=1234):
        self.host = host
        if port < 1024 or port > 65535: # invlaid port number
            return
        self.port = port
        self.server_socket = None

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.server_socket.settimeout(10)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        # debug
        # print(f"proxy server started on {self.host}:{self.port}")
        while True:
            client_socket, client_address = self.server_socket.accept()
            # debug
            # print(f"new connection from {client_address}")
            
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def log_request(self, method, uri):
        current_time = time.strftime("%d %b %H:%M:%S", time.localtime())
        print(f"{current_time} - >>> {method} {uri}")

    def handle_client(self, client_socket):
        client_socket.settimeout(10)
        try:
            request = client_socket.recv(BUFFER_SIZE)
            try:
                request_decoded = request.decode('utf-8')
            except UnicodeDecodeError:
                request_decoded = request.decode('iso-8859-1')
            first_line = request_decoded.split('\r\n')[0]
            
            # debug
            # print(f"Received request: {request_decoded}")
            parts = first_line.split(' ', 2)
            if len(parts) < 3:
                client_socket.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                return
            method, uri, _ = parts
            # current_time = time.strftime("%d %b %H:%M:%S", time.localtime())
            # print(f"{current_time} - >>> {method} {uri}")
            self.log_request(method, uri)
            
            if first_line.startswith("CONNECT"):
                self.handle_connect_request(client_socket, request_decoded)
            else:
                self.handle_non_connect_request(client_socket, request_decoded)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()
            
    def handle_connect_request(self, client_socket, request):
        target_host, target_port = self.parse_port(request)
        try:
            self.log_request("CONNECT", f"{target_host}:{target_port}")

            target_socket = socket.create_connection((target_host, target_port))
            client_socket.sendall(b"HTTP/1.0 200 Connection Established\r\n\r\n")
            self.forward_data(client_socket, target_socket)
        except Exception as e:
            client_socket.sendall(b"HTTP/1.0 502 Bad Gateway\r\n\r\n")
            
    def forward_data(self, client_socket, target_socket):
        sockets = [client_socket, target_socket]
        while True:
            (readable,_ , _) = select.select(sockets, [], [])
            for sock in readable:
                try:
                    data = sock.recv(BUFFER_SIZE)
                    if not data:
                        return
                    if sock is client_socket:
                        target_socket.sendall(data)
                    else:
                        client_socket.sendall(data)
                except Exception as e:
                    sock.close()
                    return


    def handle_non_connect_request(self, client_socket, request):
        try:
            # parse host and port from headers      
            host, port = self.parse_port(request)
            if not host or not port:
                print("Failed to extract host or port from request.")
                client_socket.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                return
            
            parts = request.split(' ', 2)
            if len(parts) < 3:
                client_socket.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                return
            method, uri, _ = parts
            self.log_request(method, uri)

            # connect to origin server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                # debug
                # print(f"connecting to origin server at {host}:{port}")
                
                server_socket.connect((host, port))     # accepts tuple as argument

                # modify HTTP headers
                modified_request = request.replace("HTTP/1.1", "HTTP/1.0")
                modified_request = modified_request.replace("Connection: keep-alive", "Connection: close")

                # send modified request to server
                server_socket.sendall(modified_request.encode('utf-8', errors='replace'))

                # relay response back to client
                while True:
                    data = server_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    client_socket.sendall(data)

        except Exception as e:
            print(f"error handling non-connect request: {e}")

    def parse_port(self, request):
        """Extract the correct port number"""
        host, port = None, None
        try:
            headers = request.split("\r\n")
            request_line = headers[0]
            # insensitive to the case
            host_line = next((header for header in headers if header.lower().startswith("host:")), None)
            if host_line is None:
                return None # maybe raise an error
            host = host_line.split(":", 1)[1].strip()

            if ":" in host: # port number is at the host line
                host, port = host.split(":", 1)
                port = int(port)
            
            if not port: # check if port number is at the first line
                _, uri, _ = request_line.split(" ", 2)
                proto, host_val = None, None
                if "://" in uri:
                    proto, rest = uri.split("://", 1)
                    host_val = rest.split("/", 1)[0]
                else:
                    host_val = uri.split("/", 1)[0]
                if ":" in host_val:
                    port = host_val.split(":", 1)[1].strip()
                    port = int(port)
            
            if not port: # no port number in the header
                if not proto or proto.lower() == "http":
                    port = 80
                else: port = 443

            return host, port
        
        except Exception as e:
            print(f"Error extracting host and port: {e}")
            return None, None

        
if __name__ == "__main__":
    proxy = HTTPProxy()
    proxy.start()