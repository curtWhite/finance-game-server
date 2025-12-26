# INSERT_YOUR_CODE
from flask import request, jsonify
import threading
from app import app
from app.BackgroundThreads import bg_update_liability
from classes.BalanceSheet.index import BalanceSheet
from classes.Player.index import Player


# Import the mock_balancesheet_for_working_class function
from .temp import mock_balancesheet_for_working_class


def get_player_or_404(username):
    player = Player.load_from_db(username)
    if not player:
        return None, jsonify({"error": "Player not found"}), 404
    return player, None, None


@app.route("/api/balancesheet/<username>/add", methods=["POST"])
def add_balancesheet_item(username):
    """
    Add an item (asset, liability, income, or expense) to the user's balancesheet.
    Body JSON: { "type": "asset", "name": "House", "amount": 100000 }
    """
    data = request.get_json()
    item_type = data.get("type")
    name = data.get("name")
    amount = data.get("amount")
    if item_type not in ["asset", "liability", "income", "expense"]:
        return jsonify(
            {"error": "Invalid type. Must be asset, liability, income, or expense."}
        ), 400
    if not name or amount is None:
        return jsonify({"error": "Missing name or amount."}), 400
    player, error_resp, status = get_player_or_404(username)
    if error_resp:
        return error_resp, status
    bs = player.balancesheet
    if item_type == "asset":
        bs.add_asset(name, amount, username=username)
    elif item_type == "liability":
        bs.add_liability(name, amount, username=username)
    elif item_type == "income":
        bs.add_income(name, amount, username=username)
    elif item_type == "expense":
        bs.add_expense(name, amount, username=username)
    # Save balancesheet update
    player.save_to_db()
    return jsonify(
        {"message": f"{item_type.capitalize()} added.", "balancesheet": bs.to_dict()}
    ), 200


@app.route("/api/balancesheet/<username>/remove", methods=["POST"])
def remove_balancesheet_item(username):
    """
    Remove an item (asset, liability, income, or expense) from the user's balancesheet.
    Body JSON: { "type": "asset", "name": "House", "amount": 100000 } # amount optional; if omitted, removes entire item
    """
    data = request.get_json()
    item_type = data.get("type")
    name = data.get("name")
    amount = data.get("amount", None)  # if omitted, item fully removed
    if item_type not in ["asset", "liability", "income", "expense"]:
        return jsonify(
            {"error": "Invalid type. Must be asset, liability, income, or expense."}
        ), 400
    if not name:
        return jsonify({"error": "Missing name."}), 400
    player, error_resp, status = get_player_or_404(username)
    if error_resp:
        return error_resp, status
    bs = player.balancesheet
    if item_type == "asset":
        bs.remove_asset(name, amount, username=username)
    elif item_type == "liability":
        bs.remove_liability(name, amount, username=username)
    elif item_type == "income":
        bs.remove_income(name, amount, username=username)
    elif item_type == "expense":
        bs.remove_expense(name, amount, username=username)
    player.save_to_db()
    return jsonify(
        {"message": f"{item_type.capitalize()} removed.", "balancesheet": bs.to_dict()}
    ), 200


@app.route("/api/balancesheet/<username>", methods=["GET"])
def get_balancesheet(username):
    """
    Get the balancesheet for a user.
    """
    player, error_resp, status = get_player_or_404(username)
    if error_resp:
        return error_resp, status
    bs = player.balancesheet.to_dict()
    return jsonify(bs), 200


# You must register this blueprint with your Flask app elsewhere, e.g.:
# app.register_blueprint(balancesheet_bp)


# INSERT_YOUR_CODE
@app.route("/api/balancesheet/<username>/liability/update", methods=["POST"])
def update_liability(username):
    """
    Update one or more fields of a liability by name for the given user.

    Request JSON:
      {
        "liabilities": [{
            "loanAmount": 210000,
            "interestRate": 0.035,
            "nextDueDate": "2024-08-01",
            ...
        },
        ...
      }]
    """
    data = request.get_json()

    updates = data.get("liabilities", [])

    player, error_resp, status = get_player_or_404(username)
    if error_resp:
        return error_resp, status


    bs = BalanceSheet(player=player)

    # Use threading.Thread for background task execution
    # This works with Flask-SocketIO in threading mode
    thread = threading.Thread(target=bg_update_liability, args=(bs, username, updates, player))
    thread.daemon = True
    thread.start()

    return jsonify(
        {
            "message": "Liability update is being processed in the background.",
            "balancesheet": bs.to_dict(),
        }
    ), 200


@app.route("/api/balancesheet/<username>/mock/workclass", methods=["POST"])
def mock_working_class_balancesheet(username):
    """
    Testing route to create a working class balancesheet for a user.
    """
    try:
        bs = mock_balancesheet_for_working_class(username)
        return jsonify(
            {
                "message": f"Mock balancesheet for {username} created.",
                "balancesheet": bs.to_dict(),
            }
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
