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

            hasil = httpserver.proses(full_request_str)

            self.connection.sendall(hasil)

        except Exception as e:
            logging.error(f"Error processing client: {e}")
        finally:
            self.connection.close()


class Server(threading.Thread):
    def __init__(self, ipaddr='0.0.0.0', port=8889):
        self.ipinfo = (ipaddr, port)
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        threading.Thread.__init__(self)

    def run(self):
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(1)
        logging.warning(f"Server running on port {self.ipinfo[1]}")
        while True:
            self.connection, self.client_address = self.my_socket.accept()
            logging.warning(f"connection from {self.client_address}")

            clt = ProcessTheClient(self.connection, self.client_address)
            clt.start()
            self.the_clients.append(clt)


class LBServer(threading.Thread):
    def __init__(self, ip='0.0.0.0', port=8181, worker_ports=[56000, 56001, 56002, 56003]):
        self.ip = ip
        self.port = port
        self.worker_ports = worker_ports
        self.current = 0
        threading.Thread.__init__(self)

    def run(self):
        logging.warning(f"Load Balancer running on {self.ip}:{self.port}")
        lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lb_socket.bind((self.ip, self.port))
        lb_socket.listen(5)
        while True:
            conn, addr = lb_socket.accept()
            logging.warning(f"Load Balancer connection from {addr}")
            worker_port = self.worker_ports[self.current]
            self.current = (self.current + 1) % len(self.worker_ports)
            logging.warning(f"Forwarding to worker on port {worker_port}")

            # Handle dalam thread terpisah untuk mencegah blocking
            threading.Thread(target=self.forward_request, args=(conn, worker_port)).start()

    def forward_request(self, conn, worker_port):
        worker_sock = None
        try:
            worker_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            worker_sock.connect(('localhost', worker_port))

            # Gunakan shared state untuk koordinasi thread
            connection_active = {'active': True}

            t1 = threading.Thread(target=self.pipe, args=(conn, worker_sock, connection_active))
            t2 = threading.Thread(target=self.pipe, args=(worker_sock, conn, connection_active))

            t1.start()
            t2.start()

            t1.join()
            t2.join()

        except Exception as e:
            logging.error(f"Forward error: {e}")
        finally:
            try:
                if worker_sock:
                    worker_sock.close()
            except:
                pass
            try:
                conn.close()
            except:
                pass

    def pipe(self, source, destination, connection_active):
        try:
            while connection_active['active']:
                data = source.recv(1024)
                if not data:
                    break
                destination.sendall(data)
        except Exception as e:
            logging.error(f"Pipe error: {e}")
        finally:
            # Tandai koneksi tidak aktif
            connection_active['active'] = False


def main():
    servers = []
    try:
        # Start worker servers
        for port in [56000, 56001, 56002, 56003]:
            worker = Server(ipaddr='127.0.0.1', port=port)
            worker.start()
            servers.append(worker)
            logging.warning(f"Worker started on port {port}")

        # Start load balancer
        lb = LBServer(worker_ports=[56000, 56001, 56002, 56003])
        lb.start()
        servers.append(lb)
        logging.warning("Load balancer started")

        while True:
            for server in servers:
                if not server.is_alive():
                    logging.warning(f"Server thread died, exiting")
                    return
            threading.Event().wait(1)

    except KeyboardInterrupt:
        logging.warning("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logging.error(f"Error in main: {e}")
    finally:
        logging.warning("Waiting for all threads to complete...")
        for server in servers:
            if server.is_alive():
                server.join(1)  # Give each thread 1 second to join
        logging.warning("Server shutdown complete")
    exit(0)


if __name__ == "__main__":
    main()
