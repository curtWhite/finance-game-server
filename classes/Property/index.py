from app import db
from app.utils.db_guard import db_call_guard
 # Update existing document
# Ensure _id is a valid ObjectId if it isn't already (can fix common 'not updating' MongoDB bug)
from bson import ObjectId

property_collection = db["property-collection"]


class Property:
    def __init__(self, player):
        self.title = None
        self.description = None
        self.location = None
        self.zoning = None
        self.crimeIndex = None
        self.appreciationRate = None
        self.cost = None
        self.downPayment = None
        self.bankPayment = None
        self.credit = None
        self.income = 0
        self.cashFlow = None
        self.roi = None
        self.icon = None
        self.pricePerM2 = None
        self.landSize = None
        self.type = None  # maps from 'property_type'/'type'
        self.legalFees = None

        # legacy field mapping support:
        self.property_type = None  # alias for 'type'
        self.price = None  # may be filled from 'cost'

        self._player = player
        self._id = None  # MongoDB document ID

    # ------------------- Getters and Setters ------------------- #

    def get_title(self):
        return self.title

    def set_title(self, value):
        self.title = value

    def get_description(self):
        return self.description

    def set_description(self, value):
        self.description = value

    def get_location(self):
        return self.location

    def set_location(self, value):
        self.location = value

    def get_zoning(self):
        return self.zoning

    def set_zoning(self, value):
        self.zoning = value

    def get_crime_index(self):
        return self.crimeIndex

    def set_crime_index(self, value):
        self.crimeIndex = value

    def get_appreciation_rate(self):
        return self.appreciationRate

    def set_appreciation_rate(self, value):
        self.appreciationRate = value

    def get_cost(self):
        return self.cost

    def set_cost(self, value):
        self.cost = value

    def get_down_payment(self):
        return self.downPayment

    def set_down_payment(self, value):
        self.downPayment = value

    def get_bank_payment(self):
        return self.bankPayment

    def set_bank_payment(self, value):
        self.bankPayment = value

    def get_credit(self):
        return self.credit

    def set_credit(self, value):
        self.credit = value

    def get_income(self):
        return self.income

    def set_income(self, value):
        self.income = value

    def get_cash_flow(self):
        return self.cashFlow

    def set_cash_flow(self, value):
        self.cashFlow = value

    def get_roi(self):
        return self.roi

    def set_roi(self, value):
        self.roi = value

    def get_icon(self):
        return self.icon

    def set_icon(self, value):
        self.icon = value

    def get_price_per_m2(self):
        return self.pricePerM2

    def set_price_per_m2(self, value):
        self.pricePerM2 = value

    def get_land_size(self):
        return self.landSize

    def set_land_size(self, value):
        self.landSize = value

    def get_type(self):
        return self.type

    def set_type(self, value):
        self.type = value

    def get_legal_fees(self):
        return self.legalFees

    def set_legal_fees(self, value):
        self.legalFees = value

    # Also for backward compatibility / convenience
    def get_property_type(self):
        return self.type if self.type is not None else self.property_type

    def set_property_type(self, value):
        self.type = value
        self.property_type = value

    def get_price(self):
        # 'price' maps to 'cost' if not set
        return self.cost if self.cost is not None else self.price

    def set_price(self, value):
        self.cost = value
        self.price = value

    # ------------------- DB methods ------------------- #

    def to_dict(self):
        """Serialize the property to a dict for MongoDB and JSON"""
        return {
            "player_id": getattr(self._player, "_id", None),
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "zoning": self.zoning,
            "crimeIndex": self.crimeIndex,
            "appreciationRate": self.appreciationRate,
            "cost": self.cost,
            "downPayment": self.downPayment,
            "bankPayment": self.bankPayment,
            "credit": self.credit,
            "income": self.income,
            "cashFlow": self.cashFlow,
            "roi": self.roi,
            "icon": self.icon,
            "pricePerM2": self.pricePerM2,
            "landSize": self.landSize,
            "type": self.type,
            "legalFees": self.legalFees,
            # legacy support for expected fields (optional)
            "property_type": self.type if self.type else self.property_type,
            "price": self.price if self.price is not None else self.cost,
        }

    def from_dict(self, data):
        """Load property attributes from a dictionary (e.g. db record)"""
        self.title = data.get("title")
        self.description = data.get("description")
        self.location = data.get("location")
        self.zoning = data.get("zoning")
        self.crimeIndex = data.get("crimeIndex")
        self.appreciationRate = data.get("appreciationRate")
        self.cost = data.get("cost")
        self.downPayment = data.get("downPayment")
        self.bankPayment = data.get("bankPayment")
        self.credit = data.get("credit")
        self.income = data.get("income", 0)
        self.cashFlow = data.get("cashFlow")
        self.roi = data.get("roi")
        self.icon = data.get("icon")
        self.pricePerM2 = data.get("pricePerM2")
        self.landSize = data.get("landSize")
        self.type = data.get("type")
        self.legalFees = data.get("legalFees")
        # backwards/JSON legacy
        self.property_type = data.get("property_type", self.type)
        self.price = data.get("price", self.cost)
        self._id = data.get("_id", None)

    def save_to_db(self):
        """Save the property to the database (insert or update)"""
        try:
            with db_call_guard("Property.save_to_db"):
                data = self.to_dict()
               
                if self._id:
                    _id = self._id
                    if _id and not isinstance(_id, ObjectId):
                        try:
                            _id = ObjectId(_id)
                        except Exception:
                            pass  # If it can't be converted, use as-is
                    
                    result = property_collection.update_one({"_id": _id}, {"$set": data})
                    if result.modified_count == 0:
                        print(f"Property with _id {self._id} was not updated (no changes or not found).")
                else:
                    # Insert new document
                    result = property_collection.insert_one(data)
                    self._id = result.inserted_id
        except Exception as e:
            print(f"Exception occurred in Property.save_to_db: {e}")
            raise

    def apply_appreciation(self, years=1, update_balancesheet=True):
        """
        Updates the cost/price of the property instance by applying appreciation or depreciation
        over a number of years based on appreciationRate. Optionally updates the associated asset
        in the player's balancesheet as well.

        Args:
            years (float or int): Number of years to apply appreciation for.
            update_balancesheet (bool): If True, also update the asset value in the balancesheet.

        Returns:
            float: The new cost/price of the property after appreciation/depreciation.
        """
        try:
            appreciation_rate = self.appreciationRate
            if appreciation_rate is None:
                # If rate not set, nothing changes.
                return self.cost if self.cost is not None else self.price

            base_cost = self.price
            if base_cost is None:
                return None

            # Appreciation rate can be e.g. 0.03 (3%) or 3 ("3%")
            rate = appreciation_rate
            if isinstance(rate, str):
                rate = rate.strip()
                if rate.endswith("%"):
                    rate = float(rate[:-1]) / 100.0
                else:
                    rate = float(rate)
            # If someone entered 3 for 3%, treat as 0.03
            if rate > 1:
                rate = rate / 100.0

            years = float(years)
            new_cost = base_cost * ((1 + rate) ** years)
            # Update the property value
            self.price = new_cost

            print("NEW PROPERTY VALUE :", self.price)

            # Update the player's balancesheet asset value if requested
            if (
                update_balancesheet
                and hasattr(self, "_player")
                and hasattr(self._player, "balancesheet")
            ):
                asset_name = self.title
                balancesheet = self._player.balancesheet
                updated = False
                # Find the asset by name/title and update its value
                for asset in getattr(balancesheet, "assets", []):
                    if asset.get("name") == asset_name:
                        asset["value"] = new_cost
                        updated = True
                        break
                if updated:
                    try:
                        balancesheet.save_to_db(self._player.username)
                    except Exception as e:
                        print(
                            f"Failed to save balancesheet with appreciated property value: {e}"
                        )
                else:
                    # Optionally: add new asset if not present
                    pass  # Do nothing if asset not found
            return new_cost
        except Exception as e:
            print(f"Exception in apply_appreciation: {e}")
            return self.cost if self.cost is not None else self.price

    def load_all_owned_properties(self):
        """
        Return a list of all properties owned by the player (_player).
        Each element is a property dictionary.
        """
        player_id = getattr(self._player, "_id", None)
        if not player_id:
            return []

        try:
            cursor = property_collection.find({"player_id": player_id})
            properties = []
            for doc in cursor:
                prop = self.__class__(self._player)
                prop.from_dict(doc)
                prop._id = doc.get("_id")
                properties.append(prop.to_json())
            return properties
        except Exception as e:
            print(f"Exception in load_all_owned_properties: {e}")
            return []

    def load_from_db(self):
        """Load this property from the db using player's ID"""
        player_id = getattr(self._player, "_id", None)
        if not player_id:
            return False
        doc = property_collection.find_one({"player_id": player_id})
        if doc:
            self.from_dict(doc)
            self._id = doc.get("_id")
            return True
        return False

    def to_json(self):
        """Return a json-serializable dictionary representation"""
        property_data = self.to_dict()
        if self._id:
            # If _id is a bson.ObjectId, convert to string
            property_data["id"] = str(self._id)
        return property_data
