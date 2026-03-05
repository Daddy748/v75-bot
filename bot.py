from flask import Flask, request, jsonify
from flask_cors import CORS  # ✅ Import CORS

app = Flask(__name__)
CORS(app)  # ✅ Enable CORS for all routes
import websocket
import json
import requests
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

DERIV_TOKEN = os.getenv("DERIV_TOKEN")

stake = float(os.getenv("Stake", 0.5))
daily_target = float(os.getenv("Daily_Target", 10))
stop_loss = float(os.getenv("Stop_Loss", 2))

start_balance = 0
current_balance = 0
profit = 0
martingale = 1
bot_status = "OFF"

def connect_deriv():
    ws = websocket.create_connection("wss://ws.derivws.com/websockets/v3")
    ws.send(json.dumps({
        "authorize": DERIV_TOKEN
    }))
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

    buy = {
        "buy": proposal_id,
        "price": stake_amount
    }

    ws.send(json.dumps(buy))
    trade = json.loads(ws.recv())

    return trade

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

@app.route("/webhook", methods=["POST"])
def webhook():
    global profit, martingale, bot_status

    if bot_status != "ON":
        return jsonify({"status": "Bot OFF"})

    data = request.json
    signal = data.get("signal")

    trade = place_trade(signal)

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
        "trade": trade,
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
