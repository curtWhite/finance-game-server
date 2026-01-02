from app import app
from flask import request, jsonify
from classes.BalanceSheet.index import BalanceSheet
from classes.Bank.index import Bank
from classes.Job.index import Job
from classes.Player.index import Player
from classes.Property.index import Property


@app.route("/api/player", methods=["GET"])
def get_player():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Missing 'username' parameter"}), 400

    player = Player.get_player(username)
    job = Job(id=player.job)
    bank = Bank(customer=player)
    bs = BalanceSheet(player=player)
    props = Property(player)
    player.balancesheet = bs

    if not player:
        result = {}
        return jsonify({"error": f"Player '{username}' not found."}), 404
    else:
        result = player.to_dict()
        result["job"] = job.to_dict()
        result["bank"] = bank.to_dict()
        result['bank']['credit_score'] = bank.calculate_credit_score(bs)
        result["balancesheet"] = bs.to_dict()
        # result['balancesheet']['prev_balancesheet'] = bs.get_prev_balancesheet(username)
        result['properties'] = props.load_all_owned_properties()

        if result["job"] is not None:
            result["job"]["staff"] = []
    print("LOADING PLAYER . BS: => ", bs.player.username)
    return jsonify(result), 200


# INSERT_YOUR_CODE
@app.route("/api/player", methods=["PUT"])
def save_player():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    username = data.get("username")
    if not username:
        return jsonify({"error": "Missing required field: 'username'"}), 400

    player = Player.get_player(username)
    if not player:
        return jsonify({"error": f"Player '{username}' not found."}), 404

    # Update player fields from incoming data
    # Only update fields that are present in the request, ignore unknown fields
    updatable_fields = [
        "score",
        "level",
        "total_time",
        "time_slots",
        "job",
        "properties",
        "crypto",
        "commodities",
        "business",
        "stock",
        "experience",
        "energy",
        "qualifications",
        "balancesheet",
    ]
    for field in updatable_fields:
        if field in data:
            setattr(player, field, data[field])

    try:
        player.save_to_db()
    except Exception as e:
        return jsonify({"error": "Failed to save player.", "details": str(e)}), 500
    return jsonify(
        {"message": "Player state saved successfully.", "player": player.to_dict()}
    ), 200


@app.route("/api/player/increase_experience", methods=["POST"])
def increase_experience():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    username = data.get("username")
    exp_points = data.get("exp_points")
    if not username or exp_points is None:
        return jsonify(
            {"error": "Missing required fields: 'username' or 'exp_points'"}
        ), 400

    try:
        exp_points = float(exp_points)
    except (ValueError, TypeError):
        return jsonify({"error": "'exp_points' must be a number."}), 400

    player = Player(username=username)
    player = player.get_player(username)
    if not player:
        return jsonify({"error": f"Player '{username}' not found."}), 404

    try:
        player.increase_experience(exp_points)
        return jsonify(
            {
                "message": f"Experience increased by {exp_points} for player '{username}'.",
            }
        ), 200
    except Exception as e:
        return jsonify(
            {"error": "Failed to increase experience", "details": str(e)}
        ), 500

        # INSERT_YOUR_CODE
@app.route("/api/player/add_property", methods=["POST"])
def add_property():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    username = data.get("username")
    property_item = data.get("property_item")
    if not username or not property_item:
        return jsonify(
            {"error": "Missing required fields: 'username' or 'property_item'"}
        ), 400

    player = Player(username=username)
    player = player.get_player(username)
    if not player:
        return jsonify({"error": f"Player '{username}' not found."}), 404

    try:
        player.add_property(property_item)
        return jsonify(
            {
                "message": f"Property added for player '{username}'.",
                "player": player.to_dict(),
            }
        ), 200
    except Exception as e:
        return jsonify(
            {"error": "Failed to add property", "details": str(e)}
        ), 500
