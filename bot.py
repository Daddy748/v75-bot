from flask import Flask, request, jsonify
from flask_cors import CORS
import websocket
import json
import os

app = Flask(__name__)
CORS(app)

# ===== ENV VARIABLES =====
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
APP_ID = os.getenv("APP_ID", "1089")

STAKE = float(os.getenv("STAKE", 1))
DAILY_TARGET = float(os.getenv("Daily_Target", 10))
DAILY_LOSS_LIMIT = float(os.getenv("DAILY_LOSS_LIMIT", 2))

# ===== BOT VARIABLES =====
bot_status = "OFF"
profit = 0
martingale = 1

# ===== CONNECT TO DERIV =====
def connect_deriv():
    ws = websocket.create_connection(
        f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}"
    )

    ws.send(json.dumps({
        "authorize": DERIV_TOKEN
    }))

    response = json.loads(ws.recv())

    if "error" in response:
        raise Exception(response["error"]["message"])

    return ws


# ===== PLACE TRADE =====
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
        "symbol": "R_75"
    }

    ws.send(json.dumps(proposal))

    response = json.loads(ws.recv())

    if "error" in response:
        ws.close()
        return {"error": response["error"]["message"]}

    proposal_id = response["proposal"]["id"]

    buy = {
        "buy": proposal_id,
        "price": STAKE
    }

    ws.send(json.dumps(buy))

    result = json.loads(ws.recv())

    ws.close()

    return result


# ===== ROUTES =====

@app.route("/")
def home():
    return {"status": "Bot running"}


@app.route("/start")
def start():
    global bot_status
    bot_status = "ON"
    return {"status": "Bot Started"}


@app.route("/stop")
def stop():
    global bot_status
    bot_status = "OFF"
    return {"status": "Bot Stopped"}


@app.route("/stats")
def stats():
    return {
        "bot_status": bot_status,
        "stake": STAKE,
        "profit": profit,
        "martingale": martingale,
        "daily_target": DAILY_TARGET,
        "stop_loss": DAILY_LOSS_LIMIT
    }


@app.route("/webhook", methods=["POST"])
def webhook():

    global bot_status

    if bot_status != "ON":
        return {"status": "Bot OFF"}

    data = request.json

    if not data:
        return {"error": "No JSON received"}

    signal = data.get("signal")

    if signal not in ["BUY", "SELL"]:
        return {"error": "Invalid signal"}

    result = place_trade(signal)

    return result


# ===== RUN SERVER =====

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))

    app.run(host="0.0.0.0", port=port)
