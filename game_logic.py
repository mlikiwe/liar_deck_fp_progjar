import random
import string
from mongo_client import MongoClient

mongodb = MongoClient()


class LiarDeckGame:
    def __init__(self):
        mongodb.reset_database()
        self.reload_state_from_db()

    def reload_state_from_db(self):
        self.players = mongodb.get_all_players_data() or {}
        self.game_started = True if mongodb.get_game_state() else False
        self.card_pile = mongodb.get_card_pile() or []
        self.current_turn_index = mongodb.get_current_turn_index() or 0
        self.player_order = mongodb.get_player_order() or []
        self.reference_card = mongodb.get_reference_card()
        self.last_play = mongodb.get_last_play() or {"player_id": None, "cards": []}
        self.game_winner = mongodb.get_game_winner() or None
        self.log = mongodb.get_log() or []
        self.assigned_players = mongodb.get_assigned_players() or []

    def join_game(self):
        self.reload_state_from_db()

        if len(self.assigned_players) >= 4:
            return {"status": "ERROR", "message": "Game is full."}

        all_possible_players = ["player1", "player2", "player3", "player4"]

        for player_id in all_possible_players:
            if player_id not in self.assigned_players:
                self.assigned_players.append(player_id)
                mongodb.set_assigned_players(self.assigned_players)
                player_key = self.generate_player_key()
                mongodb.set_player_key(player_id, player_key)

                self.add_to_log(f"{player_id} has joined the lobby.")
                return {"status": "OK", "player_id": player_id, "key": player_key}

        return {"status": "ERROR", "message": "Could not assign player ID."}

    def start_game(self):
        mongodb.reset_new_game_state()

        self.player_order = self.assigned_players

        mongodb.set_player_order(self.player_order)
        mongodb.set_assigned_players(self.player_order)

        if len(self.player_order) < 2:
            self.log = ["Waiting for more players to join..."]
            mongodb.set_log(self.log)
            return {"status": "ERROR", "message": "Need at least 2 players to start."}

        deck = self.shuffle_deck()

        num_players = len(self.player_order)
        cards_per_player = len(deck) // num_players

        for i, player_id in enumerate(self.player_order):
            player_key = mongodb.get_player_key(player_id)
            print(f"Assigning player {player_id} with key {player_key}")
            self.players[player_id] = {
                "hand": deck[i * cards_per_player: (i + 1) * cards_per_player],
                "roulette_index": 0,
                "roulette": random.randint(0, 2),
                "key": mongodb.get_player_key(player_id),
                "is_eliminated": False
            }
            mongodb.insert_player_data(player_id, self.players[player_id])

        self.game_started = True
        mongodb.set_game_state(True)
        self.current_turn_index = 0
        mongodb.set_current_turn_index(self.current_turn_index)

        self.log = []  # Reset log for new game
        self.add_to_log(f"Game started with {num_players} players.")
        self.add_to_log(f"Reference card is {self.reference_card}.")
        self.add_to_log(f"It's {self.player_order[self.current_turn_index]}'s turn.")

        return {"status": "OK", "message": "Game started successfully."}

    def generate_new_deck(self):
        deck = self.shuffle_deck()

        active_players = [p for p in self.player_order if not self.players.get(p, {}).get("is_eliminated")]
        num_active_players = len(active_players)
        if num_active_players == 0: return

        cards_per_player = len(deck) // num_active_players

        for i, player_id in enumerate(active_players):
            self.players[player_id]["hand"] = deck[i * cards_per_player: (i + 1) * cards_per_player]
            mongodb.update_player_hand(player_id, self.players[player_id]["hand"])

    def shuffle_deck(self):
        ranks = ["Ace", "Jack", "Queen", "King"]
        deck = [rank for rank in ranks for _ in range(6)]
        random.shuffle(deck)
        self.reference_card = random.choice(ranks)
        mongodb.set_reference_card(self.reference_card)
        return deck

    def get_game_state(self, player_id, key=None):
        self.reload_state_from_db()

        if not self.game_started:
            return {
                "game_started": False,
                "assigned_players": self.assigned_players,
                "log": self.log,
                "message": "Game has not started. Waiting in lobby."
            }

        player_data = mongodb.get_player_data(player_id)

        if key:
            if not self.verify_player_key(player_id, key):
                return {"status": "ERROR", "game_started": self.game_started, "error": "Invalid player key."}

        if not player_data:
            return {"status": "ERROR", "game_started": self.game_started, "error": "Player not found in this game."}

        all_players = mongodb.get_all_players_data()

        state = {
            "game_started": True,
            "is_eliminated": player_data.get("is_eliminated", False),
            "your_hand": player_data.get("hand", []),
            "roulette_index": player_data.get("roulette_index", 0),
            "all_players_card_count": {pid: len(p.get("hand", [])) for pid, p in all_players.items()},
            "players_eliminated": [pid for pid, p in all_players.items() if p.get("is_eliminated")],
            "card_pile_count": len(self.card_pile),
            "current_turn": self.player_order[self.current_turn_index] if self.player_order else None,
            "reference_card": self.reference_card,
            "game_winner": self.game_winner,
            "log": self.log[-5:]
        }
        return state

    def next_turn(self, set_turn_to_player=None):
        # self.reload_state_from_db()
        active_players = [p for p in self.player_order if not self.players.get(p, {}).get("is_eliminated")]

        if not active_players or len(active_players) <= 1:
            self.game_winner = active_players[0] if active_players else "No one"
            mongodb.set_game_winner(self.game_winner)
            self.add_to_log(f"Game over! Winner is {self.game_winner}")
            return

        all_hands_empty = all(len(self.players[p].get("hand", [])) == 0 for p in active_players)
        if all_hands_empty:
            self.generate_new_deck()
            self.add_to_log("All players have no cards left. New deck generated.")

        if set_turn_to_player and not self.players.get(set_turn_to_player, {}).get("is_eliminated"):
            self.current_turn_index = self.player_order.index(set_turn_to_player)
        else:
            current_player_id = self.player_order[self.current_turn_index]

            next_index = (self.player_order.index(current_player_id) + 1) % len(self.player_order)

            while self.players.get(self.player_order[next_index], {}).get("is_eliminated"):
                next_index = (next_index + 1) % len(self.player_order)
            self.current_turn_index = next_index

        if len(self.players[self.player_order[self.current_turn_index]].get("hand", [])) == 0:
            print("Setting game winner due to no cards left.")
            winner = self.player_order[self.current_turn_index]
            self.set_game_winner(winner)
            return {"status": "OK", "message": f"No cards left to play. {winner} is the winner!"}

        # if set_turn_to_player:
        #     for pid in self.players:
        #         if len(self.players[pid].get("hand", [])) == 0:
        #             self.set_game_winner(pid)
        #             return {"status": "OK", "message": f"{pid} has no cards left. Game over!"}

        mongodb.set_current_turn_index(self.current_turn_index)
        self.add_to_log(f"It's {self.player_order[self.current_turn_index]}'s turn.")

    def play_card(self, player_id, cards_played, key=None):
        self.reload_state_from_db()
        if self.player_order[self.current_turn_index] != player_id:
            return {"status": "ERROR", "message": "Not your turn."}

        if key and not self.verify_player_key(player_id, key):
            return {"status": "ERROR", "message": "Invalid player key."}

        for player in self.player_order:
            if (len(self.players.get(player, {}).get("hand", [])) == 0 and
                    not self.players[player].get("is_eliminated", False)):
                self.set_game_winner(player)
                return {"status": "OK", "message": f"{player} has no cards left. Game over!"}

        player_hand = self.players.get(player_id, {}).get("hand", [])

        # Verify cards are in hand before removing
        temp_hand = list(player_hand)
        for card in cards_played:
            if card in temp_hand:
                temp_hand.remove(card)
            else:
                return {"status": "ERROR", "message": f"You don't have a {card}."}

        # If verification passes, update hand
        self.players[player_id]["hand"] = temp_hand
        mongodb.update_player_hand(player_id, temp_hand)

        self.card_pile.extend(cards_played)
        mongodb.set_card_pile(self.card_pile)

        mongodb.set_last_play(player_id, cards_played)
        self.last_play = {"player_id": player_id, "cards": cards_played}

        self.add_to_log(f"{player_id} played {len(cards_played)} card(s).")
        self.next_turn()
        return {"status": "OK"}

    def set_game_winner(self, player_id):
        # self.reload_state_from_db()
        if player_id not in self.players or self.players[player_id]["is_eliminated"]:
            return {"status": "ERROR", "message": "Player not found or already eliminated."}

        self.game_winner = player_id
        print("Game winner set to:", self.game_winner)
        mongodb.set_game_winner(self.game_winner)
        self.add_to_log(f"Game over! Winner is {self.game_winner}")

    def kill_player(self, player_id):
        # self.reload_state_from_db()
        if player_id not in self.players or self.players[player_id]["is_eliminated"]:
            return {"status": "ERROR", "message": "Player not found or already eliminated."}

        self.players[player_id]["is_eliminated"] = True
        mongodb.set_player_killed(player_id)
        self.add_to_log(f"{player_id} has been eliminated.")

        # Check for winner
        active_players = [p for p in self.player_order if not self.players.get(p, {}).get("is_eliminated")]
        if len(active_players) == 1:
            self.game_winner = active_players[0]
            mongodb.set_game_winner(self.game_winner)
            self.add_to_log(f"Game over! Winner is {self.game_winner}")

    def proceed_roulette(self, player_id):
        # self.reload_state_from_db()
        player_data = self.players.get(player_id)
        if not player_data: return

        roulette_index = player_data["roulette_index"]
        bullet_position = player_data["roulette"]

        if roulette_index == bullet_position:
            self.add_to_log(f"{player_id} pulls the trigger... BANG!")
            self.kill_player(player_id)
        else:
            player_data["roulette_index"] += 1
            mongodb.set_roulette_index(player_id, player_data["roulette_index"])
            self.add_to_log(f"{player_id} survived the roulette! Index is now {player_data['roulette_index']}.")

    def challenge(self, challenger_id, key=None):
        self.reload_state_from_db()

        if not self.last_play or not self.last_play["player_id"]:
            return {"status": "ERROR", "message": "No play to challenge."}

        if key and not self.verify_player_key(challenger_id, key):
            return {"status": "ERROR", "message": "Invalid player key."}

        player_who_played = self.last_play["player_id"]
        cards_in_play = self.last_play["cards"]

        is_a_lie = any(card != self.reference_card for card in cards_in_play)

        if is_a_lie:
            winner, loser = challenger_id, player_who_played
            self.add_to_log(f"{challenger_id} challenges {player_who_played}... and was RIGHT!")
            self.proceed_roulette(loser)
        else:
            winner, loser = player_who_played, challenger_id
            self.add_to_log(f"{challenger_id} challenges {player_who_played}... and was WRONG!")
            self.proceed_roulette(loser)

        self.card_pile = []

        mongodb.set_card_pile([])
        mongodb.set_last_play(None, [])  # Clear last play after challenge

        self.generate_new_deck()
        self.next_turn(set_turn_to_player=winner)
        return {"status": "OK", "challenge_winner": winner, "challenge_loser": loser}

    def add_to_log(self, message):
        current_log = mongodb.get_log() or []
        current_log.append(message)
        mongodb.set_log(current_log)
        self.log = current_log

    def generate_player_key(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    def verify_player_key(self, player_id, key):
        player_data = mongodb.get_player_data(player_id)
        if not player_data:
            return False
        return player_data.get("key") == key