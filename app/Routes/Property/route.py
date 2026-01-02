from app import app
from flask import jsonify
from app.BackgroundThreads import update_properties_in_background
from classes.Player.index import Player
from classes.Property.index import Property
from flask import request
import threading


@app.route("/api/property/<username>", methods=["GET"])
def load_user_properties(username):
    """
    Load all properties for a user.
    Returns a list of property dictionaries.
    """
    try:
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404


        player_id = getattr(player, "id", None)
        if player_id is None and hasattr(player, "_id"):
            player_id = getattr(player, "_id", None)
       
        if player_id is None:
            return jsonify({"error": "Player ID not found"}), 404

        prop = Property(player)
        props = prop.load_all_owned_properties()

        return jsonify({"properties": props}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


        # INSERT_YOUR_CODE
@app.route("/api/property/<username>/apply_appreciation", methods=["POST"])
def apply_property_appreciation(username):
    """
    Apply appreciation/depreciation to one or more of a user's properties.
    Expects JSON: { "property_ids": ["..."], "years": int/float (optional), "update_balancesheet": bool (optional) }
    The appreciation update runs in a background thread.
    """
    try:
        data = request.get_json(force=True)
        property_ids = data.get("property_ids")
        years = data.get("years", 1/12)
        update_balancesheet = data.get("update_balancesheet", True)

        if not property_ids or not isinstance(property_ids, list):
            return jsonify({"error": "property_ids (array) is required in request body"}), 400

        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404

        # Start the background thread for updating properties
        thread = threading.Thread(
            target=update_properties_in_background,
            args=(player, Property, property_ids, years, update_balancesheet),
            daemon=True,
        )
        thread.start()

        return jsonify({
            "message": "Appreciation update started in background",
            "property_ids": property_ids,
            "years": years
        }), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500

