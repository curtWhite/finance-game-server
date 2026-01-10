from app import app
from flask import request, jsonify
import threading
from app.BackgroundThreads import bg_process_lotto_ticket
from classes.Lotto.index import Lotto
from classes.Bank.index import Bank
from classes.Player.index import Player


@app.route("/api/lotto/<username>/submit", methods=["POST"])
def submit_lotto_ticket(username):
    """
    Submit a lottery ticket for a player.

    Expects JSON:
    {
        "numbers": [1, 5, 10, 15, 20, 25],  // List of numbers chosen by player
        "ticket_cost": 10,                  // Optional, default: 10
        "result_delay_hours": 1             // Optional, default: 1 hour
    }
    """
    data = request.get_json()
    numbers = data.get("numbers")
    ticket_cost = data.get("ticket_cost", 10)
    result_delay_hours = data.get("result_delay_hours", None)  # None uses default

    if not numbers or not isinstance(numbers, list):
        return jsonify(
            {"error": "Missing or invalid 'numbers' field. Must be a list."}
        ), 400

    try:
        ticket_cost = float(ticket_cost)
        if ticket_cost <= 0:
            raise ValueError
    except Exception:
        return jsonify(
            {"error": "Invalid 'ticket_cost'. Must be a positive number."}
        ), 400

    if result_delay_hours is not None:
        try:
            result_delay_hours = float(result_delay_hours)
            if result_delay_hours <= 0:
                raise ValueError
        except Exception:
            return jsonify(
                {"error": "Invalid 'result_delay_hours'. Must be a positive number."}
            ), 400
        result_delay_seconds = result_delay_hours * 3600
    else:
        result_delay_seconds = Lotto.DEFAULT_RESULT_DELAY_HOURS * 3600

    # Load the player
    player = Player.get_player(username)
    if not player:
        return jsonify({"error": f"User '{username}' not found."}), 404

    # Check if player has enough balance to buy ticket
    bank = Bank(customer=player)
    bank.load_bank_data()
    if bank.get_balance() < ticket_cost:
        return jsonify({"error": "Insufficient funds to purchase ticket."}), 400

    try:
        # Create lotto ticket
        lotto = Lotto(player=player)
        ticket_data = lotto.submit_ticket(
            numbers=numbers,
            ticket_cost=ticket_cost,
            result_delay_seconds=result_delay_seconds,
        )

        # Deduct ticket cost from bank account
        bank.withdraw(amount=ticket_cost)

        # Start background thread to process ticket after delay
        thread = threading.Thread(
            target=bg_process_lotto_ticket,
            args=(lotto, player, result_delay_seconds),
            daemon=True,
        )
        thread.start()

        return jsonify(
            {
                "message": f"Lotto ticket submitted successfully. Results will be available in {result_delay_hours or Lotto.DEFAULT_RESULT_DELAY_HOURS} hour(s).",
                "ticket": ticket_data,
                "balance": bank.get_balance(),
            }
        ), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500


@app.route("/api/lotto/<username>/tickets", methods=["GET"])
def get_player_tickets(username):
    """
    Get all lotto tickets for a player, optionally filtered by status.

    Query parameters:
    - status: Optional filter ("pending", "won", "lost")
    """
    status = request.args.get("status", None)

    # Load the player
    player = Player.get_player(username)
    if not player:
        return jsonify({"error": f"User '{username}' not found."}), 404

    try:
        tickets = Lotto.load_player_tickets(username, status=status)
        return jsonify({"tickets": tickets, "count": len(tickets)}), 200
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500


@app.route("/api/lotto/<username>/ticket/<ticket_id>", methods=["GET"])
def get_ticket_details(username, ticket_id):
    """
    Get details of a specific lotto ticket.
    """
    # Load the player
    player = Player.get_player(username)
    if not player:
        return jsonify({"error": f"User '{username}' not found."}), 404

    try:
        ticket = Lotto.load_from_db(ticket_id, player=player)
        if not ticket:
            return jsonify({"error": f"Ticket '{ticket_id}' not found."}), 404

        # Verify ticket belongs to player
        if ticket.username != username:
            return jsonify({"error": "Ticket does not belong to this player."}), 403

        return jsonify({"ticket": ticket.to_dict()}), 200
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500
