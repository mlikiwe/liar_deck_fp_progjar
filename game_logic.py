import random
from mongo_client import MongoClient 

mongodb = MongoClient()

class LiarDeckGame:
    def __init__(self):
        mongodb.reset_database()
        self.players = mongodb.get_all_players_data() or {}
        self.game_started = True if mongodb.get_game_state() else False or False
        self.card_pile = mongodb.get_card_pile() or []
        self.current_turn_index = mongodb.get_current_turn_index() or 0
        self.player_order = mongodb.get_player_order() or []
        self.reference_card = mongodb.get_reference_card()
        self.last_play = mongodb.get_last_play() or {"player_id": None, "cards": []}
        self.game_winner = mongodb.get_game_winner() or None
        self.log = mongodb.get_log() or ["Game has not started."]

    def start_game(self, player_ids=["player1", "player2", "player3", "player4"]):
        # self.players = {}
        # self.card_pile = []
        # self.current_turn_index = 0
        # self.player_order = []
        # self.reference_card = None
        # self.last_play = {"player_id": None, "cards": []}
        # self.game_winner = None
        # self.log = ["Game has not started."]
        
        deck = self.shuffle_deck()
        
        # 2. Inisialisasi pemain dan bagi kartu
        self.player_order = [pid.strip() for pid in player_ids]
        mongodb.set_player_order(self.player_order)
        
        for i, player_id in enumerate(self.player_order):
            self.players[player_id] = {
                "hand": deck[i*6 : (i+1)*6],
                "roulette_index":0,
                "roulette": random.randint(0, 2),  # Indeks acak untuk roulette
                "is_eliminated": False
            }
            mongodb.insert_player_data(player_id, self.players[player_id])
        
        self.game_started = True
        mongodb.set_game_state(1 if self.game_started else 0)
        self.current_turn_index = 0
        mongodb.set_current_turn_index(self.current_turn_index)
        self.write_log = [f"Game started. Reference card is {self.reference_card}."]
        self.write_log(f"It's {self.player_order[self.current_turn_index]}'s turn.")
        
    def generate_new_deck(self):
        deck = self.shuffle_deck()
        
        for i, player_id in enumerate(self.player_order):
            if self.players[player_id]["is_eliminated"]:
                continue
            self.players[player_id]["hand"] = deck[i*6 : (i+1)*6]
        
    def shuffle_deck(self):
        # Mengacak dek kartu
        ranks = ["Ace", "Jack", "Queen", "King"]
        deck = [rank for rank in ranks for _ in range(6)]
        random.shuffle(deck)
        self.reference_card = random.choice(ranks)
        mongodb.set_reference_card(self.reference_card)
        return deck

    def get_game_state(self, player_id):
        # Mengembalikan state yang relevan untuk satu pemain
        game_started = mongodb.get_game_state()
        if game_started is None or not game_started:
            return {"game_started": False, "message": "Game has not started."}
        
        player_data = mongodb.get_player_data(player_id)
        card_pile = mongodb.get_card_pile()
        reference_card = mongodb.get_reference_card()
        all_players = mongodb.get_all_players_data()
        log = mongodb.get_log()
        
        state = {
            "game_started": True,
            "your_hand": player_data["hand"] if player_data else [],
            "your_roulette_index": player_data["roulette_index"] if player_data else 0, 
            "all_players_card_count": {pid: len(p["hand"]) for pid, p in all_players.items()},
            "players_eliminated": [pid for pid, p in self.players.items() if p["is_eliminated"]],
            "card_pile_count": len(card_pile) if card_pile else 0,
            "current_turn": self.player_order[mongodb.get_current_turn_index()] if mongodb.get_current_turn_index() is not None else self.player_order[self.current_turn_index],
            "reference_card": reference_card if reference_card else self.reference_card,
            "game_winner": self.game_winner,
            "log": log[-5:] if log else [],
        }
        return state
        
    def next_turn(self, set_turn_to_player=None):
        active_players = [p for p in self.player_order if not self.players[p]["is_eliminated"]]
        if not active_players or len(active_players) == 1:
            self.game_winner = active_players[0] if active_players else "No one"
            self.write_log(f"Game over! Winner is {self.game_winner}")
            return

        if set_turn_to_player:
            # Jika ada pemenang challenge, set giliran ke dia
            self.current_turn_index = self.player_order.index(set_turn_to_player)
        else:
            # Jika tidak, lanjutkan ke pemain berikutnya dalam urutan
            self.current_turn_index = (self.current_turn_index + 1) % len(self.player_order)
            while self.players[self.player_order[self.current_turn_index]]["is_eliminated"]:
                self.current_turn_index = (self.current_turn_index + 1) % len(self.player_order)
                
        mongodb.set_current_turn_index(self.current_turn_index)
        
        self.write_log(f"It's {self.player_order[self.current_turn_index]}'s turn.")

    def play_card(self, player_id, cards_played):
        if self.player_order[self.current_turn_index] != player_id:
            return {"status": "ERROR", "message": "Not your turn."}
        
        self.players = mongodb.get_all_players_data()
        
        # Hapus kartu dari tangan pemain
        for card in cards_played:
            if card in self.players[player_id]["hand"]:
                self.players[player_id]["hand"].remove(card)
                mongodb.update_player_hand(player_id, self.players[player_id]["hand"])
                
            else:
                return {"status": "ERROR", "message": f"You don't have a {card}."}

        self.card_pile.extend(cards_played)
        mongodb.set_card_pile(self.card_pile)
        self.last_play = {"player_id": player_id, "cards": cards_played}
        mongodb.set_last_play(player_id, cards_played)
        self.write_log(f"{player_id} played {len(cards_played)} card(s).")
        self.next_turn() # Panggilan ini tidak berubah, akan memajukan giliran secara normal
        return {"status": "OK"}
    
    def kill_player(self, player_id):
        if player_id not in self.players or self.players[player_id]["is_eliminated"]:
            return {"status": "ERROR", "message": "Player not found or already eliminated."}
        
        self.players[player_id]["is_eliminated"] = True
        mongodb.set_player_killed(player_id)
        self.write_log(f"{player_id} has been eliminated.")
        
        # Cek apakah game berakhir
        active_players = [p for p in self.player_order if not self.players[p]["is_eliminated"]]
        if len(active_players) == 1:
            self.game_winner = active_players[0]
            mongodb.set_game_winner(self.game_winner)
            self.write_log(f"Game over! Winner is {self.game_winner}")
            
        # Pindah ke pemain berikutnya
        self.next_turn()
        return {"status": "OK", "eliminated_player": player_id}
    
    def proceed_roulette(self, player_id):        
        roulette_index = self.players[player_id]["roulette_index"]
        bullet_position = self.players[player_id]["roulette"]
        
        if roulette_index == bullet_position:
           self.kill_player(player_id)
           self.write_log(f"{player_id} has been shot by the roulette!")
        else:
            # Pemain aman, lanjutkan ke giliran berikutnya
            self.players[player_id]["roulette_index"] += 1
            mongodb.set_roulette_index(player_id, self.players[player_id]["roulette_index"])
            self.write_log(f"{player_id} survived the roulette! Current roulette index: {self.players[player_id]['roulette_index']}.")

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
            self.write_log(f"{challenger_id} challenges {player_who_played}... and was RIGHT! The card was not a {self.reference_card}.")
            self.proceed_roulette(loser)  # Pemain yang kalah harus menjalani roulette
        else:
            # Penantang SALAH, penantang KALAH
            winner, loser = player_who_played, challenger_id
            self.write_log(f"{challenger_id} challenges {player_who_played}... and was WRONG!")
            self.proceed_roulette(loser)
        
        # Reset tumpukan untuk ronde baru
        self.card_pile = []
        mongodb.set_card_pile(self.card_pile)
        
        # --- PERUBAHAN: Panggil next_turn dengan menyertakan pemenang challenge ---
        self.generate_new_deck()
        self.next_turn(set_turn_to_player=winner)
        return {"status": "OK", "challenge_winner": winner, "challenge_loser": loser}
    
    def write_log(self, message):
        # Tambahkan pesan ke log
        self.log.append(message)
        mongodb.set_log(self.log)