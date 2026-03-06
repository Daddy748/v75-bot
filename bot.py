from flask import Flask, request, jsonify
from flask_cors import CORS
import websocket
import json
import os

app = Flask(__name__)
CORS(app)

# ==============================
# DERIV SETTINGS
# ==============================
DERIV_TOKEN = os.getenv("DERIV_TOKEN", "your_deriv_token_here")
APP_ID = os.getenv("APP_ID", "1089")
SYMBOL = "R_75"
STAKE = float(os.getenv("STAKE", 1))

# ==============================
# CONNECT TO DERIV
# ==============================
def connect_deriv():
    ws = websocket.create_connection(f"wss://ws.derivws.com/websockets/v3?app_id={APP_ID}")
    auth = {"authorize": DERIV_TOKEN}
    ws.send(json.dumps(auth))
    response = json.loads(ws.recv())
    if "error" in response:
        raise Exception(response["error"]["message"])
    return ws

# ==============================
# PLACE TRADE
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

    if "error" in response:
        ws.close()
        return {"error": response["error"]["message"]}

    if "proposal" not in response:
        ws.close()
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
# ROUTES
# ==============================
@app.route("/")
def home():
    return {"status": "Bot running"}

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data or "signal" not in data:
        return {"error": "Invalid JSON or missing signal"}
    signal = data["signal"]
    if signal not in ["BUY", "SELL"]:
        return {"error": "Signal must be BUY or SELL"}
    result = place_trade(signal)
    return result

# ==============================
# RUN FLASK
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Match Railway's public port
    app.run(host="0.0.0.0", port=port)
