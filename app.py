from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import requests
import os
import json
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
    # 최소 주문 수량 설정
    min_order_sizes = {
        'BTC-USDT-SWAP': (0.001, 3),
        'ETH-USDT-SWAP': (0.01, 2),
        'XRP-USDT-SWAP': (1.0, 0),
        'SUI-USDT-SWAP': (1.0, 0),
        'SOL-USDT-SWAP': (0.1, 1),
        'DOGE-USDT-SWAP': (10.0, 0)
    }
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
            # 최소 수량 체크 및 반영
            min_size, decimals = min_order_sizes.get(symbol, (1.0, 0))
    import math
    raw_size = max(float(size), min_size)
    factor = 10 ** decimals
    final_size = math.floor(raw_size * factor) / factor
    body["sz"] = str(final_size)

        response = requests.post(OKX_TRADE_URL + path, headers=HEADERS, data=json.dumps(body))
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
