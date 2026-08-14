import math
from config import (
    SYMBOLS, LOWER_TIMEFRAME, HIGHER_TIMEFRAME,
    EMA_FAST, EMA_SLOW, EMA_TREND, RSI_PERIOD,
    RSI_MIN, RSI_MAX, ATR_PERIOD, MIN_ATR_PERCENT,
    MAX_ATR_PERCENT, VOLUME_PERIOD, VOLUME_MULTIPLIER,
    MIN_MOMENTUM, MIN_TREND_STRENGTH, MAX_GREEN_CANDLE,
    BUY_SCORE
)
from indicators import ema, rsi, atr, momentum, volume_ma, trend_strength, macd, adx
from market_data import get_candles

def _num(v):
    return float(v) if v == v and math.isfinite(float(v)) else None

def analyze_symbol(symbol):
    try:
        low = get_candles(symbol, LOWER_TIMEFRAME)
        high = get_candles(symbol, HIGHER_TIMEFRAME)

        if len(low) < 220 or len(high) < 220:
            return None

        lc = low["close"]
        hc = high["close"]

        low_fast = ema(lc, EMA_FAST)
        low_slow = ema(lc, EMA_SLOW)
        low_trend = ema(lc, EMA_TREND)
        high_fast = ema(hc, EMA_FAST)
        high_slow = ema(hc, EMA_SLOW)
        high_trend = ema(hc, EMA_TREND)

        low_rsi = rsi(lc, RSI_PERIOD)
        low_atr = atr(low, ATR_PERIOD)
        low_mom = momentum(lc, 5)
        vol_ma = volume_ma(low["volume"], VOLUME_PERIOD)
        macd_line, macd_signal, macd_hist = macd(lc)
        adx_v = adx(low, 14)

        i = -1
        price = float(lc.iloc[i])
        a = _num(low_atr.iloc[i])
        if a is None or price <= 0:
            return None

        atr_pct = a / price
        vol_ratio = float(low["volume"].iloc[i] / vol_ma.iloc[i]) if vol_ma.iloc[i] > 0 else 0
        mom = float(low_mom.iloc[i])
        ts = float(trend_strength(low_fast, low_slow).iloc[i])
        r = float(low_rsi.iloc[i])
        htf_bull = (
            hc.iloc[i] > high_trend.iloc[i]
            and high_fast.iloc[i] > high_slow.iloc[i]
        )
        ltf_bull = (
            price > low_trend.iloc[i]
            and low_fast.iloc[i] > low_slow.iloc[i]
        )

        candle_body = abs(float(low["close"].iloc[i] - low["open"].iloc[i])) / float(low["open"].iloc[i])
        adx_now = _num(adx_v.iloc[i]) or 0
        hist_now = float(macd_hist.iloc[i])

        if not (MIN_ATR_PERCENT <= atr_pct <= MAX_ATR_PERCENT):
            return None
        if not htf_bull or not ltf_bull:
            return None
        if not (RSI_MIN <= r <= RSI_MAX):
            return None
        if mom < MIN_MOMENTUM:
            return None
        if ts < MIN_TREND_STRENGTH:
            return None
        if vol_ratio < VOLUME_MULTIPLIER:
            return None
        if candle_body > MAX_GREEN_CANDLE:
            return None
        if hist_now <= 0:
            return None
        if adx_now < 18:
            return None

        score = 0
        score += 25  # HTF trend
        score += 20  # LTF trend
        score += 15 if r >= 55 else 8
        score += 15 if vol_ratio >= 1.25 else 8
        score += 10 if mom >= 0.004 else 5
        score += 10 if adx_now >= 25 else 5
        score += 5 if hist_now > 0 else 0
        score = min(score, 100)

        confidence = score

        return {
            "symbol": symbol,
            "signal": "BUY" if score >= BUY_SCORE else "WATCH",
            "score": score,
            "confidence": confidence,
            "quality": "A" if score >= 85 else "B" if score >= 75 else "C",
            "close": price,
            "atr": a,
            "trend_strength": ts,
            "momentum": mom,
            "volume": float(low["volume"].iloc[i]),
            "volume_ma": float(vol_ma.iloc[i]),
            "rsi": r,
            "adx": adx_now,
        }
    except Exception as exc:
        print(f"[SCAN ERROR] {symbol}: {exc}")
        return None

def scan_market():
    signals = []
    for symbol in SYMBOLS:
        result = analyze_symbol(symbol)
        if result:
            signals.append(result)

    signals.sort(key=lambda x: (x["score"], x["momentum"], x["volume"]), reverse=True)
    return signals
