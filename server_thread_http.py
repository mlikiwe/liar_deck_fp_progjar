from socket import *
import socket
import threading
import time
import sys
import logging
from http import HttpServer

httpserver = HttpServer()

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        # ================== AWAL DARI KODE YANG DIPERBAIKI ==================
        # Logika baru yang lebih andal untuk membaca request HTTP dengan body
        try:
            # 1. Baca semua headers sampai menemukan baris kosong (\r\n\r\n)
            all_headers = b""
            while True:
                data = self.connection.recv(1024)
                if not data:
                    break
                all_headers += data
                if b"\r\n\r\n" in all_headers:
                    # Pisahkan header dan bagian awal dari body jika ada
                    header_part, body_part = all_headers.split(b"\r\n\r\n", 1)
                    break
            
            # 2. Cari Content-Length dari header
            headers_str = header_part.decode('utf-8')
            content_length = 0
            for line in headers_str.split('\r\n'):
                if line.lower().startswith('content-length:'):
                    content_length = int(line.split(':')[1].strip())
                    break
            
            # 3. Baca sisa body sesuai Content-Length
            while len(body_part) < content_length:
                data = self.connection.recv(1024)
                if not data:
                    break
                body_part += data

            # 4. Gabungkan kembali menjadi request utuh untuk diproses
            full_request_str = headers_str + "\r\n\r\n" + body_part.decode('utf-8')
            
            logging.warning(f"data dari client: {full_request_str}")
            
            # Proses request
            hasil = httpserver.proses(full_request_str)
            
            # Kirim balasan
            # Tidak perlu menambahkan "\\r\\n\\r\\n" lagi karena sudah ada di dalam 'hasil'
            logging.warning(f"balas ke client: {hasil}")
            self.connection.sendall(hasil)

        except Exception as e:
            logging.error(f"Error processing client: {e}")
        finally:
            self.connection.close()
        # =================== AKHIR DARI KODE YANG DIPERBAIKI ===================

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
    def __init__(self, ip='0.0.0.0', port=55555, worker_ports=[56000, 56001]):
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
            # Tutup socket dengan aman
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
    worker1 = Server(ipaddr='127.0.0.1', port=56000)
    worker2 = Server(ipaddr='127.0.0.1', port=56001)
    worker1.start()
    worker2.start()

    lb = LBServer(worker_ports=[56000, 56001])
    lb.start()

    worker1.join()
    worker2.join()
    lb.join()

if __name__ == "__main__":
    main()