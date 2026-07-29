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

    score = 0

    trend_fast = row["ema_fast"] > row["ema_slow"]
    trend_main = row["ema_slow"] > row["ema_trend"]

    rsi_ok = 50 <= row["rsi"] <= 60

    volume_ok = (
        row["volume"] >=
        row["vol_ma"] * 1.30
    )

    momentum_ok = row["momentum"] > 0.003

    price_ok = row["close"] > row["ema_fast"]

    atr_ok = (
        MIN_ATR_PERCENT <= row["atr_pct"] <= 0.03
    )

    trend_ok = row["trend_strength"] > 0.40

    candle_gain = (
        row["close"] - row["open"]
    ) / row["open"]

    candle_ok = candle_gain <= 0.015

    # ==========================
    # Mandatory filters
    # ==========================
    
    # Основният тренд трябва да е възходящ
    if not trend_fast:
        return {
            "signal": "WAIT",
            "score": 0,
            "confidence": 0,
            "candle_time": row["open_time"].isoformat(),
        }
    
    if not trend_main:
        return {
            "signal": "WAIT",
            "score": 0,
            "confidence": 0,
            "candle_time": row["open_time"].isoformat(),
        }
    
    # Не купуваме при слаб обем
    if not volume_ok:
        return {
            "signal": "WAIT",
            "score": 0,
            "confidence": 0,
            "candle_time": row["open_time"].isoformat(),
        }
    
    # Не купуваме без положителен momentum
    if not momentum_ok:
        return {
            "signal": "WAIT",
            "score": 0,
            "confidence": 0,
            "candle_time": row["open_time"].isoformat(),
        }
    
    # ==========================
    # Score
    # ==========================
    
    score = 0
    
    if trend_fast:
        score += 3
    
    if trend_main:
        score += 3
    
    if rsi_ok:
        score += 2
    
    if volume_ok:
        score += 2
    
    if momentum_ok:
        score += 2
    
    if price_ok:
        score += 1
    
    if atr_ok:
        score += 1
    
    if trend_ok:
        score += 2
    
    if candle_ok:
        score += 1
    
    # ==========================
    # Final Decision
    # ==========================
    
    MAX_SCORE = 17
    confidence = round((score / MAX_SCORE) * 100, 1)
    
    if score >= 13:
        signal = "BUY"
    elif score >= 10:
        signal = "WATCH"
    else:
        signal = "WAIT"
    
    reasons = []
    
    if not trend_fast:
        reasons.append("EMA20<EMA50")
    
    if not trend_main:
        reasons.append("EMA50<EMA200")
    
    if not rsi_ok:
        reasons.append("RSI")
    
    if not volume_ok:
        reasons.append("LOW_VOLUME")
    
    if not momentum_ok:
        reasons.append("MOMENTUM")
    
    if not price_ok:
        reasons.append("PRICE_BELOW_EMA20")
    
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
