import json
from app import db
from app.utils import sum_of_values

bank_collection = db["bank-collection"]
bank_logs_collection = db["bank-logs-collection"]


class Bank:
    def __init__(self, initial_balance: float = 1000, customer=None):
        self._player = customer
        self.late_payments = 0  # Default property; will load actual from DB if present
        self.bank = bank_collection.find_one(
            {"customerId": getattr(self._player, "id", None)}
        )
        # Load logs from bank ID if available
        if self.bank and "_id" in self.bank:
            logs_doc = bank_logs_collection.find_one({"bankId": self.bank["_id"]})
            self.bank_logs = logs_doc["logs"] if logs_doc and "logs" in logs_doc else []
        else:
            self.bank_logs = []
        self._operation_logs = self.bank_logs
        self._balance = (
            self.bank["balance"]
            if self.bank and "balance" in self.bank
            else initial_balance
        )
        # Load late_payments from DB if present (make sure load_bank_data handles it)
        self.load_bank_data()

    def _create_new_account(self):
        data = {
            "balance": self._balance,
            "late_payments": self.late_payments,
            "Banklog": self._operation_logs,
            "customerId": getattr(self._player, "id", None),
            "customerName": f"{getattr(self._player, 'firstName', '')} {getattr(self._player, 'lastName', '')}".strip(),
            # 'createdAt' could be added as datetime.utcnow().isoformat() if needed
        }
        return data

    def _log_operation(self, entry: dict):
        log_entry = entry.copy()
        from datetime import datetime

        log_entry["date"] = datetime.utcnow()
        self._operation_logs.append(log_entry)
        self._operation_logs = self._operation_logs[-20:]

    def deposit(self, amount: float, sender=None, message=None):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self._balance += amount

        self._log_operation(
            {
                "type": "deposit",
                "amount": amount,
                "balanceAfter": self._balance,
                "from": sender,
                "message": message,
            }
        )
        self.save_bank_data()

    def withdraw(self, amount: float):
        if amount <= 0:
            raise ValueError("Withdraw amount must be positive")
        if amount > self._balance:
            raise ValueError("Insufficient funds for withdrawal")
        self._balance -= amount
        self._log_operation(
            {"type": "withdraw", "amount": amount, "balanceAfter": self._balance}
        )
        self.save_bank_data()

    def make_payment(self, amount: float, recipient: str, late_payment: bool = None):
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        if amount > self._balance:
            raise ValueError("Insufficient funds for payment")
        self._balance -= amount

        if late_payment is not None:
            if late_payment:
                self.late_payments += 1
            else:
                self.late_payments -= 1

        self._log_operation(
            {
                "type": "payment",
                "amount": amount,
                "to": recipient,
                "balanceAfter": self._balance,
            }
        )
        self.save_bank_data()

    def get_logs(self):
        return self._operation_logs[:]

    def get_balance(self) -> float:
        return self._balance

    def get_late_payments(self) -> int:
        return self.late_payments

    def set_late_payments(self, value: int):
        try:
            self.late_payments = int(value)
        except Exception:
            self.late_payments = 0

    @classmethod
    def create_account(cls, initial_balance: float = 0):
        return cls(initial_balance)

    def delete_account(self):
        self._balance = 0
        self._operation_logs = []
        self.late_payments = 0
        customer_id = getattr(self._player, "id", None)
        if customer_id:
            # Delete the bank account document
            bank_collection.delete_one({"customerId": customer_id})
            # Delete any associated logs
            bank_logs_collection.delete_many(
                {"bankId": self.bank["_id"]}
            ) if self.bank and "_id" in self.bank else None
            self.bank = None
            self.bank_logs = []
    
    def required_credit_score(self, loan_amount, bs):
        loan_ratio = loan_amount / max(sum_of_values(bs.income, "amount"), 1)

        if loan_ratio < 0.1:
            return 500   # very small loan
        elif loan_ratio < 0.3:
            return 580
        elif loan_ratio < 0.6:
            return 650
        elif loan_ratio < 1.0:
            return 700
        else:
            return 760   # large / risky loan

    def request_loan_from_bank(
        self, amount=None, interest_rate=None, term_months=None, reason=None, bs=None
    ):
        """
        Handles a loan request, adds the loan as a liability to the player's balancesheet,
        and increases the player's bank account by the loan amount.

        If arguments are not provided, raises an error. (API expects to use the explicit arguments.)

        Returns a dict summarizing the operation.
        """

        # Determine if the player has enough credit score to request a loan
        if bs is None:
            bs = getattr(self._player, "balancesheet", None)
            if bs is None:
                raise ValueError("Could not find balancesheet for player.")
        print(f" >> request_loan_from_bank: bs => {bs.player.username} -----------------------------------------")
        credit_score = self.calculate_credit_score(bs)
        required_credit_score = self.required_credit_score(amount, bs)
        if credit_score < required_credit_score:
            raise ValueError(f"Player has insufficient credit score to request a loan. Required: {required_credit_score}, Current: {credit_score}")

        if amount is None or interest_rate is None or term_months is None:
            raise ValueError(
                "amount, interest_rate, and term_months are required to request a loan."
            )

        # Validation
        try:
            amount = float(amount)
            interest_rate = float(interest_rate)
            term_months = int(term_months)
            if amount <= 0 or interest_rate < 0 or term_months <= 0:
                raise ValueError()
        except Exception:
            raise ValueError("Invalid values for loan request.")

        # Add funds to balance
        print(
            ">>>>>>>>>>>>> BALANCE BEFORE LOAN: ",
            self._balance,
            " >> LOAN AMOUNT => ",
            amount,
        )
        self._balance += amount

        # Add liability to player's balancesheet
        player = getattr(self, "_player", None)
        if player is None:
            raise ValueError(
                "Bank instance is not associated with a player for liability creation."
            )

        bs = getattr(player, "balancesheet", None)
        if bs is None:
            # Try loading balancesheet dynamically
            if hasattr(player, "get_player"):
                fetched = player.get_player(getattr(player, "username", ""))
                bs = getattr(fetched, "balancesheet", None)
            if bs is None:
                raise ValueError("Could not find balancesheet for player.")

        bs = bs.load_from_db(username=player.username)

        # Construct liability details
        import datetime

        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        liability = {
            "name": f"({reason}) Loan" if reason else "Loan",
            "loanAmount": amount,
            "originalLoanAmount": amount,
            "interestRate": interest_rate,
            "amortizationTerm": term_months,
            "compoundingFrequency": "monthly",
            "paymentFrequency": "monthly",
            "totalPaymentsMade": 0,
            "totalAmountPaid": 0,
            "startDate": today_str,
            "durationMonths": term_months,
            "nextDueDate": today_str,
        }
        # Add to liabilities
        if hasattr(bs, "add_liability"):
            bs.add_liability(
                liability["name"],
                liability["loanAmount"],
                liability["interestRate"],
                amortizationTerm=liability["amortizationTerm"],
                compoundingFrequency=liability["compoundingFrequency"],
                paymentFrequency=liability["paymentFrequency"],
                totalPaymentsMade=liability["totalPaymentsMade"],
                totalAmountPaid=liability["totalAmountPaid"],
                startDate=liability["startDate"],
                durationMonths=liability["durationMonths"],
                nextDueDate=liability["nextDueDate"],
                originalLoanAmount=liability["originalLoanAmount"],
                username=getattr(player, "username", ""),
            )
            print(
                f"[DEBUG] Bank class => request_loan_from_bank: We assume liability updated? {bs.id} | {self._balance} -----------------------------------------"
            )
            print(">>>>>>>>>>>>> BALANCE AFTER LOAN: ", self._balance)

        else:
            raise ValueError("Player's balancesheet does not support liabilities.")

        # Log and persist
        self._log_operation(
            {
                "type": "loan_request",
                "amount": amount,
                "interestRate": interest_rate,
                "termMonths": term_months,
                "balanceAfter": self._balance,
                "reason": reason,
            }
        )
        self.save_bank_data()
        # Try saving balancesheet
        if hasattr(bs, "save_to_db"):
            try:
                username = getattr(player, "username", None)
                if username:
                    bs.save_to_db(username)
            except Exception:
                pass

        return {
            "loan": liability,
            "balance": self._balance,
            "message": "Loan approved and amount credited to bank account.",
        }

    def load_bank_data(self):
        """
        Loads the bank data for this customer from the database and loads it into the class instance.
        Also loads the late_payments field if present.
        """
        customer_id = getattr(self._player, "_id", None)
        if not customer_id:
            # Try loading by username if id not present
            username = getattr(self._player, "username", None)
            if username:
                player = self._player.get_player(username)
                customer_id = getattr(player, "_id", None)
        if not customer_id:
            raise ValueError("Cannot load bank data: customer ID not found.")

        bank_doc = bank_collection.find_one({"customerId": customer_id})
        if bank_doc:
            self.bank = bank_doc
            self._balance = bank_doc.get("balance", self._balance)
            self._operation_logs = bank_doc.get("Banklog", [])
            self.late_payments = bank_doc.get("late_payments", 0)
        else:
            self.bank = None
            self._balance = 0
            self._operation_logs = []
            self.late_payments = 0

        # Load logs from the bank_logs_collection, if exists
        if self.bank and "_id" in self.bank:
            logs_doc = bank_logs_collection.find_one({"bankId": self.bank["_id"]})
            self.bank_logs = logs_doc["logs"] if logs_doc and "logs" in logs_doc else []
        else:
            self.bank_logs = []

    def calculate_credit_score(self, bs):
        """
        bs: current BalanceSheet
        """

        prev_bs = bs.load_from_db(username=bs.player.username)
        if prev_bs:
            prev_bs = prev_bs.to_dict().get("prev_balancesheet", None)
            if prev_bs:
                prev_bs = json.loads(prev_bs)
                prev_bs = bs.from_dict(prev_bs).to_dict()
        else:
            prev_bs = None


        current_liabilities = sum_of_values(bs.liabilities, "loanAmount")
        current_assets = sum_of_values(bs.assets, "value")
        income = sum_of_values(bs.income, "amount")
        expenses = sum_of_values(bs.expenses, "amount")


        score = 500  # more realistic starting point

        # ---------- 1. Payment behavior ----------
        # Use Bank's late_payments property if BalanceSheet doesn't have it
        late_payments_count = getattr(bs, "late_payments", None)
        if late_payments_count is None:
            late_payments_count = self.late_payments

        score -= min(late_payments_count * 30, 150)

        # ---------- 2. Debt-to-Income (DTI) ----------
        income = max(income, 1)
        dti = current_liabilities / income

        if dti < 0.3:
            score += 120
        elif dti < 0.5:
            score += 60
        elif dti < 0.8:
            score -= 50
        else:
            score -= 120

        # ---------- 3. Cash flow ----------
        cash_flow = income - expenses

        if cash_flow > 0:
            score += 80
        else:
            score -= min(abs(cash_flow) / income * 100, 100)

        # ---------- 4. Liquidity (assets vs liabilities) ----------
        if current_assets > current_liabilities:
            score += 60
        else:
            score -= 80

        # ---------- 5. Behavioral changes (trend-based penalties/bonuses) ----------
        if prev_bs:
            # Rising debt
            previous_liabilities = sum_of_values(prev_bs.liabilities, "loanAmount")
            previous_assets = sum_of_values(prev_bs.assets, "value")
            previous_income = sum_of_values(prev_bs.income, "amount")
            previous_expenses = sum_of_values(prev_bs.expenses, "amount")


            if current_liabilities > previous_liabilities:
                increase_ratio = (current_liabilities - previous_liabilities) / max(
                    previous_liabilities, 1
                )
                score -= min(increase_ratio * 100, 80)

            # Income drop
            if income < previous_income:
                drop_ratio = (previous_income - income) / max(previous_income, 1)
                score -= min(drop_ratio * 120, 100)

            # Expense growth
            if expenses > previous_expenses:
                score -= min((expenses - previous_expenses) / income * 50, 50)

            # Improvement bonus (good trends)
            if (
                current_liabilities < previous_liabilities
                and income >= previous_income
                and expenses <= previous_expenses
            ):
                score += 50
        print(
            f" >> calculate_credit_score: score => {score} -----------------------------------------"
        )
        # ---------- 6. Clamp to realistic bounds ----------
        return max(300, min(score, 850))

    def save_bank_data(self):
        """
        Update bank data if it exists, or create a new entry if not.
        Also persists the late_payments field.
        """
        customer_id = getattr(self._player, "_id", None)

        if not self._player or customer_id is None:
            player = self._player.get_player(self._player.username)
            customer_id = player._id

        bank_data = {
            "balance": self._balance,
            "late_payments": self.late_payments,
            "Banklog": self._operation_logs,
            "customerId": customer_id,
            "customer": f"{getattr(self._player, 'username', '')}".strip(),
        }
        # Try to update, or insert if not exists (upsert=True)
        result = bank_collection.replace_one(
            {"customerId": customer_id}, bank_data, upsert=True
        )
        # Store all logs in a single document per bank to optimize performance
        if self._operation_logs:
            bank_id = (
                result.upserted_id
                if result.upserted_id
                else self.bank["_id"]
                if self.bank and "_id" in self.bank
                else None
            )
            # Upsert a single document containing all logs for the bank
            bank_logs_collection.replace_one(
                {"bankId": bank_id},
                {"bankId": bank_id, "logs": self._operation_logs},
                upsert=True,
            )
        self.load_bank_data()

    def to_dict(self, include_logs=False):
        """
        Returns a dictionary representation of the bank object.
        """
        data = {
            "balance": self._balance,
            "late_payments": self.late_payments,
            "customer": getattr(self._player, "username", None),
        }

        if include_logs:
            data["bank_logs"] = self.bank_logs
            data["operation_logs"] = self._operation_logs

        return data
