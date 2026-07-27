from indicators import ema, rsi, atr
from config import (
    EMA_FAST, EMA_SLOW, RSI_PERIOD, ATR_PERIOD,
    RSI_BUY_MIN, RSI_BUY_MAX, VOLUME_MULTIPLIER
)

def analyze(df):
    x = df.copy()
    x["ema_fast"] = ema(x["close"], EMA_FAST)
    x["ema_slow"] = ema(x["close"], EMA_SLOW)
    x["rsi"] = rsi(x["close"], RSI_PERIOD)
    x["atr"] = atr(x, ATR_PERIOD)
    x["vol_ma"] = x["volume"].rolling(20).mean()

    # Use the last CLOSED candle, not the currently forming candle.
    row = x.iloc[-2]
    prev = x.iloc[-3]

    needed = ["ema_fast","ema_slow","rsi","atr","vol_ma"]
    if any(row[k] != row[k] for k in needed):
        return {"signal": "WAIT"}

    trend = row["ema_fast"] > row["ema_slow"]
    momentum = RSI_BUY_MIN <= row["rsi"] <= RSI_BUY_MAX
    volume_ok = row["volume"] >= row["vol_ma"] * VOLUME_MULTIPLIER
    price_ok = row["close"] > row["ema_fast"]
    rising = row["close"] > prev["close"]

    score = sum([trend, momentum, volume_ok, price_ok, rising])

    return {
        "signal": "BUY" if score >= 4 else "WAIT",
        "score": score,
        "close": float(row["close"]),
        "atr": float(row["atr"]),
        "rsi": float(row["rsi"]),
        "candle_time": row["open_time"].isoformat(),
    }
