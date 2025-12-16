from app import db
from app.utils.db_guard import db_call_guard
from classes.BalanceSheet.index import BalanceSheet
# from classes.Job.index import Job

BASE_TOTAL_TIME = 720


class Player:
    def __init__(
        self,
        username=None,
        id=None,
        score=0,
        level=1,
        total_time=None,
        time_slots=None,
        job=None,
        properties=None,
        crypto=None,
        commodities=None,
        business=None,
        stock=None,
        bank=None,
        experience=0,
        energy=0,
        qualifications=None,  # New property added for qualifications
        balancesheet=None,  # New property: BalanceSheet instance
    ):
        self.username = username
        self.score = score
        self.level = level
        self.total_time = total_time if total_time is not None else BASE_TOTAL_TIME
        self.time_slots = time_slots if time_slots is not None else {}
        self.job = job
        self.properties = properties if properties is not None else []
        self.crypto = crypto if crypto is not None else []
        self.commodities = commodities if commodities is not None else []
        self.business = business if business is not None else []
        self.stock = stock if stock is not None else []
        self._id = id
        self.bank = bank
        self.experience = experience
        self.energy = energy
        self.qualifications = (
            qualifications if qualifications is not None else []
        )  # Initialize qualifications

        # Initialize BalanceSheet: use provided or load from DB or new
        if balancesheet is not None:
            self.balancesheet = balancesheet
        elif username is not None:
            loaded_bs = BalanceSheet.load_from_db(username)
            if loaded_bs is not None:
                self.balancesheet = loaded_bs
            else:
                self.balancesheet = BalanceSheet()
        else:
            self.balancesheet = BalanceSheet()

        if not id and username is not None:
            self.get_player(username=username)

    def increase_score(self, points):
        if not isinstance(points, (int, float)):
            raise ValueError("Points must be an integer or float.")
        self.score += points
        self.save_to_db()

    def increase_experience(self, exp_points):
        if not isinstance(exp_points, (int, float)):
            raise ValueError("Experience points must be an integer or float.")
        self.experience += exp_points
        self.save_to_db()

    def assign_time_slot(self, key=None, value=None):
        if key is None:
            raise ValueError("Must provide time slot key")

        if value is None or value <= 0:
            raise ValueError("Not positive time value provided")

        time_sum = value
        if time_sum > BASE_TOTAL_TIME:
            raise ValueError("Not enough available time for this assignment")

        self.total_time = BASE_TOTAL_TIME - time_sum
        self.time_slots[key] = value
        self.save_to_db()

    def remove_allocated_time(self, key):
        """
        Remove an allocated time slot by key from the player's time_slots.
        Adds the removed time back to total_time (up to BASE_TOTAL_TIME).
        """
        if key in self.time_slots:
            removed_time = self.time_slots.pop(key)
            self.total_time = min(self.total_time + removed_time, BASE_TOTAL_TIME)
            self.save_to_db()
            return removed_time
        return 0

    def add_property(self, property_item):
        self.properties.append(property_item)
        self.save_to_db()

    def add_crypto(self, crypto_item):
        self.crypto.append(crypto_item)
        self.save_to_db()

    def add_commodity(self, commodity_item):
        self.commodities.append(commodity_item)
        self.save_to_db()

    def add_business(self, business_item):
        self.business.append(business_item)
        self.save_to_db()

    def add_stock(self, stock_item):
        self.stock.append(stock_item)
        self.save_to_db()

    def remove_property(self, property_item):
        if property_item in self.properties:
            self.properties.remove(property_item)
            self.save_to_db()

    def remove_crypto(self, crypto_item):
        if crypto_item in self.crypto:
            self.crypto.remove(crypto_item)
            self.save_to_db()

    def remove_commodity(self, commodity_item):
        if commodity_item in self.commodities:
            self.commodities.remove(commodity_item)
            self.save_to_db()

    def remove_business(self, business_item):
        if business_item in self.business:
            self.business.remove(business_item)
            self.save_to_db()

    def remove_stock(self, stock_item):
        if stock_item in self.stock:
            self.stock.remove(stock_item)
            self.save_to_db()

    def is_hired(self):
        return self.job is not None

    def level_up(self):
        self.level += 1
        self.save_to_db()

    def to_dict(self):
        # Adding all relevant properties for saving/loading, including experience, energy, bank, qualifications, and balancesheet as dict
        return {
            "id": str(self._id),
            "username": self.username,
            "score": self.score,
            "level": self.level,
            "total_time": self.total_time,
            "time_slots": self.time_slots,
            "job": self.job,
            "properties": self.properties,
            "crypto": self.crypto,
            "commodities": self.commodities,
            "business": self.business,
            "stock": self.stock,
            "bank": self.bank,
            "experience": self.experience,
            "energy": self.energy,
            "qualifications": self.qualifications,
            "balancesheet": self.balancesheet.to_dict()
            if hasattr(self.balancesheet, "id")
            else self.balancesheet,
        }

    def save_to_db(self, skip_balancesheet=False):
        """
        Save the player to the users collection in the provided db.
        If a user with the same username already exists, replace/overwrite it.
        Also saves the balancesheet to its own collection.
        """
        # INSERT_YOUR_CODE
        import inspect

        with db_call_guard("Player.save_to_db"):
            frame = inspect.currentframe()
            caller_frame = frame.f_back
            caller_name = caller_frame.f_code.co_name if caller_frame else None
            print(
                f" >> save_to_db was called by: {caller_name} -> ",
                self.balancesheet.liabilities[1],
            )

            data = self.to_dict()

            # Always store balancesheet id as a string, or fallback to embedded id/val
            balancesheet_id = getattr(self.balancesheet, "id", None)
            bs_value = data.get("balancesheet")
            if balancesheet_id is not None:
                data["balancesheet"] = str(balancesheet_id)
            elif isinstance(bs_value, dict):
                data["balancesheet"] = bs_value.get("id")
            else:
                data["balancesheet"] = bs_value

            if hasattr(self.bank, "id"):
                data["bank"] = self.bank.id
            elif isinstance(data["bank"], str):
                data["bank"] = self.bank

            users_collection = db["users-collection"]
            users_collection.replace_one({"username": self.username}, data, upsert=True)
            # Save balancesheet in its own document/collection as well, under the username
            if (
                not skip_balancesheet
                and self.balancesheet is not None
                and self.username is not None
            ):
                self.balancesheet.save_to_db(self.username)

    @classmethod
    def create_and_save(
        cls,
        username,
        score=0,
        level=1,
        bank=None,
        experience=0,
        energy=0,
        qualifications=None,
        balancesheet=None,
    ):
        """
        Convenience method to create a Player and insert into the users collection.
        """
        player = cls(
            username,
            score,
            level,
            bank=bank,
            experience=experience,
            energy=energy,
            qualifications=qualifications,
            balancesheet=balancesheet,
        )
        player.save_to_db()
        return player

    @classmethod
    def load_from_db(cls, username):
        """
        Loads a player from database by username.
        Returns a Player object or None if not found.
        """
        with db_call_guard("Player.load_from_db"):
            users_collection = db["users-collection"]
            player_data = users_collection.find_one({"username": username})
            if player_data:
                # Always load the balancesheet with the player class.
                balancesheet = BalanceSheet.load_from_db(username=username) or None

                return cls(
                    username=player_data.get("username"),
                    score=player_data.get("score", 0),
                    level=player_data.get("level", 1),
                    total_time=player_data.get("total_time", BASE_TOTAL_TIME),
                    time_slots=player_data.get("time_slots", {}),
                    job=player_data.get(
                        "job", {}
                    ),  # Job object needs more context to reconstruct
                    properties=player_data.get("properties", []),
                    crypto=player_data.get("crypto", []),
                    commodities=player_data.get("commodities", []),
                    business=player_data.get("business", []),
                    stock=player_data.get("stock", []),
                    bank=player_data.get("bank", None),
                    id=str(player_data.get("_id"))
                    if player_data.get("_id") is not None
                    else None,
                    experience=player_data.get("experience", 0),
                    energy=player_data.get("energy", 0),
                    qualifications=player_data.get(
                        "qualifications", []
                    ),  # Load qualifications
                    balancesheet=balancesheet,
                )
        return None

    # INSERT_YOUR_CODE
    @classmethod
    def from_json(cls, data):
        """
        Creates a Player instance from a JSON-like dict.
        Any missing field will be filled with a default value.
        """
        if "balancesheet" in data and data["balancesheet"] is not None:
            bs = BalanceSheet.from_dict(data["balancesheet"]).id
        elif "username" in data and data["username"] is not None:
            bs = BalanceSheet.load_from_db(data["username"]).id or None
        else:
            bs = None
        return cls(
            username=data.get("username"),
            id=data.get("id", None),
            score=data.get("score", 0),
            level=data.get("level", 1),
            total_time=data.get("total_time", BASE_TOTAL_TIME),
            time_slots=data.get("time_slots", {}),
            job=data.get("job", None),
            properties=data.get("properties", []),
            crypto=data.get("crypto", []),
            commodities=data.get("commodities", []),
            business=data.get("business", []),
            stock=data.get("stock", []),
            bank=data.get("bank", None),
            experience=data.get("experience", 0),
            energy=data.get("energy", 0),
            qualifications=data.get("qualifications", []),
            balancesheet=bs,
        )

    def apply_for_job(self, job):
        """
        Allows a player to apply for a job.
        If not already hired, assign the job and save to DB.
        """
        if self.is_hired():
            raise ValueError("Player is already hired for a job.")
        self.job = job
        self.save_to_db()

    @classmethod
    def get_player(cls, username):
        """
        Fetch a player from the DB by username.
        Returns a Player instance if found, otherwise None.
        """
        return cls.load_from_db(username)
