import requests
import pandas as pd
from config import BASE_URL, INTERVAL, CANDLE_LIMIT

def get_candles(symbol):
    url = f"{BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": INTERVAL, "limit": CANDLE_LIMIT}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    rows = r.json()

    cols = ["open_time","open","high","low","close","volume","close_time",
            "quote_volume","trades","taker_base","taker_quote","ignore"]
    df = pd.DataFrame(rows, columns=cols)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df

def get_price(symbol):
    url = f"{BASE_URL}/api/v3/ticker/price"
    r = requests.get(url, params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    return float(r.json()["price"])
