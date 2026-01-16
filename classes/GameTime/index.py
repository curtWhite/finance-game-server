from app import db
from app.utils.db_guard import db_call_guard
from datetime import datetime


game_time_collection = db["game-time-collection"]


class GameTime:
    """
    Per-user game time management for calendar-based game time.
    Stores year, month, week, day, startTime, and elapsedGameMonths.
    """
    
    def __init__(self, data=None):
        self.username = None
        self.year = 2024
        self.month = 1
        self.week = 1
        self.day = 1
        self.startTime = None
        self.elapsedGameMonths = 0.0
        
        if data:
            self.load(data)
    
    def toDict(self):
        """
        Convert game time to dictionary for serialization.
        
        Returns:
            dict: Game time data as dictionary
        """
        return {
            "username": self.username,
            "year": self.year,
            "month": self.month,
            "week": self.week,
            "day": self.day,
            "startTime": self.startTime.isoformat() if self.startTime else None,
            "elapsedGameMonths": self.elapsedGameMonths,
        }
    
    def load(self, data):
        """
        Load game time data from dictionary.
        
        Args:
            data: Dictionary containing game time data
        """
        if isinstance(data, dict):
            self.username = data.get("username")
            self.year = data.get("year", 2024)
            self.month = data.get("month", 1)
            self.week = data.get("week", 1)
            self.day = data.get("day", 1)
            self.elapsedGameMonths = data.get("elapsedGameMonths", 0.0)
            
            # Parse startTime if it's a string
            startTime = data.get("startTime")
            if startTime:
                if isinstance(startTime, str):
                    try:
                        self.startTime = datetime.fromisoformat(startTime.replace('Z', '+00:00'))
                    except:
                        self.startTime = None
                elif isinstance(startTime, datetime):
                    self.startTime = startTime
                else:
                    self.startTime = None
            else:
                self.startTime = None
    
    def save_to_db(self):
        """
        Save game time to database.
        """
        try:
            with db_call_guard("GameTime.save_to_db"):
                if not self.username:
                    raise ValueError("Username is required to save game time")
                
                data = self.toDict()
                # Remove username from data for query, but keep it in the document
                username = data.pop("username", None)
                
                if username:
                    result = game_time_collection.replace_one(
                        {"username": username},
                        {"username": username, **data},
                        upsert=True
                    )
                else:
                    raise ValueError("Username is required to save game time")
        except Exception as e:
            print(f"Exception occurred in GameTime.save_to_db: {e}")
            raise
    
    @classmethod
    def load_from_db(cls, username):
        """
        Load game time from database by username.
        
        Args:
            username: Username of the player
        
        Returns:
            GameTime instance or None if not found
        """
        try:
            with db_call_guard("GameTime.load_from_db"):
                if not username:
                    return None
                
                doc = game_time_collection.find_one({"username": username})
                if doc:
                    instance = cls()
                    instance.load(doc)
                    return instance
        except Exception as e:
            print(f"Exception occurred in GameTime.load_from_db: {e}")
        return None
    
    @classmethod
    def create_or_update(cls, username, game_time_data):
        """
        Create or update game time for a user.
        
        Args:
            username: Username of the player
            game_time_data: Dictionary with game time data
        
        Returns:
            GameTime instance
        """
        instance = cls.load_from_db(username)
        if not instance:
            instance = cls()
            instance.username = username
        
        # Update with new data
        instance.load({**game_time_data, "username": username})
        instance.save_to_db()
        
        return instance
