from flask import Flask, request, jsonify
import websocket
import json
import os
from datetime import datetime

app = Flask(__name__)

DERIV_TOKEN = os.environ.get("DERIV_TOKEN")
STAKE = float(os.environ.get("STAKE", 1))
DAILY_LOSS_LIMIT = float(os.environ.get("DAILY_LOSS_LIMIT", 10))
BOT_ACTIVE = os.environ.get("BOT_ACTIVE", "true").lower() == "true"

daily_loss = 0
today_date = datetime.utcnow().date()


def reset_daily_loss():
    global daily_loss, today_date
    if datetime.utcnow().date() != today_date:
        daily_loss = 0
        today_date = datetime.utcnow().date()


def connect_ws():
    return websocket.create_connection("wss://ws.derivws.com/websockets/v3?app_id=1089")


def authorize(ws):
    ws.send(json.dumps({"authorize": DERIV_TOKEN}))
    return json.loads(ws.recv())


def get_balance(ws):
    ws.send(json.dumps({"balance": 1}))
    return json.loads(ws.recv())


def place_trade():
    global daily_loss

    reset_daily_loss()

    if not BOT_ACTIVE:
        return {"status": "Bot is OFF"}

    if daily_loss >= DAILY_LOSS_LIMIT:
        return {"status": "Daily loss limit reached"}

    ws = connect_ws()
    authorize(ws)

    balance_data = get_balance(ws)
    balance = balance_data["balance"]["balance"]

    if balance < STAKE:
        ws.close()
        return {"status": "Insufficient balance"}

    proposal = {
        "proposal": 1,
        "amount": STAKE,
        "basis": "stake",
        "contract_type": "CALL",
        "currency": "USD",
        "duration": 1,
        "duration_unit": "m",
        "symbol": "R_75"
    }

    ws.send(json.dumps(proposal))
    proposal_response = json.loads(ws.recv())

    if "error" in proposal_response:
        ws.close()
        return {"status": proposal_response["error"]["message"]}

    buy_request = {
        "buy": proposal_response["proposal"]["id"],
        "price": STAKE
    }

    ws.send(json.dumps(buy_request))
    buy_response = json.loads(ws.recv())

    ws.close()

    return {"status": "Trade Placed", "details": buy_response}


@app.route('/')
def home():
    return "V75 REAL Bot Ready"


@app.route('/trade', methods=['POST'])
def trade():
    result = place_trade()
    return jsonify(result)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
profit = 0
loss = 0
start_balance = 0

@app.route("/stats")
def stats():
    return {
        "start_balance": start_balance,
        "current_profit": profit,
        "current_loss": loss
    }
