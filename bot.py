from flask import Flask, request, jsonify
from flask_cors import CORS
import websocket
import json
import os

app = Flask(__name__)
CORS(app)

# --- Bot & Deriv settings ---
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
APP_ID = os.getenv("APP_ID", "1089")
STAKE = float(os.getenv("STAKE", 1))
DAILY_TARGET = float(os.getenv("Daily_Target", 10))
DAILY_LOSS_LIMIT = float(os.getenv("DAILY_LOSS_LIMIT", 2))

bot_status = "OFF"
profit = 0
martingale = 1

# --- Connect to Deriv ---
def connect_deriv():
    ws = websocket.create_connection(f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}")
    ws.send(json.dumps({"authorize": DERIV_TOKEN}))
    response = json.loads(ws.recv())
    if "error" in response:
        raise Exception(response["error"]["message"])
    return ws

# --- Place trade ---
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
    if "error" in response or "proposal" not in response:
        ws.close()
        return {"error": response.get("error", "No proposal received")}
    proposal_id = response["proposal"]["id"]
    buy = {"buy": proposal_id, "price": STAKE}
    ws.send(json.dumps(buy))
    result = json.loads(ws.recv())
    ws.close()
    return result

# --- Flask routes ---
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

@app.route("/webhook", methods=["POST"])
def webhook():
    global profit, martingale, bot_status
    data = request.json
    if not data or "signal" not in data:
        return {"error": "Invalid JSON"}
    signal = data["signal"]
    result = place_trade(signal)
    # Here you can also implement martingale, stop loss, daily target
    return result

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

# --- Run Flask app ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Use Railway’s port
    app.run(host="0.0.0.0", port=port)
