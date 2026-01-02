# INSERT_YOUR_REWRITE_HERE

import copy
from app import db
from app.utils import sum_of_values
from app.utils.db_guard import db_call_guard
import json


class BalanceSheet:
    """
    Tracks the player's assets, liabilities, income, and expenses.
    Uses arrays (lists of objects with 'name' and 'amount') for each property.
    """

    def __init__(
        self,
        assets=None,
        liabilities=None,
        income=None,
        expenses=None,
        id=None,
        player=None,
    ):
        # Each field is an array of dicts
        self.assets = copy.deepcopy(assets) if assets is not None else []
        self.liabilities = copy.deepcopy(liabilities) if liabilities is not None else []
        self.income = copy.deepcopy(income) if income is not None else []
        self.expenses = copy.deepcopy(expenses) if expenses is not None else []
        self.id = id  # Optional unique identifier
        self.player = player

        if (
            player is not None
            and hasattr(player, "balancesheet")
            and player.balancesheet is not None
        ):
            loaded = self.load_from_db(id=player.balancesheet.id)

        elif player is not None:
            loaded = self.load_from_db(username=player.username)

        if player is not None and loaded:
            self.assets = loaded.assets
            self.liabilities = loaded.liabilities
            self.income = loaded.income
            self.expenses = loaded.expenses
            self.id = loaded.id
            self.player = player

    @property
    def id(self):
        return self._id if hasattr(self, "_id") else None

    @id.setter
    def id(self, value):
        self._id = value

    def _find_item(self, arr, name):
        for i, item in enumerate(arr):
            if item.get("name") == name:
                return i
        return None

    def add_asset(self, name, income, value, username=None):
        idx = self._find_item(self.assets, name)
        if idx is not None:
            self.assets[idx]["income"] += income
            self.assets[idx]["value"] += value
        else:
            self.assets.append({"name": name, "income": income, "value": value})
            if income > 0:
                self.add_all_asset_incomes_to_income(
                    {"name": name, "income": income, "value": value}, username
                )
        if username is not None:
            self.save_to_db(username)

    def add_all_asset_incomes_to_income(self, data, username):
        """
        Add the 'income' value from every asset to self.income as {name, amount}.
        Does not duplicate income entries with identical name.
        Ignores incomes <= 0. Optionally, saves to DB if username is provided.
        """
        if data["income"] > 0:
            self.income.append({"name": data["name"], "amount": data["income"]})
        else:
            pass

    def remove_asset(self, name, amount=None, username=None):
        idx = self._find_item(self.assets, name)
        if idx is not None:
            if amount is None:
                self.assets.pop(idx)
            else:
                self.assets[idx]["amount"] -= amount
                if self.assets[idx].get("amount", 0) <= 0:
                    self.assets.pop(idx)

            self.income = [i for i in self.income if i.get("name") != name]

            if username is not None:
                self.save_to_db(username)

    def add_liability(self, name, loanAmount, interestRate, username=None, **kwargs):
        """
        Add or update a liability. Accepts arbitrary additional keyword arguments,
        which are stored on the liability dict.

        Example call:
          add_liability(name, loanAmount, interestRate, username=username, **extra_fields)
        """
        idx = self._find_item(self.liabilities, name)

        if idx is not None:
            # Update existing liability, sum compatible fields, update/overwrite fields with new values if provided
            self.liabilities[idx]["loanAmount"] += loanAmount
            self.liabilities[idx]["interestRate"] = (
                interestRate  # always update to latest or TO DO: handle as needed
            )
            for k, v in kwargs.items():
                self.liabilities[idx][k] = v
            self.add_liability_expenses_to_expenses(self.liabilities[idx])
        else:
            liability = {
                "name": name,
                "loanAmount": loanAmount,
                "interestRate": interestRate,
            }
            for k, v in kwargs.items():
                liability[k] = v
            self.liabilities.append(liability)
            self.add_liability_expenses_to_expenses(liability)

        if username is not None:
            self.save_to_db(username)

    def add_liability_expenses_to_expenses(self, liability):
        """
        For a given liability with loanAmount > 0, add or update an expense item in the form {"name", "amount"}
        where amount is the amortization_calculation().payment of that liability,
        and name is the liability name.
        Defaults amortizationTerm to 1 year unless otherwise specified.
        """
        loan_amount = liability.get("loanAmount", 0)
        if loan_amount > 0:
            name = liability.get("name", "")
            interest = liability.get("interestRate", 0)
            # If amortizationTerm is stored on the liability, use that; else fall back to default
            this_term = liability.get("amortizationTerm", 1)
            comp_freq = liability.get("compoundingFrequency", "monthly")
            pay_freq = liability.get("paymentFrequency", "monthly")
            payment_info = self.amortization_calculation(
                loanAmount=loan_amount,
                interestRate=interest,
                amortizationTerm=this_term,
                compoundingFrequency=comp_freq,
                paymentFrequency=pay_freq,
            )
            payment = payment_info.get("payment", 0)
            existing = next((e for e in self.expenses if e.get("name") == name), None)
            if existing:
                existing["amount"] = payment
            else:
                self.expenses.append({"name": name, "amount": payment})

    def amortization_calculation(
        self,
        loanAmount,
        interestRate,
        amortizationTerm,
        compoundingFrequency="weekly",
        paymentFrequency="monthly",
    ):
        """
        Calculate amortization schedule/payment details.

        Args:
            loanAmount (float): Principal amount.
            interestRate (float): Annual interest rate (decimal, e.g. 0.05 for 5%).
            amortizationTerm (int|float): Amortization term in years.
            compoundingFrequency (str): One of yearly, semiannual, quarterly, monthly, weekly, daily.
            paymentFrequency (str): One of yearly, semiannual, quarterly, monthly, weekly, daily.

        Returns:
            dict: {
                "loan_amount", "interest_rate", "amortization_term",
                "compounding_frequency", "payment_frequency",
                "payment", "total_amount", "interest_payment"
            }
        """
        freq_map = {
            "yearly": 1,
            "semiannual": 2,
            "quarterly": 4,
            "monthly": 12,
            "weekly": 52,
            "daily": 365,
        }

        compPerYear = freq_map.get(compoundingFrequency, 52)
        payPerYear = freq_map.get(paymentFrequency, 12)
        n = amortizationTerm * payPerYear
        r_comp = interestRate / compPerYear
        compPerPay = compPerYear / payPerYear
        r_pay = (1 + r_comp) ** compPerPay - 1

        P = loanAmount

        if r_pay == 0:
            payment = P / n
        else:
            payment = P * (r_pay * (1 + r_pay) ** n) / ((1 + r_pay) ** n - 1)

        totalPayment = payment * n
        totalInterest = totalPayment - loanAmount

        return {
            "loan_amount": loanAmount,
            "interest_rate": interestRate,
            "amortization_term": amortizationTerm,
            "compounding_frequency": compoundingFrequency,
            "payment_frequency": paymentFrequency,
            "payment": round(payment, 1),
            "total_amount": round(totalPayment),
            "interest_payment": round(totalInterest),
        }

    def payable_liabilities(self, liabilities):
        total_payment = 0
        for liab in liabilities:
            amm = self.amortization_calculation(
                liab.get("loanAmount"),
                liab.get("interestRate"),
                liab.get("amortizationTerm"),
                liab.get("compoundingFrequency"),
                liab.get("paymentFrequency"),
            )
            total_payment += amm.get("payment")
        return {"total_payment": total_payment}

    def remove_liability(self, name, loanAmount=None, username=None):
        """
        Remove liability by name, or partially reduce by loanAmount.
        """
        idx = self._find_item(self.liabilities, name)
        if idx is not None:
            if loanAmount is None:
                self.liabilities.pop(idx)
            else:
                self.liabilities[idx]["loanAmount"] -= loanAmount
                if self.liabilities[idx]["loanAmount"] <= 0:
                    self.liabilities.pop(idx)

            self.liabilities = [i for i in self.liabilities if i.get("name") != name]

            if username is not None:
                self.save_to_db(username)

    def add_income(self, name, amount, username=None):
        idx = self._find_item(self.income, name)
        if idx is not None:
            self.income[idx]["amount"] += amount
        else:
            self.income.append({"name": name, "amount": amount})
        if username is not None:
            self.save_to_db(username)

    def remove_income(self, name, amount=None, username=None):
        idx = self._find_item(self.income, name)
        if idx is not None:
            if amount is None:
                self.income.pop(idx)
            else:
                self.income[idx]["amount"] -= amount
                if self.income[idx]["amount"] <= 0:
                    self.income.pop(idx)
            if username is not None:
                self.save_to_db(username)

    def add_expense(self, name, amount, username=None):
        idx = self._find_item(self.expenses, name)
        if idx is not None:
            self.expenses[idx]["amount"] += amount
        else:
            self.expenses.append({"name": name, "amount": amount})
        if username is not None:
            self.save_to_db(username)

    def remove_expense(self, name, amount=None, username=None):
        idx = self._find_item(self.expenses, name)
        if idx is not None:
            if amount is None:
                self.expenses.pop(idx)
            else:
                self.expenses[idx]["amount"] -= amount
                if self.expenses[idx]["amount"] <= 0:
                    self.expenses.pop(idx)
            if username is not None:
                self.save_to_db(username)

    def total_assets(self):
        return sum(item["value"] for item in self.assets)

    def total_liabilities(self):
        # Sum using "loanAmount" key, fallback to "amount" for backward compatibility
        return sum(
            item.get("loanAmount", item.get("amount", 0)) for item in self.liabilities
        )

    def total_income(self):
        return sum(item["amount"] for item in self.income)

    def total_expenses(self):
        return sum(item["amount"] for item in self.expenses)

    def net_worth(self):
        """Assets minus liabilities."""
        if self.player:
            _player = self.player.load_from_db(self.player.username).to_dict()
            _bank = db["bank-collection"]
            _bank = _bank.find_one({"customer": self.player.username})
            return (self.total_assets() + _bank["balance"]) - self.total_liabilities()
        else:
            return 0

    def cashflow(self):
        """Income minus liabilities."""
        return self.total_income() - self.total_expenses()

    def to_dict(self):
        result = {
            "assets": copy.deepcopy(self.assets),
            "liabilities": copy.deepcopy(self.liabilities),
            "income": copy.deepcopy(self.income),
            "expenses": copy.deepcopy(self.expenses),
            "net_worth": self.net_worth(),
            "cashflow": self.cashflow(),
            "prev_balancesheet": self.get_prev_balancesheet(
                getattr(self.player, "username", None)
            ),
            "id": self.id,
        }
        if self.id is not None:
            result["id"] = str(self.id)
        return result

    def get_ammotization_of_liablity(self, liability):
        return self.amortization_calculation(
            liability.get("loanAmount"),
            liability.get("interestRate"),
            liability.get("amortizationTerm"),
            liability.get("compoundingFrequency"),
            liability.get("paymentFrequency"),
        )

    # INSERT_YOUR_CODE
    def get_prev_balancesheet(self, username=None):
        """
        Fetch the previous balancesheet for the specified user (or self.player if present).

        Returns:
            dict: The previous balancesheet as a dictionary, or None if not found.
        """
        # Use self.player.username if username not provided
        target_username = username or getattr(self.player, "username", None)
        if not target_username:
            return None
        collection = db["balancesheet-collection"]
        bs = collection.find_one({"username": target_username}, sort=[("_id", -1)])
        prev_bs = bs.get("prev_balancesheet")

        if prev_bs:
            return json.loads(prev_bs)
        return None

    def update_liability_in_db(self, username, updates):
        """
        Update Liabilities in class and db
        """

        self.load_from_db(username)

        # Build a lookup from update liabilities list by name
        updates_by_name = {liab.get("name"): liab for liab in updates if "name" in liab}

        # Replace or add liabilities: build new liabilities list
        new_liabilities = []

        # Track existing names found in updates
        updated_names = set()

        # Replace existing liabilities if in updates, else keep as is
        for liab in self.liabilities:
            liab_name = liab.get("name")
            if liab_name in updates_by_name:
                # Use updated liability
                new_liabilities.append(copy.deepcopy(updates_by_name[liab_name]))
                updated_names.add(liab_name)
            else:
                # Keep original if not updated
                new_liabilities.append(copy.deepcopy(liab))

        # Add any new liabilities in updates not already present
        for name, liab in updates_by_name.items():
            if name not in updated_names and name:
                new_liabilities.append(copy.deepcopy(liab))

        self.liabilities = new_liabilities

        for liability in self.liabilities:
            if liability.get("loanAmount") <= 0:
                # Remove the liability if loanAmount <= 0, along with matching expenses
                liab_name = liability.get("name")
                self.liabilities = [
                    liab for liab in self.liabilities if liab.get("name") != liab_name
                ]
                self.expenses = [e for e in self.expenses if e.get("name") != liab_name]
                continue

            ammotization = self.get_ammotization_of_liablity(liability)
            # Remove any existing expense entry with same name as liability
            self.expenses = [
                i for i in self.expenses if i.get("name", None) != liability.get("name")
            ]
            # Only add an expense if payment value is not None
            payment = ammotization.get("payment") if ammotization else None
            if payment is not None:
                self.expenses.append({"name": liability.get("name"), "amount": payment})

        self.save_to_db(username)
        return self

    # INSERT_YOUR_CODE
    def update_assets_in_db(self, username, updates):
        """
        Update the assets of the balance sheet in memory and persist them to the database.

        Args:
            username (str): The username whose balance sheet this is.
            updates (list): List of new asset dicts to update to.

        Returns:
            self (BalanceSheet): The updated BalanceSheet instance.
        """
        self.load_from_db(username)

        # Update or add assets from updates, without deleting existing ones

        # Build a lookup for incoming assets by name
        updates_by_name = {a["name"]: a for a in updates if "name" in a}
        # Map current assets by name
        current_assets_by_name = {a.get("name"): a for a in self.assets if "name" in a}

        # Update existing assets or add new ones
        for name, updated_asset in updates_by_name.items():
            if name in current_assets_by_name:
                current_assets_by_name[name].update(updated_asset)
            else:
                self.assets.append(updated_asset)

        # No deletion: assets not in updates are preserved

        self.save_to_db(username)
        return self

    def save_to_db(self, username):
        """
        Save the current balance sheet to the database under the given username.
        If a record exists, update it; otherwise, insert a new one.
        """

        with db_call_guard("BalanceSheet.save_to_db"):
            collection = db["balancesheet-collection"]
            data = self.to_dict()
            data.pop("prev_balancesheet", None)

            prev_balancesheet = collection.find_one({"username": username})

            current_cashflow = data.get("cashflow", 0)
            prev_cashflow = prev_balancesheet.get("cashflow", 0)

            if not prev_balancesheet or (current_cashflow != prev_cashflow):
                if not prev_balancesheet:
                    prev_balancesheet = json.dumps(data)
                prev_balancesheet = {**prev_balancesheet}
                prev_balancesheet.pop("_id", None)
                prev_balancesheet.pop("prev_balancesheet", None)
                data["prev_balancesheet"] = json.dumps(prev_balancesheet)

            data["username"] = username
            # Only use _id if it exists
            if self.id is not None:
                data["_id"] = self.id
            collection.update_one({"username": username}, {"$set": data}, upsert=True)
            # After upsert, assign _id if necessary
            if self.id is None:
                doc = collection.find_one({"username": username})
                if doc and "_id" in doc:
                    self.id = doc["_id"]

    @classmethod
    def load_from_db(cls, username=None, id=None):
        """
        Load a balance sheet from the database by username or id.
        Returns a BalanceSheet instance, or None if not found.
        """

        with db_call_guard("BalanceSheet.load_from_db"):
            collection = db["balancesheet-collection"]
            query = {}
            if id is not None:
                # If id is provided, search by _id
                query["_id"] = id
            elif username is not None:
                query["username"] = username
            else:
                raise ValueError(
                    "Either 'username' or 'id' must be provided to load BalanceSheet."
                )

            doc = collection.find_one(query)
            if doc:
                _id = doc.pop("_id", None)
                doc.pop("username", None)
                instance = cls.from_dict(doc)
                instance.id = _id
                return instance
        return None

    @classmethod
    def from_dict(cls, d):
        def fix_array(arr):
            if arr is None:
                return []
            if isinstance(arr, dict):
                return [dict(item) for item in arr.values()]
            if isinstance(arr, list):
                return [dict(item) for item in arr]
            return []

        instance = cls(
            assets=fix_array(d.get("assets", [])),
            liabilities=d.get("liabilities", []),
            income=fix_array(d.get("income", [])),
            expenses=fix_array(d.get("expenses", [])),
            id=d.get(
                "id", None
            ),  # Accept id from dict if available (as string or ObjectId)
        )
        return instance
