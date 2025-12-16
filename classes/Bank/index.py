# INSERT_YOUR_CODE
from app import db

bank_collection = db['bank-collection']
bank_logs_collection = db['bank-logs-collection']

class Bank:
    def __init__(self, initial_balance: float = 1000, customer = None):
        self._player = customer
        self.bank = bank_collection.find_one({"customerId": getattr(self._player, 'id', None)})
        # Load logs from bank ID if available
        if self.bank and '_id' in self.bank:
            logs_doc = bank_logs_collection.find_one({"bankId": self.bank['_id']})
            self.bank_logs = logs_doc['logs'] if logs_doc and 'logs' in logs_doc else []
        else:
            self.bank_logs = []
        self._operation_logs = self.bank_logs
        self._balance = self.bank['balance'] if self.bank and 'balance' in self.bank else initial_balance
        self.load_bank_data()
            
    
    def _create_new_account(self):
        data = {
            "balance": self._balance,
            "Banklog": self._operation_logs,
            "customerId": getattr(self._player, 'id', None),
            "customerName": f"{getattr(self._player, 'firstName', '')} {getattr(self._player, 'lastName', '')}".strip()
            # 'createdAt' could be added as datetime.utcnow().isoformat() if needed
        }
        return data
 
    def _log_operation(self, entry: dict):
        
        log_entry = entry.copy()
        from datetime import datetime
        log_entry['date'] = datetime.utcnow()
        self._operation_logs.append(log_entry)
        self._operation_logs = self._operation_logs[-20:]

    def deposit(self, amount: float, sender=None, message=None):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self._balance += amount

        self._log_operation({
            'type': 'deposit',
            'amount': amount,
            'balanceAfter': self._balance,
            'from': sender,
            'message': message
        })
        self.save_bank_data()

    def withdraw(self, amount: float):
        if amount <= 0:
            raise ValueError("Withdraw amount must be positive")
        if amount > self._balance:
            raise ValueError("Insufficient funds for withdrawal")
        self._balance -= amount
        self._log_operation({
            'type': 'withdraw',
            'amount': amount,
            'balanceAfter': self._balance
        })
        self.save_bank_data()


    def make_payment(self, amount: float, recipient: str):
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        if amount > self._balance:
            raise ValueError("Insufficient funds for payment")
        self._balance -= amount
        self._log_operation({
            'type': 'payment',
            'amount': amount,
            'to': recipient,
            'balanceAfter': self._balance
        })
        self.save_bank_data()

    
    def get_logs(self):
        return self._operation_logs[:]
    
    def get_balance(self) -> float:
        return self._balance

    @classmethod
    def create_account(cls, initial_balance: float = 0):
        return cls(initial_balance)

    def delete_account(self):
        self._balance = 0
        self._operation_logs = []
        customer_id = getattr(self._player, 'id', None)
        if customer_id:
            # Delete the bank account document
            bank_collection.delete_one({"customerId": customer_id})
            # Delete any associated logs
            bank_logs_collection.delete_many({"bankId": self.bank['_id']}) if self.bank and '_id' in self.bank else None
            self.bank = None
            self.bank_logs = []

    def load_bank_data(self):
        """
        Loads the bank data for this customer from the database and loads it into the class instance.
        """
        customer_id = getattr(self._player, '_id', None)
        if not customer_id:
            # Try loading by username if id not present
            username = getattr(self._player, 'username', None)
            if username:
                player = self._player.get_player(username)
                customer_id = getattr(player, '_id', None)
        if not customer_id:
            raise ValueError("Cannot load bank data: customer ID not found.")

        bank_doc = bank_collection.find_one({"customerId": customer_id})
        if bank_doc:
            self.bank = bank_doc
            self._balance = bank_doc.get("balance", self._balance)
            self._operation_logs = bank_doc.get("Banklog", [])
        else:
            self.bank = None
            self._balance = 0
            self._operation_logs = []

        # Load logs from the bank_logs_collection, if exists
        if self.bank and '_id' in self.bank:
            logs_doc = bank_logs_collection.find_one({"bankId": self.bank['_id']})
            self.bank_logs = logs_doc['logs'] if logs_doc and 'logs' in logs_doc else []
        else:
            self.bank_logs = []

    def save_bank_data(self):
            """
            Update bank data if it exists, or create a new entry if not.
            """
            customer_id = getattr(self._player, '_id', None)

            if not self._player or customer_id == None:
                player = self._player.get_player(self._player.username)
                customer_id = player._id

            bank_data = {
                "balance": self._balance,
                "Banklog": self._operation_logs,
                "customerId": customer_id,
                "customer": f"{getattr(self._player, 'username', '')}".strip()
            }
            # Try to update, or insert if not exists (upsert=True)
            result = bank_collection.replace_one(
                {"customerId": customer_id},
                bank_data,
                upsert=True
            )
            # Store all logs in a single document per bank to optimize performance
            if self._operation_logs:
                bank_id = result.upserted_id if result.upserted_id else self.bank['_id'] if self.bank and '_id' in self.bank else None
                # Upsert a single document containing all logs for the bank
                bank_logs_collection.replace_one(
                    {"bankId": bank_id},
                    {
                        "bankId": bank_id,
                        "logs": self._operation_logs
                    },
                    upsert=True
                )
            self.load_bank_data()
    def to_dict(self, include_logs=False):
        """
        Returns a dictionary representation of the bank object.
        """
        data = {
            "balance": self._balance,
            "customer": getattr(self._player, 'username', None)
        }

        if include_logs:
            data['bank_logs'] = self.bank_logs
            data['operation_logs'] = self._operation_logs

        return data
