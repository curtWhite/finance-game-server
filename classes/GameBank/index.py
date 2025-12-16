from app import db
from app.utils.db_guard import db_call_guard
from classes.Player.index import Player
from classes.Bank.index import Bank

class GameBank:
    def __init__(self, balance=1000000):
        self.balance = balance
        self.properties = [] #/Not yet implemented
        self.stock = []  #Not yet implemented
        self.load_from_db()

    def load_from_db(self):
        """
        Loads bank data from the db or initializes if not exists.
        """
        with db_call_guard("GameBank.load_from_db"):
            bank_collection = db['game-bank']
            bank_data = bank_collection.find_one({"_id": "main"})
            if bank_data:
                self.balance = bank_data.get("balance", self.balance)
                self.name = 'GAME BANK'
            else:
                self.save_to_db()

    def save_to_db(self):
        """
        Saves the current bank state to the db.
        """
        with db_call_guard("GameBank.save_to_db"):
            bank_collection = db['game-bank']
            bank_collection.replace_one(
                {"_id": "main"},
                {"_id": "main", "balance": self.balance},
                upsert=True
            )

    def pay_player(self, player_username, amount, proxy=None, message=None):
        """
        Pays a player from the bank's balance.
        """
        if amount > self.balance:
            raise ValueError("Bank does not have enough balance.")
        player = Player(username=player_username)
        player_data = player.get_player(player_username)
        if not player:
            raise ValueError(f"Player '{player_username}' not found.")
        bank = Bank(customer=player)
        bank.deposit(amount=amount, sender=proxy if proxy != None else self.name, message=message)
        self.balance -= amount
        self.save_to_db()

    def sell_asset_to_player(self, player_username, asset, price, asset_type):
        """
        Sells an asset (property, crypto, commodities, business, stock) to the player in exchange for score/points.
        """
        if price > self.balance:
            raise ValueError("Bank does not have enough balance to cover the asset (simulation purpose).")
        player = Player.get_player(player_username)
        if not player:
            raise ValueError(f"Player '{player_username}' not found.")
        if player.score < price:
            raise ValueError("Player does not have enough score/points to purchase asset.")

        # Deduct from player, add to bank
        player.score -= price
        self.balance += price
        # Add asset to player
        if asset_type == "property":
            player.add_property(asset)
        elif asset_type == "crypto":
            player.add_crypto(asset)
        elif asset_type == "commodity":
            player.add_commodity(asset)
        elif asset_type == "business":
            player.add_business(asset)
        elif asset_type == "stock":
            player.add_stock(asset)
        else:
            raise ValueError(f"Unknown asset type: {asset_type}")
        player.save_to_db()
        self.save_to_db()


    def give_loan_to_player(self, player_username, amount):
        """
        Gives a loan to a player if the bank has enough balance.
        The player receives 'amount', but could repay later (repay logic not included).
        """
        if amount > self.balance:
            raise ValueError("Bank does not have enough balance to give this loan.")
        player = Player.get_player(player_username)
        if not player:
            raise ValueError(f"Player '{player_username}' not found.")
        # For simplicity, loan is added to player score. You could add loan tracking later.
        player.increase_score(amount)
        self.balance -= amount
        self.save_to_db()

    @classmethod
    def get_bank(cls):
        return cls()

