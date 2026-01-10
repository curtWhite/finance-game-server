from app import db
from app.utils.db_guard import db_call_guard
from bson import ObjectId
import random
from datetime import datetime, timedelta
import copy

lotto_collection = db["lotto-collection"]


class Lotto:
    """
    Lotto Office class for managing lottery tickets.
    Players can submit tickets with numbers, and results are processed after a delay.
    """
    
    # Default delay in hours (can be configured)
    DEFAULT_RESULT_DELAY_HOURS = 1
    
    def __init__(self, player=None, ticket_id=None):
        self._player = player
        self._id = ticket_id
        
        # Ticket properties
        self.username = None
        self.numbers = []  # List of numbers chosen by player
        self.winning_numbers = []  # Winning numbers (drawn after delay)
        self.ticket_cost = 0  # Cost to purchase ticket
        self.prize_amount = 0  # Prize won (0 if lost)
        self.status = "pending"  # pending, won, lost
        self.submitted_at = None  # When ticket was submitted
        self.result_at = None  # When result should be available
        self.processed_at = None  # When result was actually processed
        
        # Load from DB if ticket_id provided
        if ticket_id:
            self.load_from_db(ticket_id)
    
    def submit_ticket(self, numbers, ticket_cost=10, result_delay_seconds=None):
        """
        Submit a lottery ticket with chosen numbers.

        Args:
            numbers: List of numbers chosen by player (e.g., [1, 5, 10, 15, 20, 25])
            ticket_cost: Cost to purchase the ticket (default: 10)
            result_delay_seconds: Seconds to wait before processing result (default: DEFAULT_RESULT_DELAY_HOURS * 3600)

        Returns:
            dict: Ticket information
        """
        if not self._player:
            raise ValueError("Player is required to submit a ticket")

        if not numbers or not isinstance(numbers, list):
            raise ValueError("Numbers must be a non-empty list")

        if len(numbers) < 1:
            raise ValueError("At least one number is required")

        if ticket_cost <= 0:
            raise ValueError("Ticket cost must be positive")

        # Set delay seconds (default or provided)
        if result_delay_seconds is not None:
            try:
                delay_seconds = float(result_delay_seconds)
                if delay_seconds <= 0:
                    raise ValueError
            except Exception:
                raise ValueError("result_delay_seconds must be a positive number")
        else:
            delay_seconds = self.DEFAULT_RESULT_DELAY_HOURS * 3600

        # Initialize ticket
        self.username = self._player.username
        self.numbers = sorted([int(n) for n in numbers])  # Sort numbers for consistency
        self.ticket_cost = float(ticket_cost)
        self.status = "pending"
        self.submitted_at = datetime.utcnow()
        self.result_at = self.submitted_at + timedelta(seconds=delay_seconds)
        self.winning_numbers = []
        self.prize_amount = 0
        self.processed_at = None

        # Save to database
        self.save_to_db()
        
        return self.to_dict()
    
    def check_winning_condition(self, winning_numbers=None):
        """
        Check if the ticket is a winner based on matching numbers.
        
        Args:
            winning_numbers: Optional winning numbers (if None, generates random)
        
        Returns:
            dict: Result with status, matches, and prize amount
        """
        if not self.numbers:
            raise ValueError("Ticket has no numbers to check")
        
        # Generate or use provided winning numbers
        if winning_numbers is None:
            max_num = max(self.numbers) if self.numbers else 36
            num_count = len(self.numbers)
            winning_numbers = sorted(random.sample(range(1, max(max_num, 36) + 1), num_count))
        
        self.winning_numbers = winning_numbers

        # Count matching numbers
        matches = len(set(self.numbers) & set(winning_numbers))
        total_numbers = len(self.numbers)

        # Determine prize based on match percentage
        match_percentage = matches / total_numbers if total_numbers > 0 else 0

        # --- Modification for winning odds based on winning_numbers length ---
        # If the lotto is using 6 numbers, odds of winning are 4x higher (i.e., thresholds 4x easier)
        adjustment = 1.0
        # if len(winning_numbers) == 6:
        #     adjustment = 1.0
        # elif len(winning_numbers) <= 5:
        #     adjustment = 4.0
        # For other lengths, no specific adjustment:
        # (could generalize but not specified)

        
        if match_percentage >= (1.0 / adjustment):  # All numbers match (jackpot, possibly easier)
            prize_multiplier = 1000
            self.status = "won"
        elif match_percentage >= (0.9 / adjustment):
            prize_multiplier = 500
            self.status = "won"
        elif match_percentage >= (0.8 / adjustment):
            prize_multiplier = 250
            self.status = "won"
        elif match_percentage >= (0.7 / adjustment):
            prize_multiplier = 125
            self.status = "won"
        elif match_percentage >= (0.6 / adjustment):
            prize_multiplier = 62.5
            self.status = "won"
        elif match_percentage >= (0.5 / adjustment):
            prize_multiplier = 30
            self.status = "won"
        elif match_percentage >= (0.4 / adjustment):
            prize_multiplier = 15
            self.status = "won"
        elif match_percentage >= (0.3 / adjustment):
            prize_multiplier = 5
            self.status = "won"
        else:  # Less than threshold
            prize_multiplier = 0
            self.status = "lost"

        # Calculate prize amount
        self.prize_amount = self.ticket_cost * prize_multiplier

        self.processed_at = datetime.utcnow()

        # Save updated ticket
        self.save_to_db()

        return {
            "status": self.status,
            "matches": matches,
            "total_numbers": total_numbers,
            "match_percentage": match_percentage,
            "prize_amount": self.prize_amount,
            "winning_numbers": self.winning_numbers,
            "player_numbers": self.numbers
        }
    
    def to_dict(self):
        """Serialize the ticket to a dict for MongoDB and JSON"""
        def format_datetime(dt):
            """Helper to format datetime to ISO string"""
            if dt is None:
                return None
            if isinstance(dt, str):
                return dt
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)
        
        return {
            "id": str(self._id) if self._id else None,
            "username": self.username,
            "numbers": self.numbers,
            "winning_numbers": self.winning_numbers,
            "ticket_cost": self.ticket_cost,
            "prize_amount": self.prize_amount,
            "status": self.status,
            "submitted_at": format_datetime(self.submitted_at),
            "result_at": format_datetime(self.result_at),
            "processed_at": format_datetime(self.processed_at),
        }
    
    def from_dict(self, data):
        """Load ticket attributes from a dictionary (e.g. db record)"""
        self.username = data.get("username")
        self.numbers = data.get("numbers", [])
        self.winning_numbers = data.get("winning_numbers", [])
        self.ticket_cost = data.get("ticket_cost", 0)
        self.prize_amount = data.get("prize_amount", 0)
        self.status = data.get("status", "pending")
        
        # Parse datetime strings
        def parse_datetime(dt_str):
            """Helper to parse datetime from string"""
            if not dt_str:
                return None
            if isinstance(dt_str, datetime):
                return dt_str
            try:
                    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # Fallback for older Python versions
                try:
                    return datetime.strptime(dt_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    return datetime.strptime(dt_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
        
        if data.get("submitted_at"):
            self.submitted_at = parse_datetime(data["submitted_at"])
        if data.get("result_at"):
            self.result_at = parse_datetime(data["result_at"])
        if data.get("processed_at"):
            self.processed_at = parse_datetime(data["processed_at"])
        
        self._id = data.get("_id", None)
    
    def save_to_db(self):
        """Save the ticket to the database (insert or update)"""
        try:
            with db_call_guard("Lotto.save_to_db"):
                data = self.to_dict()
                # Remove id from data for MongoDB operations
                ticket_id = data.pop("id", None)
                
                if ticket_id:
                    _id = ticket_id
                    if _id and not isinstance(_id, ObjectId):
                        try:
                            _id = ObjectId(_id)
                        except Exception:
                            pass
                    
                    result = lotto_collection.update_one({"_id": _id}, {"$set": data})
                    if result.modified_count == 0:
                        print(f"Lotto ticket with _id {self._id} was not updated (no changes or not found).")
                else:
                    # Insert new document
                    result = lotto_collection.insert_one(data)
                    self._id = result.inserted_id
        except Exception as e:
            print(f"Exception occurred in Lotto.save_to_db: {e}")
            raise
    
    @classmethod
    def load_from_db(cls, ticket_id, player=None):
        """
        Load a ticket from the database by ticket_id.
        
        Args:
            ticket_id: MongoDB _id of the ticket
            player: Optional player instance
        
        Returns:
            Lotto instance or None if not found
        """
        try:
            with db_call_guard("Lotto.load_from_db"):
                if not isinstance(ticket_id, ObjectId):
                    try:
                        ticket_id = ObjectId(ticket_id)
                    except Exception:
                        return None
                
                doc = lotto_collection.find_one({"_id": ticket_id})
                if doc:
                    instance = cls(player=player, ticket_id=None)
                    instance.from_dict(doc)
                    instance._id = doc.get("_id")
                    return instance
        except Exception as e:
            print(f"Exception occurred in Lotto.load_from_db: {e}")
        return None
    
    @classmethod
    def load_player_tickets(cls, username, status=None):
        """
        Load all tickets for a player, optionally filtered by status.
        
        Args:
            username: Player username
            status: Optional status filter ("pending", "won", "lost")
        
        Returns:
            List of Lotto ticket dictionaries
        """
        try:
            with db_call_guard("Lotto.load_player_tickets"):
                query = {"username": username}
                if status:
                    query["status"] = status
                
                cursor = lotto_collection.find(query).sort("submitted_at", -1)
                tickets = []
                for doc in cursor:
                    ticket = cls()
                    ticket.from_dict(doc)
                    ticket._id = doc.get("_id")
                    tickets.append(ticket.to_dict())
                return tickets
        except Exception as e:
            print(f"Exception occurred in Lotto.load_player_tickets: {e}")
            return []
    
    @classmethod
    def load_pending_tickets(cls):
        """
        Load all pending tickets that are ready to be processed (result_at <= now).
        
        Returns:
            List of Lotto instances
        """
        try:
            with db_call_guard("Lotto.load_pending_tickets"):
                now = datetime.utcnow()
                now_str = now.isoformat()
                # Query for pending tickets where result_at is less than or equal to now
                # Handle both string and datetime formats
                cursor = lotto_collection.find({
                    "status": "pending",
                    "$or": [
                        {"result_at": {"$lte": now_str}},
                        {"result_at": {"$lte": now}}
                    ]
                })
                
                tickets = []
                for doc in cursor:
                    ticket = cls()
                    ticket.from_dict(doc)
                    ticket._id = doc.get("_id")
                    # Double-check the result_at time in case of timezone issues
                    if ticket.result_at:
                        if isinstance(ticket.result_at, str):
                            ticket.result_at = datetime.fromisoformat(ticket.result_at.replace('Z', '+00:00'))
                        if ticket.result_at <= now:
                            tickets.append(ticket)
                    else:
                        # If no result_at, consider it ready (shouldn't happen, but handle it)
                        tickets.append(ticket)
                return tickets
        except Exception as e:
            print(f"Exception occurred in Lotto.load_pending_tickets: {e}")
            return []

