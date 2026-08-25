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
# SAFE HELPERS
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
        a = float(a)
        b = float(b)

        if b > 0:
            return a / b

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

        # -------------------------------------------------
        # CLOSE DATA
        # -------------------------------------------------

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

        _, _, macd_hist = macd(lc)

        adx_v = adx(
            low,
            14
        )

        # -------------------------------------------------
        # LAST VALUES
        # -------------------------------------------------

        i = -1

        price = _num(
            lc.iloc[i]
        )

        a = _num(
            low_atr.iloc[i]
        )

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

        adx_now = (
            _num(adx_v.iloc[i])
            or 0.0
        )

        hist_now = (
            _num(macd_hist.iloc[i])
            or 0.0
        )

        volume_now = (
            _num(low["volume"].iloc[i])
            or 0.0
        )

        volume_average = (
            _num(vol_ma.iloc[i])
            or 0.0
        )

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if price is None or price <= 0:
            return None

        if a is None or a <= 0:
            return None

        if r is None:
            return None

        if mom is None:
            return None

        if ts is None:
            return None

        # -------------------------------------------------
        # ATR
        #
        # IMPORTANT:
        # ATR IS NO LONGER A HARD REJECTION.
        # It becomes a scoring factor.
        # -------------------------------------------------

        atr_pct = a / price

        atr_valid = (
            MIN_ATR_PERCENT
            <= atr_pct
            <= MAX_ATR_PERCENT
        )

        # -------------------------------------------------
        # HTF / LTF VALUES
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

        low_trend_now = _num(
            low_trend.iloc[i]
        )

        low_fast_now = _num(
            low_fast.iloc[i]
        )

        low_slow_now = _num(
            low_slow.iloc[i]
        )

        if None in (
            high_close,
            high_trend_now,
            high_fast_now,
            high_slow_now,
            low_trend_now,
            low_fast_now,
            low_slow_now,
        ):
            return None

        # -------------------------------------------------
        # TREND
        # -------------------------------------------------

        htf_bull = (
            high_close > high_trend_now
            and high_fast_now > high_slow_now
        )

        ltf_bull = (
            price > low_trend_now
            and low_fast_now > low_slow_now
        )

        # -------------------------------------------------
        # CANDLE
        # -------------------------------------------------

        open_price = _num(
            low["open"].iloc[i]
        )

        if open_price is None or open_price <= 0:
            return None

        candle_body = (
            abs(price - open_price)
            / open_price
        )

        # -------------------------------------------------
        # VOLUME
        # -------------------------------------------------

        vol_ratio = _safe_ratio(
            volume_now,
            volume_average
        )

        # =================================================
        # SCORE
        # =================================================

        score = 0

        reasons = []

        # -------------------------------------------------
        # HTF
        # -------------------------------------------------

        if htf_bull:

            score += 20
            reasons.append("HTF")

        # -------------------------------------------------
        # LTF
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

        elif RSI_MIN <= r <= RSI_MAX:

            score += 10
            reasons.append("RSI")

        elif 45 <= r < RSI_MIN:

            score += 5
            reasons.append("RSI-WEAK")

        # -------------------------------------------------
        # RSI TOO HIGH
        # -------------------------------------------------

        if r > 68:

            score -= 8
            reasons.append("RSI-HIGH")

        # -------------------------------------------------
        # MOMENTUM
        # -------------------------------------------------

        if mom >= 0.006:

            score += 15
            reasons.append("MOM+")

        elif mom >= max(
            0.003,
            MIN_MOMENTUM
        ):

            score += 10
            reasons.append("MOM")

        elif mom >= MIN_MOMENTUM * 0.75:

            score += 5
            reasons.append("MOM-WEAK")

        else:

            score -= 6
            reasons.append("MOM-LOW")

        # -------------------------------------------------
        # ADX
        # -------------------------------------------------

        if adx_now >= 30:

            score += 15
            reasons.append("ADX+")

        elif adx_now >= 25:

            score += 10
            reasons.append("ADX")

        elif adx_now >= 20:

            score += 5
            reasons.append("ADX-WEAK")

        else:

            # Do not reject.
            # Just don't reward weak trend.
            reasons.append("ADX-LOW")

        # -------------------------------------------------
        # MACD
        # -------------------------------------------------

        if hist_now > 0:

            score += 10
            reasons.append("MACD")

        elif hist_now >= 0:

            score += 5
            reasons.append("MACD-FLAT")

        else:

            score -= 6
            reasons.append("MACD-NEG")

        # -------------------------------------------------
        # VOLUME
        # -------------------------------------------------

        if vol_ratio >= 1.50:

            score += 10
            reasons.append("VOL+")

        elif vol_ratio >= 1.20:

            score += 7
            reasons.append("VOL")

        elif vol_ratio >= 1.00:

            score += 4
            reasons.append("VOL-NORMAL")

        else:

            reasons.append("VOL-LOW")

        # -------------------------------------------------
        # ATR
        #
        # ATR DOES NOT REJECT THE SYMBOL.
        # It only affects the score.
        # -------------------------------------------------

        if atr_valid:

            score += 5
            reasons.append("ATR")

        elif atr_pct < MIN_ATR_PERCENT:

            reasons.append("ATR-LOW")

        else:

            reasons.append("ATR-HIGH")

        # -------------------------------------------------
        # CANDLE
        # -------------------------------------------------

        if candle_body <= MAX_GREEN_CANDLE * 0.70:

            score += 5
            reasons.append("CANDLE")

        elif candle_body <= MAX_GREEN_CANDLE:

            score += 3
            reasons.append("CANDLE-WEAK")

        else:

            score -= 8
            reasons.append("CANDLE-LARGE")

        # -------------------------------------------------
        # FINAL SCORE LIMIT
        # -------------------------------------------------

        score = max(
            0,
            min(
                100,
                int(round(score))
            )
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

        elif score >= 70:

            quality = "C"

        else:

            quality = "D"

        # =================================================
        # CONFIDENCE
        # =================================================

        confidence_points = 0

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
            (
                confidence_points
                / 7
            ) * 100
        )

        # =================================================
        # BUY THRESHOLD
        #
        # Respect config.py.
        # Do NOT force it to 90.
        # =================================================

        buy_score = int(
            BUY_SCORE
        )

        # Safety floor
        buy_score = max(
            70,
            min(
                95,
                buy_score
            )
        )

        # =================================================
        # BUY CONDITIONS
        #
        # Score alone is NOT enough.
        # =================================================

        strong_buy = (
            score >= buy_score
            and confidence >= 85
            and htf_bull
            and ltf_bull
            and adx_now >= 20
            and hist_now > 0
            and vol_ratio >= 1.15
            and mom >= 0.003
            and r <= 68
            and candle_body <= MAX_GREEN_CANDLE
        )

        if strong_buy:

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

            "atr_valid": atr_valid,

            "reasons": reasons,

        }

    except Exception as exc:

        print(
            f"[SCAN ERROR] {symbol}: {exc}"
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

    # Diagnostic counters
    data_fail = 0
    atr_low = 0
    atr_high = 0
    score_low = 0

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
            x.get("score", 0),
            x.get("confidence", 0),
            x.get("adx", 0),
            x.get("momentum", 0),
            x.get("volume_ratio", 0),
        ),
        reverse=True,
    )

    # =====================================================
    # SCAN SUMMARY
    # =====================================================

    print(
        f"[SCAN] "
        f"Checked={checked} "
        f"Candidates={len(signals)} "
        f"BUY={buy_count} "
        f"WATCH={watch_count}"
    )

    # =====================================================
    # TOP CANDIDATE
    # =====================================================

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

    else:

        print(
            "[SCAN] No qualifying candidates."
        )

    return signals
