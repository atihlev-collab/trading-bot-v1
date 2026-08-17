import math

from config import (
    SYMBOLS,
    LOWER_TIMEFRAME,
    HIGHER_TIMEFRAME,
    EMA_FAST,
    EMA_SLOW,
    EMA_TREND,
    RSI_PERIOD,
    RSI_MIN,
    RSI_MAX,
    ATR_PERIOD,
    MIN_ATR_PERCENT,
    MAX_ATR_PERCENT,
    VOLUME_PERIOD,
    VOLUME_MULTIPLIER,
    MIN_MOMENTUM,
    MIN_TREND_STRENGTH,
    MAX_GREEN_CANDLE,
    BUY_SCORE,
)

from indicators import (
    ema,
    rsi,
    atr,
    momentum,
    volume_ma,
    trend_strength,
    macd,
    adx,
)

from market_data import get_candles


# ============================================================
# SAFE NUMBER
# ============================================================

def _num(value):
    try:
        value = float(value)

        if math.isfinite(value):
            return value

        return None

    except Exception:
        return None


# ============================================================
# ANALYZE SYMBOL
# ============================================================

def analyze_symbol(symbol):

    try:

        # ----------------------------------------------------
        # LOAD DATA
        # ----------------------------------------------------

        low = get_candles(symbol, LOWER_TIMEFRAME)
        high = get_candles(symbol, HIGHER_TIMEFRAME)

        if low is None or high is None:
            return None

        if len(low) < 220 or len(high) < 220:
            return None

        lc = low["close"]
        hc = high["close"]

        # ----------------------------------------------------
        # EMAs
        # ----------------------------------------------------

        low_fast = ema(lc, EMA_FAST)
        low_slow = ema(lc, EMA_SLOW)
        low_trend = ema(lc, EMA_TREND)

        high_fast = ema(hc, EMA_FAST)
        high_slow = ema(hc, EMA_SLOW)
        high_trend = ema(hc, EMA_TREND)

        # ----------------------------------------------------
        # INDICATORS
        # ----------------------------------------------------

        low_rsi = rsi(lc, RSI_PERIOD)
        low_atr = atr(low, ATR_PERIOD)
        low_mom = momentum(lc, 5)

        vol_ma = volume_ma(
            low["volume"],
            VOLUME_PERIOD
        )

        macd_line, macd_signal, macd_hist = macd(lc)

        adx_v = adx(low, 14)

        low_ts = trend_strength(
            low_fast,
            low_slow
        )

        # ----------------------------------------------------
        # CURRENT VALUES
        # ----------------------------------------------------

        i = -1

        price = _num(lc.iloc[i])
        a = _num(low_atr.iloc[i])
        r = _num(low_rsi.iloc[i])
        mom = _num(low_mom.iloc[i])
        ts = _num(low_ts.iloc[i])
        adx_now = _num(adx_v.iloc[i])
        hist_now = _num(macd_hist.iloc[i])

        if (
            price is None
            or a is None
            or r is None
            or mom is None
            or ts is None
            or adx_now is None
            or hist_now is None
        ):
            return None

        if price <= 0 or a <= 0:
            return None

        # ----------------------------------------------------
        # ATR
        # ----------------------------------------------------

        atr_pct = a / price

        if not (
            MIN_ATR_PERCENT
            <= atr_pct
            <= MAX_ATR_PERCENT
        ):
            return None

        # ----------------------------------------------------
        # VOLUME
        # ----------------------------------------------------

        current_volume = _num(
            low["volume"].iloc[i]
        )

        volume_average = _num(
            vol_ma.iloc[i]
        )

        if (
            current_volume is None
            or volume_average is None
            or volume_average <= 0
        ):
            return None

        vol_ratio = current_volume / volume_average

        # ----------------------------------------------------
        # TREND
        # ----------------------------------------------------

        high_price = _num(hc.iloc[i])
        high_trend_value = _num(high_trend.iloc[i])
        high_fast_value = _num(high_fast.iloc[i])
        high_slow_value = _num(high_slow.iloc[i])

        low_trend_value = _num(low_trend.iloc[i])
        low_fast_value = _num(low_fast.iloc[i])
        low_slow_value = _num(low_slow.iloc[i])

        if None in (
            high_price,
            high_trend_value,
            high_fast_value,
            high_slow_value,
            low_trend_value,
            low_fast_value,
            low_slow_value,
        ):
            return None

        # Higher timeframe trend
        htf_bull = (
            high_price > high_trend_value
            and high_fast_value > high_slow_value
        )

        # Lower timeframe trend
        ltf_bull = (
            price > low_trend_value
            and low_fast_value > low_slow_value
        )

        # ----------------------------------------------------
        # CANDLE
        # ----------------------------------------------------

        candle_open = _num(
            low["open"].iloc[i]
        )

        candle_close = _num(
            low["close"].iloc[i]
        )

        if (
            candle_open is None
            or candle_close is None
            or candle_open <= 0
        ):
            return None

        candle_body = (
            abs(candle_close - candle_open)
            / candle_open
        )

        # ----------------------------------------------------
        # HARD QUALITY FILTERS
        # ----------------------------------------------------

        # We want the bigger trend to agree.
        if not htf_bull:
            return None

        # We also want the entry timeframe aligned.
        if not ltf_bull:
            return None

        # Avoid overbought entries.
        if r < max(RSI_MIN, 52):
            return None

        if r > min(RSI_MAX, 68):
            return None

        # Minimum momentum.
        if mom < max(MIN_MOMENTUM, 0.002):
            return None

        # Trend strength.
        if ts < MIN_TREND_STRENGTH:
            return None

        # Volume confirmation.
        if vol_ratio < max(VOLUME_MULTIPLIER, 1.15):
            return None

        # MACD must confirm bullish momentum.
        if hist_now <= 0:
            return None

        # ADX must confirm a real trend.
        if adx_now < 25:
            return None

        # Avoid buying an abnormally large green candle.
        if candle_body > MAX_GREEN_CANDLE:
            return None

        # ----------------------------------------------------
        # QUALITY SCORE
        # ----------------------------------------------------

        score = 0

        # Higher timeframe trend
        score += 25

        # Lower timeframe trend
        score += 20

        # RSI
        if 55 <= r <= 65:
            score += 15
        elif 52 <= r <= 68:
            score += 10

        # Volume
        if vol_ratio >= 1.50:
            score += 15
        elif vol_ratio >= 1.25:
            score += 12
        else:
            score += 8

        # Momentum
        if mom >= 0.004:
            score += 10
        elif mom >= 0.0025:
            score += 8
        else:
            score += 5

        # ADX
        if adx_now >= 30:
            score += 10
        elif adx_now >= 25:
            score += 7
        else:
            score += 5

        # MACD
        if hist_now > 0:
            score += 5

        score = min(score, 100)

        # ----------------------------------------------------
        # BUY THRESHOLD
        # ----------------------------------------------------

        # Main goal:
        # FEWER SIGNALS + BETTER QUALITY
        buy_threshold = max(BUY_SCORE, 85)

        signal = (
            "BUY"
            if score >= buy_threshold
            else "WATCH"
        )

        # ----------------------------------------------------
        # QUALITY
        # ----------------------------------------------------

        if score >= 90:
            quality = "A+"
        elif score >= 85:
            quality = "A"
        elif score >= 78:
            quality = "B"
        elif score >= 70:
            quality = "C"
        else:
            quality = "D"

        confidence = score

        # ----------------------------------------------------
        # CONFIRMATION SCORE
        # ----------------------------------------------------

        confirmations = 0

        if htf_bull:
            confirmations += 1

        if ltf_bull:
            confirmations += 1

        if adx_now >= 25:
            confirmations += 1

        if vol_ratio >= 1.15:
            confirmations += 1

        if hist_now > 0:
            confirmations += 1

        # BUY requires at least 4/5 confirmations.
        if signal == "BUY" and confirmations < 4:
            signal = "WATCH"

        # ----------------------------------------------------
        # DEBUG
        # ----------------------------------------------------

        if signal == "BUY":

            print(
                f"[CANDIDATE] {symbol} BUY "
                f"Score={score} "
                f"RSI={r:.1f} "
                f"ADX={adx_now:.1f} "
                f"MOM={mom:.4f} "
                f"VOL={vol_ratio:.2f} "
                f"HTF={htf_bull} "
                f"LTF={ltf_bull} "
                f"CONF={confirmations}/5"
            )

        # ----------------------------------------------------
        # RETURN
        # ----------------------------------------------------

        return {
            "symbol": symbol,
            "signal": signal,
            "score": score,
            "confidence": confidence,
            "quality": quality,

            "close": price,
            "atr": a,

            "trend_strength": ts,
            "momentum": mom,

            "volume": current_volume,
            "volume_ma": volume_average,

            "rsi": r,
            "adx": adx_now,

            "atr_percent": atr_pct,
            "volume_ratio": vol_ratio,

            "htf_bull": htf_bull,
            "ltf_bull": ltf_bull,

            "macd_hist": hist_now,
            "confirmations": confirmations,
        }

    except Exception as exc:

        print(
            f"[SCAN ERROR] {symbol}: {exc}"
        )

        return None


# ============================================================
# SCAN MARKET
# ============================================================

def scan_market():

    signals = []

    checked = 0
    candidates = 0
    buys = 0
    watches = 0

    for symbol in SYMBOLS:

        checked += 1

        result = analyze_symbol(symbol)

        if not result:
            continue

        candidates += 1

        if result["signal"] == "BUY":
            buys += 1
            signals.append(result)

        elif result["signal"] == "WATCH":
            watches += 1

    # --------------------------------------------------------
    # SORT BEST BUY SIGNALS FIRST
    # --------------------------------------------------------

    signals.sort(
        key=lambda x: (
            x["score"],
            x["confirmations"],
            x["adx"],
            x["momentum"],
            x["volume_ratio"],
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # SCAN SUMMARY
    # --------------------------------------------------------

    print(
        f"[SCAN] Checked={checked} "
        f"Candidates={candidates} "
        f"BUY={buys} "
        f"WATCH={watches}"
    )

    # --------------------------------------------------------
    # TOP BUY
    # --------------------------------------------------------

    if signals:

        top = signals[0]

        print(
            f"[TOP BUY] "
            f"{top['symbol']} "
            f"Score={top['score']} "
            f"Quality={top['quality']} "
            f"RSI={top['rsi']:.1f} "
            f"ADX={top['adx']:.1f} "
            f"MOM={top['momentum']:.4f} "
            f"VOL={top['volume_ratio']:.2f} "
            f"CONF={top['confirmations']}/5"
        )

    return signals
