import time
import requests
import pandas as pd

from config import (
    BASE_URL,
    INTERVAL,
    CANDLE_LIMIT,
    REQUEST_TIMEOUT,
    REQUEST_RETRIES,
    RETRY_DELAY,
)

session = requests.Session()


def _request(endpoint, params):
    url = f"{BASE_URL}{endpoint}"

    last_error = None

    for attempt in range(REQUEST_RETRIES):
        try:
            r = session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT
            )

            r.raise_for_status()

            return r.json()

        except requests.RequestException as e:
            last_error = e

            if attempt < REQUEST_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    raise RuntimeError(f"Binance API error: {last_error}")


def get_candles(symbol):
    rows = _request(
        "/api/v3/klines",
        {
            "symbol": symbol,
            "interval": INTERVAL,
            "limit": CANDLE_LIMIT,
        },
    )

    cols = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_base",
        "taker_quote",
        "ignore",
    ]

    df = pd.DataFrame(rows, columns=cols)

    numeric = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["open_time"] = pd.to_datetime(
        df["open_time"],
        unit="ms",
        utc=True,
    )

    return df


def get_price(symbol):
    data = _request(
        "/api/v3/ticker/price",
        {
            "symbol": symbol,
        },
    )

    return float(data["price"])
