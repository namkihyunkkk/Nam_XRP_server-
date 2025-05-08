from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
OKX_TRADE_URL = "https://www.okx.com"

HEADERS = {
    "Content-Type": "application/json",
    "OK-ACCESS-KEY": OKX_API_KEY,
    "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE
}

def generate_signature(timestamp, method, request_path, body):
    message = f"{timestamp}{method}{request_path}{body}"
    return hmac.new(bytes(OKX_API_SECRET, encoding='utf8'), msg=message.encode(), digestmod=hashlib.sha256).hexdigest()

def place_order(symbol, side, size):
    timestamp = str(time.time())
    path = "/api/v5/trade/order"
    body = {
        "instId": symbol,
        "tdMode": "cross",
        "side": "buy" if side == "BUY" else "sell",
        "ordType": "market",
        "sz": size
    }
    body_json = json.dumps(body)
    HEADERS.update({
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-SIGN": generate_signature(timestamp, "POST", path, body_json)
    })
    response = requests.post(OKX_TRADE_URL + path, headers=HEADERS, data=body_json)
    return response.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or data.get("secret") != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    signal = data.get("signal")
    symbol = data.get("symbol") + "-USDT-SWAP"
    size = str(data.get("size", "1"))

    if signal in ["BUY", "TP", "SL"]:
        result = place_order(symbol, signal, size)
        return jsonify(result)

    return jsonify({"status": "ignored"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
