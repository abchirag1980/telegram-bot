import requests
import json
import datetime
import threading
import time
import yfinance as yf
import ta
import pandas as pd
from flask import Flask, request, jsonify

# ================= CONFIG =================
BOT_TOKEN = "8570941131:AAFSBDaXQa_TuDEX3auyOVXgol0xJhybwKE"
VIP_CHANNEL = "1003778847832"

WATCHLIST = ["RELIANCE.NS", "TCS.NS", "BTC-INR"]

app = Flask(__name__)

# ================= TELEGRAM =================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})


# ================= SIGNAL ENGINE =================
def get_signal(symbol):
    try:
        df = yf.download(symbol, period="2d", interval="15m")

        if df is None or len(df) < 20:
            return None

        close = df["Close"]

        # FIX: force 1D series
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        close = close.squeeze()

        df["ema5"] = ta.trend.ema_indicator(close, window=5)
        df["ema13"] = ta.trend.ema_indicator(close, window=13)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        ema5_last = float(last["ema5"].iloc[0])
        ema13_last = float(last["ema13"].iloc[0])
        ema5_prev = float(prev["ema5"].iloc[0])
        ema13_prev = float(prev["ema13"].iloc[0])

        if ema5_prev <= ema13_prev and ema5_last > ema13_last:
            return "BUY", float(last["Close"])

        if ema5_prev >= ema13_prev and ema5_last < ema13_last:
            return "SELL", float(last["Close"])

        return None

    except Exception as e:
        print("Signal error:", e)
        return None


# ================= SIGNAL LOOP =================
def signal_loop():
    while True:
        for s in WATCHLIST:
            sig = get_signal(s)
            if sig:
                msg = f"🔥 {sig[0]} SIGNAL\n{s}\nPrice: ₹{sig[1]}"
                send_message(VIP_CHANNEL, msg)

        time.sleep(900)


# ================= TELEGRAM BOT =================
def telegram_polling():
    offset = None

    while True:
        try:
            res = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={"offset": offset}
            ).json()

            for update in res.get("result", []):
                offset = update["update_id"] + 1

                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "")

                    # /start command
                    if text == "/start":
                        send_message(chat_id, "👋 Welcome!\nBuy VIP ₹499 💰")

                    # /vip command
                    elif text == "/vip":
                        send_message(chat_id, "✅ VIP system active")

        except Exception as e:
            print("Polling error:", e)

        time.sleep(1)


# ================= API =================
@app.route("/signals")
def signals():
    result = []

    for s in WATCHLIST:
        sig = get_signal(s)
        if sig:
            result.append({
                "symbol": s,
                "type": sig[0],
                "price": sig[1]
            })

    return jsonify(result)


# ================= START =================
if __name__ == "__main__":
    threading.Thread(target=signal_loop, daemon=True).start()
    threading.Thread(target=telegram_polling, daemon=True).start()

    print("Bot running...")

    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)