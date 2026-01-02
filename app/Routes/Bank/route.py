from app import app, socketio
from flask import request, jsonify
import threading
from app.BackgroundThreads import bg_payment
from classes.BalanceSheet.index import BalanceSheet
from classes.Bank.index import Bank
from classes.Player.index import Player


@app.route("/api/bank/<username>/make_payment", methods=["POST"])
def make_bank_payment(username):
    """
    Make a payment from the user's bank account to a specified recipient.

    Expects JSON:
    {
        "recipient": "recipient_name_or_account",
        "amount": 100.0,
        "late_payment"?: true
    }
    """
    data = request.get_json()
    recipient = data.get("recipient")
    amount = data.get("amount")
    late_payment = data.get("late_payment", None)

    if not recipient or amount is None:
        return jsonify({"error": "Missing 'recipient' or 'amount'."}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except Exception:
        return jsonify({"error": "Invalid payment 'amount'."}), 400

    # Load the player and bank
    player = Player(username)
    player = player.get_player(username)
    bank = Bank(customer=player)
    bank.load_bank_data()
    if not player:
        return jsonify({"error": f"User '{username}' not found."}), 404

    if not bank:
        return jsonify({"error": f"Bank account for '{username}' not found."}), 404

    # Check that the user has sufficient balance before starting the payment thread
    if amount > bank.get_balance():
        return jsonify({"error": "Insufficient funds for payment."}), 400

    try:
        # Use threading.Thread for background task execution
        # This works with Flask-SocketIO in threading mode
        thread = threading.Thread(
            target=bg_payment, args=(bank, player, amount, recipient, late_payment)
        )
        thread.daemon = True
        thread.start()
        return jsonify(
            {
                "message": f"Payment of {amount} to '{recipient}' is being processed in the background.",
                "balance": bank.get_balance(),
                "bank_log": bank.get_logs(),
            }
        ), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500

        # INSERT_YOUR_CODE


@app.route("/api/bank/<username>/request-loan", methods=["POST"])
def request_loan(username):
    """
    Request a loan for the given user.
    Expects JSON:
    {
        "amount": 50000,
        "interestRate": 0.04,
        "termMonths": 60,
        "reason": "Car purchase"
    }
    """
    data = request.get_json()
    amount = data.get("amount")
    interest_rate = data.get("interestRate")
    term_months = data.get("termMonths")
    reason = data.get("reason", "")

    if amount is None or interest_rate is None or term_months is None:
        return jsonify(
            {
                "error": "Missing required fields: 'amount', 'interestRate', or 'termMonths'."
            }
        ), 400

    try:
        amount = float(amount)
        interest_rate = float(interest_rate)
        term_months = int(term_months)
        if amount <= 0 or interest_rate < 0 or term_months <= 0:
            raise ValueError
    except Exception:
        return jsonify(
            {
                "error": "Invalid field types for 'amount', 'interestRate', or 'termMonths'."
            }
        ), 400

    # Load the player and bank
    player = Player(username)
    player = player.get_player(username)
    if not player:
        return jsonify({"error": f"User '{username}' not found."}), 404

    bs = BalanceSheet(player=player)
    if not bs:
        return jsonify({"error": f"Balance sheet for '{username}' not found."}), 404

    bank = Bank(customer=player)
    bank.load_bank_data()
    if not bank:
        return jsonify({"error": f"Bank account for '{username}' not found."}), 404

    try:
        loan_result = (
            bank.request_loan_from_bank(
                amount=amount,
                interest_rate=interest_rate,
                term_months=term_months,
                reason=reason,
                bs=bs,
            )
            if hasattr(bank, "request_loan_from_bank")
            else bank.request_loan_from_bank()
        )  # fallback if method signature not updated

        return jsonify(
            {
                "message": f"Loan request for {amount} submitted successfully.",
                "result": loan_result if loan_result is not None else {},
                "balance": bank.get_balance(),
            }
        ), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500
