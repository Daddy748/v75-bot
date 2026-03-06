from flask import Flask, request, jsonify
from flask_cors import CORS
import websocket
import json
import os

app = Flask(__name__)
CORS(app)

# ==============================
# ENVIRONMENT VARIABLES
# ==============================
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
APP_ID = os.getenv("APP_ID", "1089")
STAKE = float(os.getenv("STAKE", 1))
DAILY_TARGET = float(os.getenv("Daily_Target", 10))
DAILY_LOSS_LIMIT = float(os.getenv("DAILY_LOSS_LIMIT", 2))

# ==============================
# BOT VARIABLES
# ==============================
bot_status = "OFF"
profit = 0
martingale = 1

# ==============================
# CONNECT TO DERIV
# ==============================
def connect_deriv():
    try:
        ws = websocket.create_connection(f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}")
        ws.send(json.dumps({"authorize": DERIV_TOKEN}))
        response = json.loads(ws.recv())
        if "error" in response:
            raise Exception(response["error"]["message"])
        return ws
    except Exception as e:
        raise Exception(f"WebSocket connection failed: {str(e)}")

# ==============================
# PLACE TRADE
# ==============================
def place_trade(signal):
    global martingale, profit
    try:
        ws = connect_deriv()
        contract_type = "CALL" if signal == "BUY" else "PUT"
        proposal = {
            "proposal": 1,
            "amount": STAKE * martingale,
            "basis": "stake",
            "contract_type": contract_type,
            "currency": "USD",
            "duration": 5,
            "duration_unit": "t",
            "symbol": "R_75"
        }
        ws.send(json.dumps(proposal))
        response = json.loads(ws.recv())

        # Validate proposal
        if "error" in response or "proposal" not in response:
            ws.close()
            return {"error": response.get("error", "No proposal received")}

        proposal_id = response["proposal"]["id"]
        buy = {"buy": proposal_id, "price": STAKE * martingale}
        ws.send(json.dumps(buy))
        trade = json.loads(ws.recv())
        ws.close()

        # Calculate profit
        buy_price = trade["buy"]["buy_price"]
        payout = trade["buy"]["payout"]
        result_profit = payout - buy_price
        profit += result_profit

        # Martingale logic
        if result_profit < 0:
            martingale *= 2
        else:
            martingale = 1

        # Daily limits
        global bot_status
        if profit >= DAILY_TARGET or profit <= -DAILY_LOSS_LIMIT:
            bot_status = "OFF"

        return {
            "trade": trade,
            "profit": profit,
            "martingale": martingale,
            "bot_status": bot_status
        }

    except Exception as e:
        return {"error": str(e)}

# ==============================
# FLASK ROUTES
# ==============================
@app.route("/")
def home():
    return jsonify({"status": "Bot running"})

@app.route("/start")
def start():
    global bot_status
    bot_status = "ON"
    return jsonify({"status": "Bot Started"})

@app.route("/stop")
def stop():
    global bot_status
    bot_status = "OFF"
    return jsonify({"status": "Bot Stopped"})

@app.route("/stats")
def stats():
    return jsonify({
        "bot_status": bot_status,
        "stake": STAKE,
        "profit": profit,
        "martingale": martingale,
        "daily_target": DAILY_TARGET,
        "stop_loss": DAILY_LOSS_LIMIT
    })

@app.route("/webhook", methods=["POST"])
def webhook():
    global bot_status
    if bot_status != "ON":
        return jsonify({"status": "Bot OFF"})

    data = request.json
    if not data or "signal" not in data:
        return jsonify({"error": "Invalid JSON"})

    signal = data["signal"]
    if signal not in ["BUY", "SELL"]:
        return jsonify({"error": "Signal must be BUY or SELL"})

    return jsonify(place_trade(signal))

# ==============================
# RUN FLASK APP
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Railway public port
    app.run(host="0.0.0.0", port=port)
