from pymongo import MongoClient as PyMongoClient
from dotenv import load_dotenv
import os

class MongoClient:
    def __init__(self):
        load_dotenv()
        mongo_connection_string = os.getenv('MONGO_CONNECTION_STRING')
        self.mongo_client = PyMongoClient(mongo_connection_string)
        

    def set_game_state(self, game_state):
        self.mongo_client.liar_decks.game_data.update_one(
            {"_id": "game_state"}, 
            {"$set": {"value": game_state}}, 
            upsert=True
        )
        
    def get_game_state(self):
        doc = self.mongo_client.liar_decks.game_data.find_one({"_id": "game_state"})
        if doc:
            return True if doc["value"] else False
        return None
    
    def set_card_pile(self, card_pile):
        self.mongo_client.liar_decks.game_data.update_one(
            {"_id": "card_pile"}, 
            {"$set": {"value": card_pile}}, 
            upsert=True
        )
        
    def get_card_pile(self):
        doc = self.mongo_client.liar_decks.game_data.find_one({"_id": "card_pile"})
        if doc:
            return doc["value"]
        return None
    
    def set_reference_card(self, reference_card):
        self.mongo_client.liar_decks.game_data.update_one(
            {"_id": "reference_card"}, 
            {"$set": {"value": reference_card}}, 
            upsert=True
        )
    
    def get_reference_card(self):
        doc = self.mongo_client.liar_decks.game_data.find_one({"_id": "reference_card"})
        if doc:
            return doc["value"]
        return None
    
    def set_log(self, log):
        self.mongo_client.liar_decks.game_data.update_one(
            {"_id": "log"}, 
            {"$set": {"value": log}}, 
            upsert=True
        )
        
    def get_log(self):
        doc = self.mongo_client.liar_decks.game_data.find_one({"_id": "log"})
        if doc:
            return doc["value"]
        return None
    
    def set_current_turn_index(self, index):
        self.mongo_client.liar_decks.game_data.update_one(
            {"_id": "current_turn_index"}, 
            {"$set": {"value": index}}, 
            upsert=True
        )
        
    def get_current_turn_index(self):
        doc = self.mongo_client.liar_decks.game_data.find_one({"_id": "current_turn_index"})
        if doc:
            return int(doc["value"])
        return None

    def insert_player_data(self, player_id, player_data):
        player_data_mapping = {
            "hand": player_data["hand"], 
            "roulette_index": player_data["roulette_index"],
            "roulette": player_data["roulette"],
            "is_eliminated": player_data["is_eliminated"]
        }
        
        self.mongo_client.liar_decks.players.update_one(
            {"_id": player_id}, 
            {"$set": player_data_mapping}, 
            upsert=True
        )
    
    def get_player_data(self, player_id):
        try:
            player_doc = self.mongo_client.liar_decks.players.find_one({"_id": player_id})
            
            if not player_doc:
                return None
            
            # Remove the _id field from the returned document
            if "_id" in player_doc: 
                del player_doc["_id"]
                
            return player_doc
        except Exception as e:
            print(f"Error retrieving player data for {player_id}: {e}")
            return None
        
    def get_all_players_data(self):
        all_players_data = {}
        player_ids = ["player1", "player2", "player3", "player4"]
        
        try:
            for player_id in player_ids:
                player_doc = self.mongo_client.liar_decks.players.find_one({"_id": player_id})
                if player_doc:
                    player_data = player_doc.copy()
                    del player_data["_id"]
                    all_players_data[player_id] = player_data
                
            return all_players_data
        except Exception as e:
            print(f"Error retrieving all players data: {e}")
            return {}
    
    def set_game_winner(self, player_id):
        self.mongo_client.liar_decks.game_data.update_one(
            {"_id": "game_winner"}, 
            {"$set": {"value": player_id}}, 
            upsert=True
        )
        
    def get_game_winner(self):
        doc = self.mongo_client.liar_decks.game_data.find_one({"_id": "game_winner"})
        if doc:
            return doc["value"]
        return None
    
    def set_last_play(self, player_id, cards):
        last_play = {
            "player_id": player_id,
            "cards": cards
        }
        self.mongo_client.liar_decks.game_data.update_one(
            {"_id": "last_play"}, 
            {"$set": {"value": last_play}}, 
            upsert=True
        )
    
    def get_last_play(self):
        doc = self.mongo_client.liar_decks.game_data.find_one({"_id": "last_play"})
        if doc:
            return doc["value"]
        return {"player_id": None, "cards": []}
    
    def set_player_order(self, player_order):
        self.mongo_client.liar_decks.game_data.update_one(
            {"_id": "player_order"}, 
            {"$set": {"value": player_order}}, 
            upsert=True
        )
    
    def get_player_order(self):
        doc = self.mongo_client.liar_decks.game_data.find_one({"_id": "player_order"})
        if doc:
            return doc["value"]
        return None
    
    def set_roulette_index(self, player_id, index):
        self.mongo_client.liar_decks.players.update_one(
            {"_id": player_id}, 
            {"$set": {"roulette_index": index}}
        )
    
    def set_player_killed(self, player_id):
        self.mongo_client.liar_decks.players.update_one(
            {"_id": player_id}, 
            {"$set": {"is_eliminated": True}}
        )
        
    def update_player_hand(self, player_id, hand):
        self.mongo_client.liar_decks.players.update_one(
            {"_id": player_id}, 
            {"$set": {"hand": hand}}
        )
    
    def reset_database(self):
        self.mongo_client.liar_decks.game_data.drop()
        self.mongo_client.liar_decks.players.drop()
        
    
    

