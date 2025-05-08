from flask import Flask, request, jsonify
import hmac
import hashlib
import requests
import os
import json
import math
from dotenv import load_dotenv

# 환경변수 로딩
load_dotenv()
app = Flask(__name__)

# 환경변수 값 읽기
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_API_PASSPHRASE = os.getenv("OKX_PASSPHRASE")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
OKX_TRADE_URL = "https://www.okx.com"

# ✅ OKX 서버 시간 동기화
def get_okx_server_timestamp():
    response = requests.get("https://www.okx.com/api/v5/public/time")
    server_time = response.json()["data"][0]["ts"]
    return str(int(server_time) / 1000)

# ✅ 시그니처 생성
def generate_signature(timestamp, method, request_path, body):
    message = f"{timestamp}{method}{request_path}{body}"
    return hmac.new(
        bytes(OKX_API_SECRET, encoding='utf8'),
        msg=message.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

# ✅ 주문 처리 함수
def place_order(symbol, side, size):
    min_order_sizes = {
        'BTC-USDT-SWAP': (0.001, 3),
        'ETH-USDT-SWAP': (0.01, 2),
        'XRP-USDT-SWAP': (1.0, 0),
        'SUI-USDT-SWAP': (1.0, 0),
        'SOL-USDT-SWAP': (0.1, 1),
        'DOGE-USDT-SWAP': (10.0, 0)
    }

    path = "/api/v5/trade/order"
    timestamp = get_okx_server_timestamp()

    # 최소 주문 수량 반영 및 반올림
    min_size, decimals = min_order_sizes.get(symbol, (1.0, 0))
    raw_size = max(float(size), min_size)
    factor = 10 ** decimals
    final_size = math.floor(raw_size * factor) / factor

    body = {
        "instId": symbol,
        "tdMode": "cross",
        "side": "buy" if side == "BUY" else "sell",
        "ordType": "market",
        "sz": str(final_size)
    }

    # ✅ JSON 직렬화 시 공백 없이 생성해야 서명 오류 없음
    body_json = json.dumps(body, separators=(',', ':'), ensure_ascii=False)

    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": generate_signature(timestamp, "POST", path, body_json),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE
    }

    response = requests.post(OKX_TRADE_URL + path, headers=headers, data=body_json)
    return response.json()

# ✅ 웹훅 엔드포인트
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

# ✅ 실행
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
