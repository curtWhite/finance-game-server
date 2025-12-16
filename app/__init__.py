from flask import Flask, jsonify
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_cors import CORS
from flask_socketio import SocketIO

load_dotenv()
MONGO_URI = os.getenv("MONGO_DB_CONNECTION_STRING")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client.get_database('Capitol-db')

app = Flask(__name__)
CORS(app)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.route('/')
def index():
    # Example: fetch some data from MongoDB to confirm connection

    collections = db.list_collection_names()
    return jsonify({'message': 'Hello, World!', 'collections': collections})


from .Routes.Bank.route import *
from .Routes.Player.route import *
from .Routes.GameBank.route import *
from .Routes.Job.route import *
from .Routes.BalanceSheet.route import *
# Import socket events (create this file for Socket.IO event handlers)
from .socket_events import *
