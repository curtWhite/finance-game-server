from app import db
from app.utils.db_guard import db_call_guard
from datetime import datetime, timedelta


game_state_collection = db["game-state-collection"]


class GameState:
    """
    Global game state management, including current game date.
    Singleton pattern for accessing game state.
    """
    
    _instance = None
    _initialized = False
    
    def __init__(self):
        if not GameState._initialized:
            self.current_date = datetime.utcnow()
            self.game_start_date = datetime.utcnow()
            self.load_from_db()
            GameState._initialized = True
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of GameState."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_current_date(self):
        """Get current game date."""
        return self.current_date
    
    def set_current_date(self, date):
        """
        Set current game date.
        
        Args:
            date: datetime object or ISO string
        """
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except:
                raise ValueError("Invalid date format. Use ISO format.")
        
        self.current_date = date
        self.save_to_db()
    
    def advance_date(self, days=1):
        """
        Advance game date by specified number of days.
        
        Args:
            days: Number of days to advance (default: 1)
        """
        self.current_date += timedelta(days=days)
        self.save_to_db()
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "current_date": self.current_date.isoformat(),
            "game_start_date": self.game_start_date.isoformat(),
        }
    
    def load_from_db(self):
        """Load game state from database."""
        try:
            with db_call_guard("GameState.load_from_db"):
                doc = game_state_collection.find_one({"_id": "main"})
                if doc:
                    current_date_str = doc.get("current_date")
                    game_start_date_str = doc.get("game_start_date")
                    
                    if current_date_str:
                        try:
                            self.current_date = datetime.fromisoformat(current_date_str.replace('Z', '+00:00'))
                        except:
                            pass
                    
                    if game_start_date_str:
                        try:
                            self.game_start_date = datetime.fromisoformat(game_start_date_str.replace('Z', '+00:00'))
                        except:
                            pass
                else:
                    # Initialize with current date
                    self.save_to_db()
        except Exception as e:
            print(f"Exception occurred in GameState.load_from_db: {e}")
    
    def save_to_db(self):
        """Save game state to database."""
        try:
            with db_call_guard("GameState.save_to_db"):
                data = self.to_dict()
                game_state_collection.replace_one(
                    {"_id": "main"},
                    {"_id": "main", **data},
                    upsert=True
                )
        except Exception as e:
            print(f"Exception occurred in GameState.save_to_db: {e}")
