import time
import requests
import pandas as pd
from config import (
    BASE_URL, REQUEST_TIMEOUT, REQUEST_RETRIES, RETRY_DELAY,
    CANDLE_LIMIT, DATA_CACHE_SECONDS
)

_cache = {}

def request_json(url, params=None):
    last_error = None
    for attempt in range(REQUEST_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            last_error = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as exc:
            last_error = exc
        if attempt + 1 < REQUEST_RETRIES:
            time.sleep(RETRY_DELAY)
    raise RuntimeError(f"Binance request failed: {last_error}")

def get_candles(symbol, interval, limit=CANDLE_LIMIT, force=False):
    key = (symbol, interval, limit)
    now = time.time()
    if not force and key in _cache and now - _cache[key][0] < DATA_CACHE_SECONDS:
        return _cache[key][1].copy()

    data = request_json(
        f"{BASE_URL}/api/v3/klines",
        {"symbol": symbol, "interval": interval, "limit": limit}
    )
    if not data:
        raise RuntimeError(f"No data for {symbol} {interval}")

    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_volume","trades","taker_buy_base",
        "taker_buy_quote","ignore"
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    for col in ["open","high","low","close","volume"]:
        df[col] = df[col].astype(float)

    # Do not trade on the still-forming candle.
    if len(df) > 2:
        df = df.iloc[:-1].copy()

    _cache[key] = (now, df)
    return df.copy()

def get_price(symbol):
    data = request_json(f"{BASE_URL}/api/v3/ticker/price", {"symbol": symbol})
    return float(data["price"])

def get_multi_tf(symbol):
    return {
        "15m": get_candles(symbol, "15m"),
        "1h": get_candles(symbol, "1h"),
    }
