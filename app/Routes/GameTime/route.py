from app import app
from flask import request, jsonify
from classes.GameTime.index import GameTime
from classes.Player.index import Player


@app.route("/api/game-time/<username>", methods=["GET"])
def get_game_time(username):
    """
    Get game time for a user.
    
    Returns:
        Game time data or 404 if not found
    """
    try:
        # Verify player exists
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        game_time = GameTime.load_from_db(username)
        if not game_time:
            return jsonify({"error": "Game time not found"}), 404
        
        return jsonify(game_time.toDict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/game-time/<username>", methods=["POST", "PUT", "PATCH"])
def save_game_time(username):
    """
    Save game time for a user.
    Creates or updates game time.
    
    Expects JSON:
    {
        "year": 2024,
        "month": 1,
        "week": 1,
        "day": 1,
        "startTime": "2024-01-01T00:00:00",  // ISO format
        "elapsedGameMonths": 0.5
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        # Verify player exists
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        # Validate required fields
        required_fields = ["year", "month", "week", "day"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        # Validate data types
        try:
            year = int(data.get("year"))
            month = int(data.get("month"))
            week = int(data.get("week"))
            day = int(data.get("day"))
            elapsedGameMonths = float(data.get("elapsedGameMonths", 0.0))
        except (ValueError, TypeError) as e:
            return jsonify({"error": f"Invalid data types: {str(e)}"}), 400
        
        # Validate ranges
        if month < 1 or month > 12:
            return jsonify({"error": "Month must be between 1 and 12"}), 400
        if week < 1 or week > 4:
            return jsonify({"error": "Week must be between 1 and 4"}), 400
        if day < 1 or day > 7:
            return jsonify({"error": "Day must be between 1 and 7"}), 400
        if elapsedGameMonths < 0:
            return jsonify({"error": "elapsedGameMonths must be non-negative"}), 400
        
        # Create or update game time
        game_time = GameTime.create_or_update(username, {
            "year": year,
            "month": month,
            "week": week,
            "day": day,
            "startTime": data.get("startTime"),
            "elapsedGameMonths": elapsedGameMonths,
        })
        
        return jsonify({
            "message": "Game time saved successfully",
            "gameTime": game_time.toDict()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
