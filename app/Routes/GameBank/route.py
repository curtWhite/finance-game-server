from app import app
from flask import request, jsonify
from classes.GameBank.index import GameBank

@app.route('/api/gamebank/pay', methods=['POST'])
def gamebank_pay():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    player_username = data.get('username')
    amount = data.get('amount')
    proxy = data.get('proxy')
    message = data.get('message')
    print(data)

    if not player_username or amount is None:
        return jsonify({"error": "Missing required fields: 'username' or 'amount'"}), 400
    try:
        amount = float(amount)
        bank = GameBank.get_bank()
        bank.pay_player(player_username, amount, proxy, message )
        return jsonify({
            "message": f"Paid {amount} to '{player_username}' from the bank.",
            "new_bank_balance": bank.balance
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500
