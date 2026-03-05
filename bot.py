from flask import Flask, request, jsonify
from flask_cors import CORS  # ✅ Import CORS
import os
import json
import websocket
import requests

app = Flask(__name__)
CORS(app)  # ✅ Enable CORS for all routes

# --- Environment variables ---
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
stake = float(os.getenv("Stake", 0.5))
daily_target = float(os.getenv("Daily_Target", 10))
stop_loss = float(os.getenv("Stop_Loss", 2))

# --- Bot variables ---
start_balance = 0
current_balance = 0
profit = 0
martingale = 1
bot_status = "OFF"

# --- Connect to Deriv ---
def connect_deriv():
    ws = websocket.create_connection("wss://ws.derivws.com/websockets/v3?app_id=1089")
    ws.send(json.dumps({"authorize": DERIV_TOKEN}))
    return ws
def place_trade(direction):
    global martingale, profit, current_balance
    ws = connect_deriv()
    stake_amount = stake * martingale
    proposal = {
        "proposal": 1,
        "amount": stake_amount,
        "basis": "stake",
        "contract_type": "CALL" if direction == "BUY" else "PUT",
        "currency": "USD",
        "duration": 5,
        "duration_unit": "t",
        "symbol": "R_75"
    }
    ws.send(json.dumps(proposal))
    result = json.loads(ws.recv())
    proposal_id = result["proposal"]["id"]
    buy = {"buy": proposal_id, "price": stake_amount}
    ws.send(json.dumps(buy))
    trade = json.loads(ws.recv())
    return trade

# --- Flask routes ---
@app.route("/")
def home():
    return "V75 BOT RUNNING"

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

# ✅ THIS IS WHERE YOU PASTE IT
@app.route("/webhook", methods=["POST"])
def webhook():
    global profit, martingale, bot_status

    if bot_status != "ON":
        return jsonify({"status": "Bot OFF"})

    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON received"})

    signal = data.get("signal")

    if signal not in ["BUY", "SELL"]:
        return jsonify({"error": "Invalid signal"})

    try:
        trade = place_trade(signal)
    except Exception as e:
        return jsonify({"error": str(e)})

    if "error" in trade:
        return jsonify(trade)

    buy_price = trade["buy"]["buy_price"]
    payout = trade["buy"]["payout"]

    result_profit = payout - buy_price
    profit += result_profit

    if result_profit < 0:
        martingale *= 2
    else:
        martingale = 1

    if profit >= daily_target:
        bot_status = "OFF"

    if profit <= -stop_loss:
        bot_status = "OFF"

    return jsonify({
        "status": "Trade Executed",
        "profit": profit,
        "martingale": martingale,
        "bot_status": bot_status
    })

@app.route("/stats")
def stats():
    return jsonify({
        "bot_status": bot_status,
        "stake": stake,
        "profit": profit,
        "martingale": martingale,
        "daily_target": daily_target,
        "stop_loss": stop_loss
    })

# --- Run Flask app ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
