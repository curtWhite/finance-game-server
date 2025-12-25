from app import app, socketio
from flask import request, jsonify
from app.BackgroundThreads import bg_payment
from classes.Bank.index import Bank
from classes.Player.index import Player


@app.route("/api/bank/<username>/make_payment", methods=["POST"])
def make_bank_payment(username):
    """
    Make a payment from the user's bank account to a specified recipient.

    Expects JSON:
    {
        "recipient": "recipient_name_or_account",
        "amount": 100.0
    }
    """
    data = request.get_json()
    recipient = data.get("recipient")
    amount = data.get("amount")

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

    try:
        # Use socketio.start_background_task for better compatibility with eventlet workers
        # This ensures proper async handling with Flask-SocketIO and Gunicorn
        socketio.start_background_task(bg_payment, bank, player, amount, recipient)
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
