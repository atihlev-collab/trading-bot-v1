import time
import requests
import pandas as pd

from config import (
    BASE_URL,
    REQUEST_TIMEOUT,
    REQUEST_RETRIES,
    RETRY_DELAY,
    CANDLE_LIMIT,
)


# ==========================================
# Request
# ==========================================

def request_json(url, params=None):

    for _ in range(REQUEST_RETRIES):

        try:

            r = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            if r.status_code == 200:
                return r.json()

        except Exception:
            pass

        time.sleep(RETRY_DELAY)

    raise Exception("Binance request failed")


# ==========================================
# Candles
# ==========================================

def get_candles(
    symbol,
    interval,
    limit=CANDLE_LIMIT,
):

   
    
    url = f"{BASE_URL}/api/v3/klines"

    data = request_json(
        url,
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )

    

    if not data:
        raise Exception(f"No data for {symbol} {interval}")
    
    df = pd.DataFrame(
        data,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )

  

    df["open_time"] = pd.to_datetime(
        df["open_time"],
        unit="ms",
    )

    df["close_time"] = pd.to_datetime(
        df["close_time"],
        unit="ms",
    )

    numeric = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for col in numeric:
        df[col] = df[col].astype(float)

   
    
    return df


# ==========================================
# Current Price
# ==========================================

def get_price(symbol):

    url = f"{BASE_URL}/api/v3/ticker/price"

    data = request_json(
        url,
        {
            "symbol": symbol,
        },
    )

    return float(data["price"])


# ==========================================
# Multiple Timeframes
# ==========================================

def get_multi_tf(symbol):

    return {
        "15m": get_candles(symbol, "15m"),
        "1h": get_candles(symbol, "1h"),
        "4h": get_candles(symbol, "4h"),
    }
