import requests
import pandas as pd
import time

SYMBOL = "BTCUSDT"
INTERVAL = "1m"

def get_price_data():
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit=100"
    data = requests.get(url).json()

    closes = [float(candle[4]) for candle in data]

    df = pd.DataFrame(closes, columns=["close"])
    return df

def calculate_signal():

    df = get_price_data()

    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema21"] = df["close"].ewm(span=21).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if prev.ema9 < prev.ema21 and last.ema9 > last.ema21:
        return "BUY"

    elif prev.ema9 > prev.ema21 and last.ema9 < last.ema21:
        return "SELL"

    return None


while True:

    signal = calculate_signal()

    if signal:
        print(f"BTCUSD SIGNAL: {signal}")

    time.sleep(60)
