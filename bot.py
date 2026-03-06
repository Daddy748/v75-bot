from flask import Flask, request, jsonify
from flask_cors import CORS
import websocket
import json
import os

app = Flask(__name__)
CORS(app)

# =========================
# ENV VARIABLES (Railway)
# =========================

DERIV_TOKEN = os.getenv("DERIV_TOKEN")
APP_ID = os.getenv("APP_ID", "1089")

STAKE = float(os.getenv("STAKE", 1))
DAILY_TARGET = float(os.getenv("DAILY_TARGET", 10))
DAILY_LOSS_LIMIT = float(os.getenv("DAILY_LOSS_LIMIT", 5))

SYMBOL = "frxBTCUSD"

# =========================
# BOT VARIABLES
# =========================

bot_status = "OFF"
profit = 0
martingale = 1

# =========================
# CONNECT TO DERIV
# =========================

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


# =========================
# PLACE TRADE
# =========================

def place_trade(signal):

    global martingale, profit, bot_status

    ws = connect_deriv()

    contract_type = "CALL" if signal == "BUY" else "PUT"

    stake_amount = STAKE * martingale

    proposal = {
        "proposal": 1,
        "amount": stake_amount,
        "basis": "stake",
        "contract_type": contract_type,
        "currency": "USD",
        "duration": 60,
        "duration_unit": "s",
        "symbol": SYMBOL
    }

    ws.send(json.dumps(proposal))

    response = json.loads(ws.recv())

    if "error" in response:
        ws.close()
        return {"error": response["error"]["message"]}

    proposal_id = response["proposal"]["id"]

    buy = {
        "buy": proposal_id,
        "price": stake_amount
    }

    ws.send(json.dumps(buy))

    trade = json.loads(ws.recv())

    ws.close()

    # simple profit simulation
    if "buy" in trade:
        payout = trade["buy"].get("payout", stake_amount * 1.9)
        result_profit = payout - stake_amount
        profit += result_profit

        if result_profit < 0:
            martingale *= 2
        else:
            martingale = 1

    if profit >= DAILY_TARGET or profit <= -DAILY_LOSS_LIMIT:
        bot_status = "OFF"

    return {
        "trade": trade,
        "profit": profit,
        "martingale": martingale,
        "bot_status": bot_status
    }


# =========================
# ROUTES
# =========================

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


# =========================
# TRADINGVIEW WEBHOOK
# =========================

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


# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))

    app.run(host="0.0.0.0", port=port)
