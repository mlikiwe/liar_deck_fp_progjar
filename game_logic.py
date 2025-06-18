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
        if self.game_started:
            return

        # 1. Buat dek kartu sesuai aturan
        ranks = ["Ace", "Jack", "Queen", "King"]
        deck = [rank for rank in ranks for _ in range(6)]
        random.shuffle(deck)

        # 2. Inisialisasi pemain dan bagi kartu
        self.player_order = [pid.strip() for pid in player_ids]
        
        for i, player_id in enumerate(self.player_order):
            self.players[player_id] = {
                "hand": deck[i*6 : (i+1)*6],
                "is_eliminated": False
            }

        # 3. Tentukan kartu acuan pertama
        self.reference_card = random.choice(ranks)
        
        self.game_started = True
        self.current_turn_index = 0
        self.log = [f"Game started. Reference card is {self.reference_card}."]
        self.log.append(f"It's {self.player_order[self.current_turn_index]}'s turn.")

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
        
    def next_turn(self):
        # Pindah ke pemain berikutnya yang belum tereliminasi
        active_players = [p for p in self.player_order if not self.players[p]["is_eliminated"]]
        if not active_players or len(active_players) == 1:
            self.game_winner = active_players[0] if active_players else "No one"
            self.log.append(f"Game over! Winner is {self.game_winner}")
            return

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
        self.next_turn()
        return {"status": "OK"}


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
            self.log.append(f"{challenger_id} challenges {player_who_played}... and was RIGHT! The card was not a {self.reference_card}.")
        else:
            # Penantang SALAH, penantang KALAH
            winner, loser = player_who_played, challenger_id
            self.log.append(f"{challenger_id} challenges {player_who_played}... and was WRONG!")
        
        self.players[loser]["is_eliminated"] = True
        self.log.append(f"{loser} has been eliminated.")
        
        # Reset tumpukan untuk ronde baru
        self.card_pile = []
        
        self.next_turn()
        return {"status": "OK", "challenge_winner": winner, "challenge_loser": loser}