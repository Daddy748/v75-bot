from flask import Flask
import os
import websocket
import json
import threading

app = Flask(__name__)

DERIV_TOKEN = os.environ.get("DERIV_TOKEN")

def test_deriv_connection():
    try:
        ws = websocket.create_connection("wss://ws.derivws.com/websockets/v3?app_id=1089")
        
        auth_data = {
            "authorize": DERIV_TOKEN
        }

        ws.send(json.dumps(auth_data))
        response = ws.recv()
        data = json.loads(response)

        if "error" in data:
            print("❌ Authorization Failed:", data["error"]["message"])
        else:
            print("✅ Deriv Connection Successful")

        ws.close()

    except Exception as e:
        print("Connection Error:", str(e))


@app.route('/')
def home():
    threading.Thread(target=test_deriv_connection).start()
    return "Testing Deriv Connection... Check Railway Logs."

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
