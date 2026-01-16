from app import app
from flask import request, jsonify
from classes.Farm.index import Farm
from classes.Player.index import Player
from classes.GameState.index import GameState
from datetime import datetime


@app.route("/api/farms/<username>", methods=["GET"])
def get_all_farms(username):
    """
    Get all farms for a user.
    Returns a list of farm dictionaries.
    """
    try:
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farms = Farm.load_all_by_username(username)
        farms_data = [farm.toDict() for farm in farms]
        
        return jsonify({"farms": farms_data, "count": len(farms_data)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>", methods=["GET"])
def get_farm(username, farm_id):
    """
    Get specific farm details.
    """
    try:
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        # Verify farm belongs to player
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        return jsonify({"farm": farm.toDict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/create", methods=["POST"])
def create_farm(username):
    """
    Create a new farm.
    
    Expects JSON:
    {
        "name": "My Farm",
        "farmType": "crop",  // or "cattle"
        "numberOfPlots": 10,
        "propertyId": "optional_property_id"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        name = data.get("name")
        farmType = data.get("farmType", "crop")
        numberOfPlots = data.get("numberOfPlots", 10)
        propertyId = data.get("propertyId")
        extraData = data.get("extraData", {})
        
        if not name:
            return jsonify({"error": "Missing required field: 'name'"}), 400
        
        if farmType not in ["crop", "cattle"]:
            return jsonify({"error": "farmType must be 'crop' or 'cattle'"}), 400
        
        try:
            numberOfPlots = int(numberOfPlots)
            if numberOfPlots <= 0:
                raise ValueError
        except:
            return jsonify({"error": "numberOfPlots must be a positive integer"}), 400
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.createFarm(name, farmType, numberOfPlots, propertyId, username, extraData)
        farm.save_to_db()
        
        return jsonify({"message": "Farm created successfully", "farm": farm.toDict()}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/save", methods=["POST"])
@app.route("/api/farms/<username>/<farm_id>/save", methods=["POST"])
def save_farm(username, farm_id=None):
    """
    Save farm state (matches frontend save() method).
    
    Expects JSON: Full farm data dictionary (must include 'id' field if farm_id not in URL)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        # Get farm_id from URL or from request body
        target_farm_id = farm_id or data.get("id")
        if not target_farm_id:
            return jsonify({"error": "Farm ID required (in URL or request body)"}), 400
        
        farm = Farm.load_from_db(farm_id=target_farm_id, username=username)
        if not farm:
            # If farm doesn't exist, create it from the data
            farm = Farm(data)
            farm.username = username
        else:
            # Update existing farm with new data
            farm.load(data)
            farm.username = username
        
        # Verify farm belongs to player
        print(f"Farm username: {farm.toDict()}, Username: {username}")
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        farm.save_to_db()
        
        return jsonify({"message": "Farm saved successfully", "farm": farm.toDict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/plant", methods=["POST"])
def plant_seed(username, farm_id):
    """
    Plant seed on a plot.
    
    Expects JSON:
    {
        "plotNumber": 1,
        "seedType": "rice",
        "fromGlobalStorage": false,  // optional
        "globalStorage": {...}  // optional, required if fromGlobalStorage is true
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        plotNumber = data.get("plotNumber")
        seedType = data.get("seedType")
        fromGlobalStorage = data.get("fromGlobalStorage", False)
        globalStorage = data.get("globalStorage")
        
        if plotNumber is None or not seedType:
            return jsonify({"error": "Missing required fields: 'plotNumber' and 'seedType'"}), 400
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        success = farm.plantSeed(plotNumber, seedType, fromGlobalStorage, globalStorage)
        if not success:
            return jsonify({"error": "Failed to plant seed. Check if plot is idle and seed is available."}), 400
        
        farm.save_to_db()
        
        return jsonify({"message": "Seed planted successfully", "farm": farm.toDict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/harvest", methods=["POST"])
def harvest_plot(username, farm_id):
    """
    Harvest produce from a plot.
    
    Expects JSON:
    {
        "plotNumber": 1,
        "quantity": 1  // optional, default: 1
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        plotNumber = data.get("plotNumber")
        quantity = data.get("quantity", 1)
        
        if plotNumber is None:
            return jsonify({"error": "Missing required field: 'plotNumber'"}), 400
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        success = farm.harvestPlot(plotNumber, quantity)
        if not success:
            return jsonify({"error": "Failed to harvest plot. Check if plot is ready and storage has space."}), 400
        
        farm.save_to_db()
        
        return jsonify({"message": "Plot harvested successfully", "farm": farm.toDict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/add-animal", methods=["POST"])
def add_animal(username, farm_id):
    """
    Add multiple animals to farm.

    Expects JSON:
    {
        "animals": [
            {
                "type": "cow",  // "cow", "chicken", "goat", "pig", "sheep"
                "birthDate": "2024-01-01T00:00:00"  // optional, ISO format
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        animals = data.get("animals")
        if not animals or not isinstance(animals, list):
            return jsonify({"error": "Missing or invalid required field: 'animals' (must be an array)"}), 400

        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        farm = Farm()
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        print(f"Farm: {farm.toDict()}")
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        print(f"Farm username: {farm.username}, Username: {username}")
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        print(f"Farm username: {farm.username}, Username: {username}")
        results = []
        for animal_obj in animals:
            animalType = animal_obj.get("type")
            birthDateStr = animal_obj.get("birthDate")
            if not animalType:
                results.append({"success": False, "error": "Missing required field: 'type'", "animal": animal_obj})
                continue

            birthDate = None
            if birthDateStr:
                try:
                    birthDate = datetime.fromisoformat(birthDateStr.replace('Z', '+00:00'))
                except Exception as e:
                    results.append({"success": False, "error": f"Invalid birthDate format. Use ISO format:{e}", "animal": animal_obj})
                    continue

            success = farm.addAnimal(animalType, birthDate)
            if not success:
                results.append({"success": False, "error": f"Invalid animal type: '{animalType}'", "animal": animal_obj})
            else:
                results.append({"success": True, "animal": animal_obj})

        farm.save_to_db()

        if all(r.get("success") for r in results):
            return jsonify({"message": "Animals added successfully", "results": results, "farm": farm.toDict()}), 200
        elif any(r.get("success") for r in results):
            return jsonify({"message": "Some animals added", "results": results, "farm": farm.toDict()}), 207
        else:
            return jsonify({"error": "No animals were added", "results": results}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/feed-animal", methods=["POST"])
def feed_animal(username, farm_id):
    """
    Feed an animal.
    
    Expects JSON:
    {
        "animalId": "animal_123"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        animalId = data.get("animalId")
        
        if not animalId:
            return jsonify({"error": "Missing required field: 'animalId'"}), 400
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        success = farm.feedAnimal(animalId)
        if not success:
            return jsonify({"error": "Animal not found"}), 404
        
        farm.save_to_db()
        
        return jsonify({"message": "Animal fed successfully", "farm": farm.toDict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/collect-products", methods=["POST"])
def collect_products(username, farm_id):
    """
    Collect products from an animal.
    
    Expects JSON:
    {
        "animalId": "animal_123"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        animalId = data.get("animalId")
        
        if not animalId:
            return jsonify({"error": "Missing required field: 'animalId'"}), 400
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        collectedProducts = farm.collectProducts(animalId)
        if not collectedProducts:
            return jsonify({"error": "No products collected. Animal may need feeding or products already collected today."}), 400
        
        farm.save_to_db()
        
        return jsonify({
            "message": "Products collected successfully",
            "collectedProducts": collectedProducts,
            "farm": farm.toDict()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/hire-manager", methods=["POST"])
def hire_manager(username, farm_id):
    """
    Hire a farm manager.
    
    Expects JSON:
    {
        "id": "manager_123",
        "name": "John Doe",
        "salary": 1000,
        "automationLevel": 5
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        manager = {
            "id": data.get("id"),
            "name": data.get("name"),
            "salary": data.get("salary"),
            "automationLevel": data.get("automationLevel")
        }
        
        if not all([manager["id"], manager["name"], manager.get("salary") is not None]):
            return jsonify({"error": "Missing required fields: 'id', 'name', 'salary'"}), 400
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        success = farm.hireManager(manager)
        if not success:
            return jsonify({"error": "Farm already has a manager"}), 400
        
        farm.save_to_db()
        
        return jsonify({"message": "Manager hired successfully", "farm": farm.toDict()}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/fire-manager", methods=["POST"])
def fire_manager(username, farm_id):
    """
    Fire the current farm manager.
    """
    try:
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        success = farm.fireManager()
        if not success:
            return jsonify({"error": "Farm has no manager to fire"}), 400
        
        farm.save_to_db()
        
        return jsonify({"message": "Manager fired successfully", "farm": farm.toDict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/update-timers", methods=["POST"])
def update_timers(username, farm_id):
    """
    Update farm timers (crops, animals, pregnancy).
    
    Optional JSON:
    {
        "currentGameDate": "2024-01-01T00:00:00"  // ISO format, optional (uses stored game date if not provided)
    }
    """
    try:
        data = request.get_json() or {}
        currentGameDateStr = data.get("currentGameDate")
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        # Get current game date
        if currentGameDateStr:
            try:
                currentGameDate = datetime.fromisoformat(currentGameDateStr.replace('Z', '+00:00'))
            except:
                return jsonify({"error": "Invalid currentGameDate format. Use ISO format."}), 400
        else:
            # Use stored game date
            gameState = GameState.get_instance()
            currentGameDate = gameState.get_current_date()
        
        farm.updateTimers(currentGameDate)
        farm.save_to_db()
        
        return jsonify({"message": "Timers updated successfully", "farm": farm.toDict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/transfer-storage", methods=["POST"])
def transfer_storage(username, farm_id):
    """
    Transfer items between farm storage and global storage.
    
    Expects JSON:
    {
        "itemId": "item_123",
        "quantity": 5,
        "direction": "toGlobal",  // or "fromGlobal"
        "globalStorage": {...}  // required
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        itemId = data.get("itemId")
        quantity = data.get("quantity")
        direction = data.get("direction")
        globalStorage = data.get("globalStorage")
        
        if not all([itemId, quantity is not None, direction, globalStorage]):
            return jsonify({"error": "Missing required fields: 'itemId', 'quantity', 'direction', 'globalStorage'"}), 400
        
        if direction not in ["toGlobal", "fromGlobal"]:
            return jsonify({"error": "direction must be 'toGlobal' or 'fromGlobal'"}), 400
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        if direction == "toGlobal":
            success = farm.transferToGlobalStorage(itemId, quantity, globalStorage)
        else:
            success = farm.transferFromGlobalStorage(itemId, quantity, globalStorage)
        
        if not success:
            return jsonify({"error": "Transfer failed. Check item availability and quantities."}), 400
        
        farm.save_to_db()
        
        return jsonify({"message": "Transfer completed successfully", "farm": farm.toDict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/farms/<username>/<farm_id>/convert-seeds", methods=["POST"])
def convert_seeds(username, farm_id):
    """
    Convert produce to seeds.
    
    Expects JSON:
    {
        "produceType": "rice",
        "quantity": 20
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        produceType = data.get("produceType")
        quantity = data.get("quantity")
        
        if not produceType or quantity is None:
            return jsonify({"error": "Missing required fields: 'produceType' and 'quantity'"}), 400
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except:
            return jsonify({"error": "quantity must be a positive integer"}), 400
        
        player = Player.get_player(username)
        if player is None:
            return jsonify({"error": f"Player '{username}' not found"}), 404
        
        farm = Farm.load_from_db(farm_id=farm_id, username=username)
        if not farm:
            return jsonify({"error": f"Farm '{farm_id}' not found"}), 404
        
        if farm.username != username:
            return jsonify({"error": "Farm does not belong to this player"}), 403
        
        success = farm.convertProduceToSeeds(produceType, quantity)
        if not success:
            return jsonify({"error": "Conversion failed. Check if you have enough produce."}), 400
        
        farm.save_to_db()
        
        return jsonify({"message": "Produce converted to seeds successfully", "farm": farm.toDict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
