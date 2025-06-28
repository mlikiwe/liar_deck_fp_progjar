import random

class LiarDeckGame:
    def __init__(self):
        self.players = {}  # E.g., { "player1": {"hand": [], "is_eliminated": False}, ... }
        self.game_started = False
        self.card_pile = []
        self.current_turn_index = 0
        self.player_order = []
        self.reference_card = None
        self.last_play = {"player_id": None, "cards": []}
        self.game_winner = None
        self.log = ["Game has not started."]

    def start_game(self, player_ids=["player1", "player2", "player3", "player4"]):
        # --- PERUBAHAN: Reset semua variabel state untuk game baru yang bersih ---
        self.players = {}
        self.card_pile = []
        self.current_turn_index = 0
        self.player_order = []
        self.reference_card = None
        self.last_play = {"player_id": None, "cards": []}
        self.game_winner = None
        self.log = ["Game has not started."]
        # --- Akhir dari blok reset ---
        
        deck = self.shuffle_deck()
        
        # 2. Inisialisasi pemain dan bagi kartu
        self.player_order = [pid.strip() for pid in player_ids]
        
        for i, player_id in enumerate(self.player_order):
            self.players[player_id] = {
                "hand": deck[i*6 : (i+1)*6],
                "roulette_index":0,
                "roulette": random.randint(0, 2),  # Indeks acak untuk roulette
                "is_eliminated": False
            }
        
        self.game_started = True
        self.current_turn_index = 0
        self.log = [f"Game started. Reference card is {self.reference_card}."]
        self.log.append(f"It's {self.player_order[self.current_turn_index]}'s turn.")
        
    def generate_new_deck(self):
        # untuk setiap pemain yang ada hand buat baru
        deck = self.shuffle_deck()
        for i, player_id in self.players:
            if self.players[player_id]["is_eliminated"]:
                continue
            self.players[player_id]["hand"] = deck[i*6 : (i+1)*6]
            
        
    def shuffle_deck(self):
        # Mengacak dek kartu
        ranks = ["Ace", "Jack", "Queen", "King"]
        deck = [rank for rank in ranks for _ in range(6)]
        random.shuffle(deck)
        self.reference_card = random.choice(ranks)  # Pilih kartu acuan awal
        return deck

    def get_game_state(self, player_id):
        # Mengembalikan state yang relevan untuk satu pemain
        if not self.game_started:
            return {"game_started": False}
            
        state = {
            "game_started": True,
            "your_hand": self.players.get(player_id, {}).get("hand", []),
            "all_players_card_count": {pid: len(p["hand"]) for pid, p in self.players.items()},
            "players_eliminated": [pid for pid, p in self.players.items() if p["is_eliminated"]],
            "card_pile_count": len(self.card_pile),
            "current_turn": self.player_order[self.current_turn_index],
            "reference_card": self.reference_card,
            "game_winner": self.game_winner,
            "log": self.log[-5:] # 5 log terakhir
        }
        return state
        
    # --- PERUBAHAN: Modifikasi fungsi next_turn untuk menerima argumen ---
    def next_turn(self, set_turn_to_player=None):
        # Pindah ke pemain berikutnya yang belum tereliminasi
        active_players = [p for p in self.player_order if not self.players[p]["is_eliminated"]]
        if not active_players or len(active_players) == 1:
            self.game_winner = active_players[0] if active_players else "No one"
            self.log.append(f"Game over! Winner is {self.game_winner}")
            return

        if set_turn_to_player:
            # Jika ada pemenang challenge, set giliran ke dia
            self.current_turn_index = self.player_order.index(set_turn_to_player)
            self.generate_new_deck()  # Generate deck baru untuk pemain yang menang challenge
        else:
            # Jika tidak, lanjutkan ke pemain berikutnya dalam urutan
            self.current_turn_index = (self.current_turn_index + 1) % len(self.player_order)
            while self.players[self.player_order[self.current_turn_index]]["is_eliminated"]:
                self.current_turn_index = (self.current_turn_index + 1) % len(self.player_order)
        
        self.log.append(f"It's {self.player_order[self.current_turn_index]}'s turn.")

    def play_card(self, player_id, cards_played):
        # Logika untuk pemain memainkan kartu
        # (Validasi giliran, hapus kartu dari tangan, dll.)
        if self.player_order[self.current_turn_index] != player_id:
            return {"status": "ERROR", "message": "Not your turn."}
            
        # Hapus kartu dari tangan pemain
        for card in cards_played:
            if card in self.players[player_id]["hand"]:
                self.players[player_id]["hand"].remove(card)
            else:
                # Seharusnya tidak terjadi jika client jujur, tapi baik untuk validasi
                return {"status": "ERROR", "message": f"You don't have a {card}."}

        self.card_pile.extend(cards_played)
        self.last_play = {"player_id": player_id, "cards": cards_played}
        self.log.append(f"{player_id} played {len(cards_played)} card(s).")
        self.next_turn() # Panggilan ini tidak berubah, akan memajukan giliran secara normal
        return {"status": "OK"}
    
    def kill_player(self, player_id):
        if player_id not in self.players or self.players[player_id]["is_eliminated"]:
            return {"status": "ERROR", "message": "Player not found or already eliminated."}
        
        self.players[player_id]["is_eliminated"] = True
        self.log.append(f"{player_id} has been eliminated.")
        
        # Cek apakah game berakhir
        active_players = [p for p in self.player_order if not self.players[p]["is_eliminated"]]
        if len(active_players) == 1:
            self.game_winner = active_players[0]
            self.log.append(f"Game over! Winner is {self.game_winner}")
        
        # Pindah ke pemain berikutnya
        self.next_turn()
        return {"status": "OK", "eliminated_player": player_id}
    
    def proceed_roulette(self, player_id):
        if self.player_order[self.current_turn_index] != player_id:
            return {"status": "ERROR", "message": "Not your turn."}
        
        roulette_index = self.players[player_id]["roulette_index"]
        bullet_position = self.players[player_id]["roulette"]
        
        if roulette_index == bullet_position:
           self.kill_player(player_id)
           self.log.append(f"{player_id} has been shot by the roulette!")
        else:
            # Pemain aman, lanjutkan ke giliran berikutnya
            self.players[player_id]["roulette_index"] += 1
            if self.players[player_id]["roulette_index"] >= 3:
                self.players[player_id]["roulette_index"] = 0       

    def challenge(self, challenger_id):
        # Logika untuk tantangan
        player_who_played = self.last_play["player_id"]
        cards_in_play = self.last_play["cards"]
        
        is_a_lie = False
        for card in cards_in_play:
            if card != self.reference_card:
                is_a_lie = True
                break
        
        if is_a_lie:
            # Penantang BENAR, yang main kartu KALAH
            winner, loser = challenger_id, player_who_played
            self.proceed_roulette(loser)  # Pemain yang kalah harus menjalani roulette
            self.log.append(f"{challenger_id} challenges {player_who_played}... and was RIGHT! The card was not a {self.reference_card}.")
        else:
            # Penantang SALAH, penantang KALAH
            winner, loser = player_who_played, challenger_id
            self.proceed_roulette(winner)
            self.log.append(f"{challenger_id} challenges {player_who_played}... and was WRONG!")
        
        # Reset tumpukan untuk ronde baru
        self.card_pile = []
        
        # --- PERUBAHAN: Panggil next_turn dengan menyertakan pemenang challenge ---
        self.next_turn(set_turn_to_player=winner)
        return {"status": "OK", "challenge_winner": winner, "challenge_loser": loser}