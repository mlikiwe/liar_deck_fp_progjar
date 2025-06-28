from socket import *
import socket
import threading
import logging
from http import HttpServer

httpserver = HttpServer()

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        try:
            all_headers = b""
            while True:
                data = self.connection.recv(1024)
                if not data:
                    break
                all_headers += data
                if b"\r\n\r\n" in all_headers:
                    header_part, body_part = all_headers.split(b"\r\n\r\n", 1)
                    break
            
            headers_str = header_part.decode('utf-8')
            content_length = 0
            for line in headers_str.split('\r\n'):
                if line.lower().startswith('content-length:'):
                    content_length = int(line.split(':')[1].strip())
                    break
            
            while len(body_part) < content_length:
                data = self.connection.recv(1024)
                if not data:
                    break
                body_part += data

            full_request_str = headers_str + "\r\n\r\n" + body_part.decode('utf-8')
            
            # logging.warning(f"data dari client: {full_request_str}")
            
            hasil = httpserver.proses(full_request_str)
            
            # logging.warning(f"balas ke client: {hasil}")
            self.connection.sendall(hasil)

        except Exception as e:
            logging.error(f"Error processing client: {e}")
        finally:
            self.connection.close()

class Server(threading.Thread):
    def __init__(self):
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        threading.Thread.__init__(self)

    def run(self):
        self.my_socket.bind(('0.0.0.0', 8889))
        self.my_socket.listen(1)
        logging.warning("Server running on port 8889")
        while True:
            self.connection, self.client_address = self.my_socket.accept()
            logging.warning(f"connection from {self.client_address}")
            
            clt = ProcessTheClient(self.connection, self.client_address)
            clt.start()
            self.the_clients.append(clt)

def main():
    svr = Server()
    svr.start()

if __name__ == "__main__":
    main()