from indicators import (
    ema,
    rsi,
    atr,
    momentum,
    volume_ma,
    atr_percent,
    trend_strength,
)

from config import (
    EMA_FAST,
    EMA_SLOW,
    EMA_TREND,
    RSI_PERIOD,
    ATR_PERIOD,
    RSI_MIN,
    RSI_MAX,
    VOLUME_MULTIPLIER,
    MIN_SCORE,
    MAX_GREEN_CANDLE,
    MIN_ATR_PERCENT,
    MAX_ATR_PERCENT,
)


def analyze(df):

    x = df.copy()

    x["ema_fast"] = ema(x["close"], EMA_FAST)
    x["ema_slow"] = ema(x["close"], EMA_SLOW)
    x["ema_trend"] = ema(x["close"], EMA_TREND)

    x["rsi"] = rsi(x["close"], RSI_PERIOD)

    x["atr"] = atr(x, ATR_PERIOD)

    x["vol_ma"] = volume_ma(x["volume"])

    x["momentum"] = momentum(x["close"])

    x["atr_pct"] = atr_percent(
        x["close"],
        x["atr"],
    )

    x["trend_strength"] = trend_strength(
        x["ema_fast"],
        x["ema_slow"],
    )

    row = x.iloc[-2]
    prev = x.iloc[-3]

    needed = [
        "ema_fast",
        "ema_slow",
        "ema_trend",
        "rsi",
        "atr",
        "vol_ma",
        "momentum",
        "atr_pct",
        "trend_strength",
    ]

    if row[needed].isna().any():
        return {
            "signal": "WAIT"
        }
        
    # ==========================
    # Filters
    # ==========================

    score = 0

    trend_fast = row["ema_fast"] > row["ema_slow"]
    trend_main = row["ema_slow"] > row["ema_trend"]

    if trend_fast:
        score += 2

    if trend_main:
        score += 2

    rsi_ok = RSI_MIN <= row["rsi"] <= RSI_MAX

    if rsi_ok:
        score += 1

    volume_ok = (
        row["volume"] >=
        row["vol_ma"] * VOLUME_MULTIPLIER
    )

    if volume_ok:
        score += 1

    momentum_ok = row["momentum"] > 0

    if momentum_ok:
        score += 1

    price_ok = row["close"] > row["ema_fast"]

    if price_ok:
        score += 1

    atr_ok = (
        MIN_ATR_PERCENT <= row["atr_pct"] <= MAX_ATR_PERCENT
    )

    if atr_ok:
        score += 1

    trend_ok = row["trend_strength"] > 0.20

    if trend_ok:
        score += 1

    candle_gain = (
        row["close"] - row["open"]
    ) / row["open"]

    candle_ok = candle_gain <= MAX_GREEN_CANDLE

    if candle_ok:
        score += 1

    # ==========================
    # Final Decision
    # ==========================

    if score >= MIN_SCORE:
        signal = "BUY"
    elif score >= (MIN_SCORE - 1):
        signal = "WATCH"
    else:
        signal = "WAIT"

    confidence = round((score / 11) * 100, 1)

    reasons = []

    if not trend_fast:
        reasons.append("EMA20 < EMA50")

    if not trend_main:
        reasons.append("EMA50 < EMA200")

    if not rsi_ok:
        reasons.append("RSI")

    if not volume_ok:
        reasons.append("LOW_VOLUME")

    if not momentum_ok:
        reasons.append("MOMENTUM")

    if not price_ok:
        reasons.append("PRICE_BELOW_EMA")

    if not atr_ok:
        reasons.append("ATR")

    if not trend_ok:
        reasons.append("WEAK_TREND")

    if not candle_ok:
        reasons.append("BIG_GREEN_CANDLE")

    return {
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "close": float(row["close"]),
        "atr": float(row["atr"]),
        "atr_pct": float(row["atr_pct"]),
        "rsi": float(row["rsi"]),
        "trend_strength": float(row["trend_strength"]),
        "momentum": float(row["momentum"]),
        "volume": float(row["volume"]),
        "volume_ma": float(row["vol_ma"]),
        "reasons": reasons,
        "candle_time": row["open_time"].isoformat(),
    }
