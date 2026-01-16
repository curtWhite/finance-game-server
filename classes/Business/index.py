from app import db
from app.utils.db_guard import db_call_guard
from bson import ObjectId
from datetime import datetime


business_collection = db["business-collection"]


class Business:
    """
    Base Business class for managing business entities.
    Provides money account management and storage functionality.
    """
    
    def __init__(self, data=None):
        self._id = None
        self.name = None
        self.type = None  # e.g., 'farm', 'factory', etc.
        self.moneyAccount = {
            "balance": 0.0,
            "logs": []
        }
        self.storage = {
            "items": [],
            "maxCapacity": 5
        }
        self.username = None
        
        if data:
            self.load(data)
    
    def deductMoney(self, amount, description="", category="purchase"):
        """
        Deduct money from the business account.
        
        Args:
            amount: Amount to deduct (float)
            description: Description of the transaction
            category: Category of the transaction (default: "purchase")
        """
        if amount < 0:
            raise ValueError("Amount must be positive")
        
        if self.moneyAccount["balance"] < amount:
            raise ValueError("Insufficient funds in business account")
        
        self.moneyAccount["balance"] -= amount
        self.moneyAccount["logs"].append({
            "amount": -amount,
            "description": description,
            "category": category,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def addMoney(self, amount, description="", category="income"):
        """
        Add money to the business account.
        
        Args:
            amount: Amount to add (float)
            description: Description of the transaction
            category: Category of the transaction (default: "income")
        """
        if amount < 0:
            raise ValueError("Amount must be positive")
        
        self.moneyAccount["balance"] += amount
        self.moneyAccount["logs"].append({
            "amount": amount,
            "description": description,
            "category": category,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def addToStorage(self, item):
        """
        Add an item to business storage.
        
        Args:
            item: Dictionary with id, name, type, quantity, unit, addedDate (optional)
        
        Returns:
            bool: True if successful, False if storage is full
        """
        if len(self.storage["items"]) >= self.storage["maxCapacity"]:
            # Check if item already exists and can be merged
            existing_item = next(
                (i for i in self.storage["items"] 
                 if i.get("type") == item.get("type") and i.get("name") == item.get("name")),
                None
            )
            if existing_item:
                existing_item["quantity"] += item.get("quantity", 1)
                return True
            return False
        
        # Ensure item has required fields
        storage_item = {
            "id": item.get("id", f"item_{datetime.utcnow().timestamp()}_{len(self.storage['items'])}"),
            "name": item.get("name", ""),
            "type": item.get("type", ""),
            "quantity": item.get("quantity", 1),
            "unit": item.get("unit", "units"),
            "addedDate": item.get("addedDate", datetime.utcnow().isoformat())
        }
        
        # Check if item already exists and merge quantities
        existing_item = next(
            (i for i in self.storage["items"] 
             if i.get("type") == storage_item["type"] and i.get("name") == storage_item["name"]),
            None
        )
        if existing_item:
            existing_item["quantity"] += storage_item["quantity"]
        else:
            self.storage["items"].append(storage_item)
        
        return True
    
    def removeFromStorage(self, itemId, quantity):
        """
        Remove items from business storage.
        
        Args:
            itemId: ID of the item to remove
            quantity: Quantity to remove
        
        Returns:
            bool: True if successful, False if item not found or insufficient quantity
        """
        item = next((i for i in self.storage["items"] if i.get("id") == itemId), None)
        if not item:
            return False
        
        if item["quantity"] < quantity:
            return False
        
        item["quantity"] -= quantity
        if item["quantity"] <= 0:
            self.storage["items"].remove(item)
        
        return True
    
    def toDict(self):
        """
        Convert business to dictionary for serialization.
        
        Returns:
            dict: Business data as dictionary
        """
        return {
            "id": str(self._id) if self._id else None,
            "name": self.name,
            "type": self.type,
            "username": self.username,
            "moneyAccount": self.moneyAccount,
            "storage": self.storage
        }
    
    def load(self, data):
        """
        Load business data from dictionary.
        
        Args:
            data: Dictionary containing business data
        """
        if isinstance(data, dict):
            self._id = data.get("_id") or data.get("id")
            if self._id and not isinstance(self._id, ObjectId):
                try:
                    self._id = ObjectId(self._id)
                except:
                    pass
            self.name = data.get("name")
            self.type = data.get("type")
            self.username = data.get("username")
            self.moneyAccount = data.get("moneyAccount", {"balance": 0.0, "logs": []})
            self.storage = data.get("storage", {"items": [], "maxCapacity": 5})
    
    def save_to_db(self):
        """
        Save business to database.
        """
        try:
            with db_call_guard("Business.save_to_db"):
                data = self.toDict()
                # Remove id from data for MongoDB operations
                business_id = data.pop("id", None)
                
                if business_id:
                    _id = business_id
                    if _id and not isinstance(_id, ObjectId):
                        try:
                            _id = ObjectId(_id)
                        except:
                            pass
                    
                    result = business_collection.update_one(
                        {"_id": _id},
                        {"$set": data}
                    )
                    if result.modified_count == 0 and result.matched_count == 0:
                        # If not found, insert as new
                        data["_id"] = _id
                        business_collection.insert_one(data)
                else:
                    # Insert new document
                    result = business_collection.insert_one(data)
                    self._id = result.inserted_id
        except Exception as e:
            print(f"Exception occurred in Business.save_to_db: {e}")
            raise
    
    @classmethod
    def load_from_db(cls, business_id=None, username=None, name=None):
        """
        Load business from database.
        
        Args:
            business_id: MongoDB _id of the business
            username: Username of the business owner
            name: Name of the business
        
        Returns:
            Business instance or None if not found
        """
        try:
            with db_call_guard("Business.load_from_db"):
                query = {}
                if business_id:
                    if not isinstance(business_id, ObjectId):
                        try:
                            business_id = ObjectId(business_id)
                        except:
                            return None
                    query["_id"] = business_id
                elif username and name:
                    query["username"] = username
                    query["name"] = name
                elif username:
                    query["username"] = username
                else:
                    return None
                
                doc = business_collection.find_one(query)
                if doc:
                    instance = cls()
                    instance.load(doc)
                    instance._id = doc.get("_id")
                    return instance
        except Exception as e:
            print(f"Exception occurred in Business.load_from_db: {e}")
        return None
    
    @classmethod
    def load_all_by_username(cls, username):
        """
        Load all businesses for a username.
        
        Args:
            username: Username of the business owner
        
        Returns:
            List of Business instances
        """
        try:
            with db_call_guard("Business.load_all_by_username"):
                cursor = business_collection.find({"username": username})
                businesses = []
                for doc in cursor:
                    instance = cls()
                    instance.load(doc)
                    instance._id = doc.get("_id")
                    businesses.append(instance)
                return businesses
        except Exception as e:
            print(f"Exception occurred in Business.load_all_by_username: {e}")
            return []
