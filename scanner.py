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


# =========================================================
# HELPERS
# =========================================================

def _num(value):
    try:
        value = float(value)

        if math.isfinite(value):
            return value

    except Exception:
        pass

    return None


def _safe_ratio(a, b):
    try:
        if b and float(b) > 0:
            return float(a) / float(b)
    except Exception:
        pass

    return 0.0


# =========================================================
# ANALYZE SYMBOL
# =========================================================

def analyze_symbol(symbol):

    try:

        # -------------------------------------------------
        # MARKET DATA
        # -------------------------------------------------

        low = get_candles(
            symbol,
            LOWER_TIMEFRAME
        )

        high = get_candles(
            symbol,
            HIGHER_TIMEFRAME
        )

        if low is None or high is None:
            return None

        if len(low) < 220 or len(high) < 220:
            return None

        lc = low["close"]
        hc = high["close"]

        # -------------------------------------------------
        # EMA
        # -------------------------------------------------

        low_fast = ema(
            lc,
            EMA_FAST
        )

        low_slow = ema(
            lc,
            EMA_SLOW
        )

        low_trend = ema(
            lc,
            EMA_TREND
        )

        high_fast = ema(
            hc,
            EMA_FAST
        )

        high_slow = ema(
            hc,
            EMA_SLOW
        )

        high_trend = ema(
            hc,
            EMA_TREND
        )

        # -------------------------------------------------
        # INDICATORS
        # -------------------------------------------------

        low_rsi = rsi(
            lc,
            RSI_PERIOD
        )

        low_atr = atr(
            low,
            ATR_PERIOD
        )

        low_mom = momentum(
            lc,
            5
        )

        vol_ma = volume_ma(
            low["volume"],
            VOLUME_PERIOD
        )

        macd_line, macd_signal, macd_hist = macd(
            lc
        )

        adx_v = adx(
            low,
            14
        )

        # -------------------------------------------------
        # LAST CANDLE
        # -------------------------------------------------

        i = -1

        price = _num(
            lc.iloc[i]
        )

        if price is None or price <= 0:
            return None

        a = _num(
            low_atr.iloc[i]
        )

        if a is None or a <= 0:
            return None

        r = _num(
            low_rsi.iloc[i]
        )

        mom = _num(
            low_mom.iloc[i]
        )

        ts = _num(
            trend_strength(
                low_fast,
                low_slow
            ).iloc[i]
        )

        adx_now = _num(
            adx_v.iloc[i]
        ) or 0.0

        hist_now = _num(
            macd_hist.iloc[i]
        ) or 0.0

        volume_now = _num(
            low["volume"].iloc[i]
        ) or 0.0

        volume_average = _num(
            vol_ma.iloc[i]
        ) or 0.0

        if r is None:
            return None

        if mom is None:
            return None

        if ts is None:
            return None

        # -------------------------------------------------
        # ATR %
        # -------------------------------------------------

        atr_pct = a / price

        # -------------------------------------------------
        # VOLUME RATIO
        # -------------------------------------------------

        vol_ratio = _safe_ratio(
            volume_now,
            volume_average
        )

        # -------------------------------------------------
        # HTF TREND
        # -------------------------------------------------

        high_close = _num(
            hc.iloc[i]
        )

        high_trend_now = _num(
            high_trend.iloc[i]
        )

        high_fast_now = _num(
            high_fast.iloc[i]
        )

        high_slow_now = _num(
            high_slow.iloc[i]
        )

        if (
            high_close is None
            or high_trend_now is None
            or high_fast_now is None
            or high_slow_now is None
        ):
            return None

        htf_bull = (
            high_close > high_trend_now
            and high_fast_now > high_slow_now
        )

        # -------------------------------------------------
        # LTF TREND
        # -------------------------------------------------

        low_trend_now = _num(
            low_trend.iloc[i]
        )

        low_fast_now = _num(
            low_fast.iloc[i]
        )

        low_slow_now = _num(
            low_slow.iloc[i]
        )

        if (
            low_trend_now is None
            or low_fast_now is None
            or low_slow_now is None
        ):
            return None

        ltf_bull = (
            price > low_trend_now
            and low_fast_now > low_slow_now
        )

        # -------------------------------------------------
        # CANDLE BODY
        # -------------------------------------------------

        open_price = _num(
            low["open"].iloc[i]
        )

        if open_price is None or open_price <= 0:
            return None

        candle_body = abs(
            price - open_price
        ) / open_price

        # =================================================
        # HARD FILTERS
        # =================================================

        # ATR must be healthy
        if not (
            MIN_ATR_PERCENT
            <= atr_pct
            <= MAX_ATR_PERCENT
        ):
            return None

        # BOTH timeframes must agree
        if not htf_bull:
            return None

        if not ltf_bull:
            return None

        # RSI
        if not (
            RSI_MIN
            <= r
            <= RSI_MAX
        ):
            return None

        # Momentum
        if mom < MIN_MOMENTUM:
            return None

        # Trend strength
        if ts < MIN_TREND_STRENGTH:
            return None

        # Volume
        if vol_ratio < VOLUME_MULTIPLIER:
            return None

        # Avoid oversized candles
        if candle_body > MAX_GREEN_CANDLE:
            return None

        # MACD must be positive
        if hist_now <= 0:
            return None

        # ADX must show a real trend
        if adx_now < 20:
            return None

        # =================================================
        # QUALITY SCORE
        # =================================================

        score = 0

        reasons = []

        # -------------------------------------------------
        # HTF TREND
        # -------------------------------------------------

        if htf_bull:

            score += 20
            reasons.append("HTF")

        # -------------------------------------------------
        # LTF TREND
        # -------------------------------------------------

        if ltf_bull:

            score += 20
            reasons.append("LTF")

        # -------------------------------------------------
        # RSI
        # -------------------------------------------------

        if 55 <= r <= 65:

            score += 15
            reasons.append("RSI+")

        elif 52 <= r <= 68:

            score += 10
            reasons.append("RSI")

        # -------------------------------------------------
        # MOMENTUM
        # -------------------------------------------------

        if mom >= 0.006:

            score += 15
            reasons.append("MOM+")

        elif mom >= 0.003:

            score += 10
            reasons.append("MOM")

        else:

            score += 5

        # -------------------------------------------------
        # ADX
        # -------------------------------------------------

        if adx_now >= 30:

            score += 15
            reasons.append("ADX+")

        elif adx_now >= 25:

            score += 10
            reasons.append("ADX")

        else:

            score += 5

        # -------------------------------------------------
        # MACD
        # -------------------------------------------------

        if hist_now > 0:

            score += 10
            reasons.append("MACD")

        # -------------------------------------------------
        # VOLUME
        # -------------------------------------------------

        if vol_ratio >= 1.50:

            score += 10
            reasons.append("VOL+")

        elif vol_ratio >= 1.20:

            score += 7
            reasons.append("VOL")

        # -------------------------------------------------
        # CANDLE QUALITY
        # -------------------------------------------------

        if candle_body <= MAX_GREEN_CANDLE * 0.70:

            score += 5
            reasons.append("CANDLE")

        # -------------------------------------------------
        # LIMIT
        # -------------------------------------------------

        score = min(
            score,
            100
        )

        # =================================================
        # QUALITY
        # =================================================

        if score >= 95:

            quality = "A+"

        elif score >= 90:

            quality = "A"

        elif score >= 80:

            quality = "B"

        else:

            quality = "C"

        # =================================================
        # CONFIDENCE
        # =================================================

        confidence_points = 0
        max_points = 7

        if htf_bull:
            confidence_points += 1

        if ltf_bull:
            confidence_points += 1

        if 52 <= r <= 68:
            confidence_points += 1

        if mom >= 0.003:
            confidence_points += 1

        if adx_now >= 25:
            confidence_points += 1

        if hist_now > 0:
            confidence_points += 1

        if vol_ratio >= 1.20:
            confidence_points += 1

        confidence = round(
            (confidence_points / max_points) * 100
        )

        # =================================================
        # SIGNAL
        # =================================================

        # IMPORTANT:
        # BUY only for very strong setups.
        #
        # This is what gives us:
        # "few but quality signals"

        if (
            score >= 90
            and confidence >= 85
            and htf_bull
            and ltf_bull
            and adx_now >= 25
            and hist_now > 0
            and vol_ratio >= 1.20
            and mom >= 0.003
        ):

            signal_type = "BUY"

        elif score >= 75:

            signal_type = "WATCH"

        else:

            return None

        # =================================================
        # RESULT
        # =================================================

        return {

            "symbol": symbol,

            "signal": signal_type,

            "score": score,

            "confidence": confidence,

            "quality": quality,

            "close": price,

            "atr": a,

            "atr_pct": atr_pct,

            "trend_strength": ts,

            "momentum": mom,

            "volume": volume_now,

            "volume_ma": volume_average,

            "volume_ratio": vol_ratio,

            "rsi": r,

            "adx": adx_now,

            "macd_hist": hist_now,

            "htf_bull": htf_bull,

            "ltf_bull": ltf_bull,

            "candle_body": candle_body,

            "reasons": reasons,

        }

    except Exception as exc:

        print(
            f"[SCAN ERROR] "
            f"{symbol}: {exc}"
        )

        return None


# =========================================================
# MARKET SCANNER
# =========================================================

def scan_market():

    signals = []

    checked = 0

    buy_count = 0

    watch_count = 0

    for symbol in SYMBOLS:

        checked += 1

        result = analyze_symbol(
            symbol
        )

        if result is None:
            continue

        signals.append(
            result
        )

        if result["signal"] == "BUY":

            buy_count += 1

        elif result["signal"] == "WATCH":

            watch_count += 1

    # =====================================================
    # SORT
    # =====================================================

    signals.sort(

        key=lambda x: (

            x.get(
                "score",
                0
            ),

            x.get(
                "confidence",
                0
            ),

            x.get(
                "adx",
                0
            ),

            x.get(
                "momentum",
                0
            ),

            x.get(
                "volume_ratio",
                0
            ),

        ),

        reverse=True

    )

    # =====================================================
    # LOG
    # =====================================================

    print(
        f"[SCAN] "
        f"Checked={checked} "
        f"Candidates={len(signals)} "
        f"BUY={buy_count} "
        f"WATCH={watch_count}"
    )

    if signals:

        top = signals[0]

        print(
            f"[TOP] "
            f"{top['symbol']} "
            f"{top['signal']} "
            f"Score={top['score']} "
            f"RSI={top['rsi']:.1f} "
            f"ADX={top['adx']:.1f} "
            f"MOM={top['momentum']:.4f} "
            f"VOL={top['volume_ratio']:.2f} "
            f"HTF={top['htf_bull']} "
            f"LTF={top['ltf_bull']} "
            f"CONF={top['confidence']} "
            f"Q={top['quality']}"
        )

        if top.get("reasons"):

            print(
                "[REASONS] "
                + ", ".join(
                    top["reasons"]
                )
            )

    return signals
