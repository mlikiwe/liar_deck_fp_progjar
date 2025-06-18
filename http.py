import json
from datetime import datetime
from game_logic import LiarDeckGame
import os

# Inisialisasi satu instance game untuk keseluruhan server
game = LiarDeckGame()

class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        self.types['.js'] = 'application/javascript'
        self.types['.css'] = 'text/css'

    def response(self, kode=404, message='Not Found', messagebody='', headers={}):
        # Fungsi response ini hampir sama, tapi pastikan messagebody di-encode jika string
        if isinstance(messagebody, dict) or isinstance(messagebody, list):
             messagebody = json.dumps(messagebody)

        if not isinstance(messagebody, bytes):
            messagebody = messagebody.encode()

        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'

        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append(f"HTTP/1.1 {kode} {message}\r\n")
        resp.append(f"Date: {tanggal}\r\n")
        resp.append("Connection: close\r\n")
        resp.append("Server: MyLiarDeckServer/1.0\r\n")
        resp.append(f"Content-Length: {len(messagebody)}\r\n")
        for kk, vv in headers.items():
            resp.append(f"{kk}: {vv}\r\n")
        resp.append("\r\n")

        response_headers = "".join(resp)
        return response_headers.encode() + messagebody

    def proses(self, data):
        requests = data.split("\r\n")
        baris = requests[0]
        
        # Ekstrak body jika ada (untuk POST)
        body_start_index = data.find('\r\n\r\n') + 4
        body = data[body_start_index:]
        
        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            object_address = j[1].strip()

            if method == 'GET':
                # Pisahkan path dan query params
                parts = object_address.split('?')
                path = parts[0]
                params = {}
                if len(parts) > 1:
                    query_string = parts[1]
                    params = dict(p.split('=') for p in query_string.split('&'))

                return self.http_get(path, params)

            elif method == 'POST':
                return self.http_post(object_address, body)
            else:
                return self.response(400, 'Bad Request', {"error": "Method not supported"})

        except IndexError:
            return self.response(400, 'Bad Request', {"error": "Malformed request line"})

    def http_get(self, path, params):
        if path == '/game/state':
            player_id = params.get('player_id', 'player1') # default ke player1 jika tidak dispesifikasi
            state = game.get_game_state(player_id)
            return self.response(200, 'OK', state)
        else:
            # Serve file statis (HTML/CSS/JS) untuk antarmuka
            try:
                # Amankan path agar tidak bisa akses file di luar direktori
                if path == '/':
                    path = '/index.html'
                
                filepath = 'www' + path
                with open(filepath, 'rb') as f:
                    content = f.read()
                
                # Tentukan content type
                file_ext = os.path.splitext(filepath)[1]
                content_type = self.types.get(file_ext, 'application/octet-stream')
                
                return self.response(200, 'OK', content, {'Content-Type': content_type})
            except FileNotFoundError:
                return self.response(404, 'Not Found', {"error": "File not found"})

    def http_post(self, object_address, body):
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self.response(400, 'Bad Request', {"error": "Invalid JSON body"})

        # ================== PERUBAHAN KUNCI ==================
        # Tambahkan blok try...except di sekitar semua logika game
        try:
            if object_address == '/game/start':
                # Inisialisasi self.players di dalam start_game jika belum ada
                if not hasattr(game, 'players') or not game.players:
                    game.players = {}
                game.start_game()
                return self.response(200, 'OK', {"message": "Game started successfully."})
            
            elif object_address == '/game/play':
                player_id = payload.get("player_id")
                cards = payload.get("cards")
                result = game.play_card(player_id, cards)
                return self.response(200, 'OK', result)
                
            elif object_address == '/game/challenge':
                player_id = payload.get("player_id")
                result = game.challenge(player_id)
                return self.response(200, 'OK', result)

            else:
                return self.response(404, 'Not Found', {"error": "Endpoint not found"})
        
        except Exception as e:
            # Jika ada error APAPUN di dalam logika game, kirim error tersebut ke client
            # agar kita bisa melihatnya di console browser.
            import traceback
            error_details = traceback.format_exc()
            # Cetak error di terminal server agar kita tahu
            print(f"\n--- SERVER ERROR ---\n{error_details}\n---------------------\n")
            return self.response(500, 'Internal Server Error', {"error": str(e), "details": error_details})
        # =======================================================