from flask import Flask, request, jsonify
from flask_cors import CORS
import websocket
import json

app = Flask(__name__)
CORS(app)

# ==============================
# DERIV SETTINGS
# ==============================

DERIV_TOKEN = "l13t3j9l14c5e84"
APP_ID = "1089"
SYMBOL = "R_75"
STAKE = 1

# ==============================
# CONNECT TO DERIV
# ==============================

def connect_deriv():
    ws = websocket.create_connection(f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}")

    auth = {
        "authorize": DERIV_TOKEN
    }

    ws.send(json.dumps(auth))
    response = json.loads(ws.recv())

    if "error" in response:
        raise Exception(response["error"]["message"])

    return ws


# ==============================
# PLACE TRADE FUNCTION
# ==============================

def place_trade(signal):

    ws = connect_deriv()

    contract_type = "CALL" if signal == "BUY" else "PUT"

    proposal = {
        "proposal": 1,
        "amount": STAKE,
        "basis": "stake",
        "contract_type": contract_type,
        "currency": "USD",
        "duration": 5,
        "duration_unit": "t",
        "symbol": SYMBOL
    }

    ws.send(json.dumps(proposal))

    response = json.loads(ws.recv())

    # Check for errors
    if "error" in response:
        return {"error": response["error"]["message"]}

    if "proposal" not in response:
        return {"error": "No proposal received"}

    proposal_id = response["proposal"]["id"]

    buy = {
        "buy": proposal_id,
        "price": STAKE
    }

    ws.send(json.dumps(buy))

    result = json.loads(ws.recv())

    ws.close()

    return result


# ==============================
# WEBHOOK FOR TRADINGVIEW
# ==============================

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json

    if not data:
        return jsonify({"error": "No JSON received"})

    signal = data.get("signal")

    if signal not in ["BUY", "SELL"]:
        return jsonify({"error": "Invalid signal"})

    result = place_trade(signal)

    return jsonify(result)


# ==============================
# BOT STATUS
# ==============================

@app.route("/")
def home():
    return jsonify({"status": "Bot ON"})


# ==============================
# RUN SERVER
# ==============================

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
