import math

from config import (
    SYMBOLS, LOWER_TIMEFRAME, HIGHER_TIMEFRAME,
    EMA_FAST, EMA_SLOW, EMA_TREND,
    RSI_PERIOD, RSI_MIN, RSI_MAX,
    ATR_PERIOD, MIN_ATR_PERCENT, MAX_ATR_PERCENT,
    VOLUME_PERIOD, VOLUME_MULTIPLIER,
    MIN_MOMENTUM, MIN_TREND_STRENGTH,
    MAX_GREEN_CANDLE, BUY_SCORE,
)

from indicators import (
    ema, rsi, atr, momentum, volume_ma,
    trend_strength, macd, adx,
)

from market_data import get_candles


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

        if b > 0 and math.isfinite(a) and math.isfinite(b):
            return a / b

    except Exception:
        pass

    return 0.0


def analyze_symbol(symbol):
    try:
        low = get_candles(symbol, LOWER_TIMEFRAME)
        high = get_candles(symbol, HIGHER_TIMEFRAME)

        if low is None or high is None:
            return None

        if len(low) < 220 or len(high) < 220:
            return None

        lc = low["close"]
        hc = high["close"]

        # =========================================================
        # EMA
        # =========================================================

        low_fast = ema(lc, EMA_FAST)
        low_slow = ema(lc, EMA_SLOW)
        low_trend = ema(lc, EMA_TREND)

        high_fast = ema(hc, EMA_FAST)
        high_slow = ema(hc, EMA_SLOW)
        high_trend = ema(hc, EMA_TREND)

        # =========================================================
        # INDICATORS
        # =========================================================

        low_rsi = rsi(lc, RSI_PERIOD)
        low_atr = atr(low, ATR_PERIOD)
        low_mom = momentum(lc, 5)

        vol_ma = volume_ma(
            low["volume"],
            VOLUME_PERIOD
        )

        _, _, macd_hist = macd(lc)
        adx_v = adx(low, 14)

        i = -1

        price = _num(lc.iloc[i])
        a = _num(low_atr.iloc[i])
        r = _num(low_rsi.iloc[i])
        mom = _num(low_mom.iloc[i])

        ts_series = trend_strength(
            low_fast,
            low_slow
        )

        ts = _num(ts_series.iloc[i])

        adx_now = _num(adx_v.iloc[i]) or 0.0
        hist_now = _num(macd_hist.iloc[i]) or 0.0

        volume_now = (
            _num(low["volume"].iloc[i])
            or 0.0
        )

        volume_average = (
            _num(vol_ma.iloc[i])
            or 0.0
        )

        # =========================================================
        # BASIC VALIDATION
        # =========================================================

        if price is None or price <= 0:
            return None

        if a is None or a <= 0:
            return None

        if r is None or mom is None or ts is None:
            return None

        # =========================================================
        # ATR MARKET QUALITY
        # =========================================================

        atr_pct = a / price

        if not (
            MIN_ATR_PERCENT
            <= atr_pct
            <= MAX_ATR_PERCENT
        ):
            return None

        # =========================================================
        # CURRENT EMA VALUES
        # =========================================================

        high_close = _num(hc.iloc[i])

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

        # =========================================================
        # TREND
        # =========================================================

        htf_bull = (
            high_close > high_trend_now
            and high_fast_now > high_slow_now
        )

        ltf_bull = (
            price > low_trend_now
            and low_fast_now > low_slow_now
        )

        # =========================================================
        # CANDLE / VOLUME
        # =========================================================

        open_price = _num(
            low["open"].iloc[i]
        )

        if open_price is None or open_price <= 0:
            return None

        candle_body = (
            abs(price - open_price)
            / open_price
        )

        vol_ratio = _safe_ratio(
            volume_now,
            volume_average
        )

        # =========================================================
        # SCORE
        # =========================================================

        score = 0
        reasons = []

        # ---------------------------------------------------------
        # HTF
        # ---------------------------------------------------------

        if htf_bull:
            score += 20
            reasons.append("HTF")

        elif high_close > high_trend_now:
            score += 10
            reasons.append("HTF-WEAK")

        # ---------------------------------------------------------
        # LTF
        # ---------------------------------------------------------

        if ltf_bull:
            score += 20
            reasons.append("LTF")

        elif price > low_trend_now:
            score += 10
            reasons.append("LTF-WEAK")

        # ---------------------------------------------------------
        # RSI
        # ---------------------------------------------------------

        if 52 <= r <= 64:
            score += 15
            reasons.append("RSI+")

        elif 48 <= r <= 68:
            score += 10
            reasons.append("RSI")

        elif 44 <= r < 48:
            score += 4
            reasons.append("RSI-WEAK")

        else:
            reasons.append("RSI-LOW")

        # ---------------------------------------------------------
        # MOMENTUM
        # ---------------------------------------------------------

        if mom >= 0.006:
            score += 15
            reasons.append("MOM+")

        elif mom >= max(
            0.003,
            MIN_MOMENTUM
        ):
            score += 10
            reasons.append("MOM")

        elif mom >= MIN_MOMENTUM * 0.70:
            score += 5
            reasons.append("MOM-WEAK")

        else:
            reasons.append("MOM-LOW")

        # ---------------------------------------------------------
        # ADX
        # ---------------------------------------------------------

        if adx_now >= 30:
            score += 15
            reasons.append("ADX+")

        elif adx_now >= 25:
            score += 10
            reasons.append("ADX")

        elif adx_now >= 20:
            score += 6
            reasons.append("ADX-WEAK")

        elif adx_now >= 15:
            score += 3
            reasons.append("ADX-LOW")

        else:
            reasons.append("ADX-LOW")

        # ---------------------------------------------------------
        # MACD
        # ---------------------------------------------------------

        if hist_now > 0:
            score += 10
            reasons.append("MACD")

        elif hist_now >= 0:
            score += 5
            reasons.append("MACD-FLAT")

        else:
            reasons.append("MACD-NEG")

        # ---------------------------------------------------------
        # VOLUME
        # ---------------------------------------------------------

        if vol_ratio >= 1.50:
            score += 10
            reasons.append("VOL+")

        elif vol_ratio >= 1.20:
            score += 7
            reasons.append("VOL")

        elif vol_ratio >= 1.00:
            score += 4
            reasons.append("VOL-NORMAL")

        elif vol_ratio >= 0.70:
            score += 2
            reasons.append("VOL-WEAK")

        else:
            reasons.append("VOL-LOW")

        # ---------------------------------------------------------
        # CANDLE
        # ---------------------------------------------------------

        if candle_body <= MAX_GREEN_CANDLE * 0.70:
            score += 5
            reasons.append("CANDLE")

        elif candle_body <= MAX_GREEN_CANDLE:
            score += 3
            reasons.append("CANDLE-WEAK")

        else:
            reasons.append("CANDLE-LARGE")

        # =========================================================
        # PENALTIES
        # =========================================================

        if r > 68:
            score -= 10
            reasons.append("RSI-HIGH")

        if candle_body > MAX_GREEN_CANDLE:
            score -= 10
            reasons.append("CANDLE-LARGE")

        if hist_now < 0:
            score -= 7

        if mom < MIN_MOMENTUM * 0.70:
            score -= 7

        score = max(
            0,
            min(
                100,
                int(round(score))
            )
        )

        # =========================================================
        # CONFIRMATIONS
        # =========================================================

        confirmation = 0

        if htf_bull:
            confirmation += 1

        if ltf_bull:
            confirmation += 1

        if 50 <= r <= 67:
            confirmation += 1

        if mom >= 0.0025:
            confirmation += 1

        if adx_now >= 18:
            confirmation += 1

        if hist_now > 0:
            confirmation += 1

        if vol_ratio >= 0.95:
            confirmation += 1

        # =========================================================
        # CONFIDENCE
        # =========================================================

        confidence = round(
            (confirmation / 7) * 100
        )

        # =========================================================
        # QUALITY
        # =========================================================

        if score >= 92 and confidence >= 85:
            quality = "A+"

        elif score >= 86 and confidence >= 71:
            quality = "A"

        elif score >= 78:
            quality = "B"

        elif score >= 70:
            quality = "C"

        else:
            quality = "D"

        # =========================================================
        # BUY
        #
        # Strict enough to protect against weak trades,
        # but not requiring every indicator to be perfect.
        # =========================================================

        buy_score = max(
            70,
            int(BUY_SCORE)
        )

        strong_buy = (
            score >= buy_score
            and confidence >= 71
            and htf_bull
            and ltf_bull
            and confirmation >= 5
            and mom >= 0.0025
            and r <= 68
            and candle_body <= MAX_GREEN_CANDLE
        )

        if strong_buy:
            signal_type = "BUY"

        # =========================================================
        # WATCH
        #
        # Keep weaker but potentially developing setups.
        # =========================================================

        elif (
            score >= 68
            and confidence >= 57
            and confirmation >= 4
        ):
            signal_type = "WATCH"

        else:
            return None

        # =========================================================
        # QUALITY FACTOR
        # =========================================================

        qfactor = {
            "A+": 1.00,
            "A": 0.90,
            "B": 0.70,
            "C": 0.40,
            "D": 0.20,
        }[quality]

        # =========================================================
        # RESULT
        # =========================================================

        return {
            "symbol": symbol,
            "signal": signal_type,

            "score": score,
            "confidence": confidence,
            "quality": quality,
            "quality_factor": qfactor,

            "confirmation": confirmation,

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
            f"[SCAN ERROR] {symbol}: {exc}"
        )
        return None


def scan_market():
    signals = []

    checked = 0
    buy_count = 0
    watch_count = 0

    for symbol in SYMBOLS:
        checked += 1

        result = analyze_symbol(symbol)

        if result is None:
            continue

        signals.append(result)

        if result["signal"] == "BUY":
            buy_count += 1

        elif result["signal"] == "WATCH":
            watch_count += 1

    # =========================================================
    # SORT
    # =========================================================

    signals.sort(
        key=lambda x: (
            x.get("signal") == "BUY",
            x.get("score", 0),
            x.get("confidence", 0),
            x.get("confirmation", 0),
            x.get("adx", 0),
            x.get("momentum", 0),
            x.get("volume_ratio", 0),
        ),
        reverse=True,
    )

    print(
        f"[SCAN] Checked={checked} "
        f"Candidates={len(signals)} "
        f"BUY={buy_count} "
        f"WATCH={watch_count}"
    )

    # =========================================================
    # TOP SIGNAL
    # =========================================================

    if signals:
        top = signals[0]

        print(
            f"[TOP] {top['symbol']} "
            f"{top['signal']} "
            f"Score={top['score']} "
            f"RSI={top['rsi']:.1f} "
            f"ADX={top['adx']:.1f} "
            f"MOM={top['momentum']:.4f} "
            f"VOL={top['volume_ratio']:.2f} "
            f"HTF={top['htf_bull']} "
            f"LTF={top['ltf_bull']} "
            f"CONF={top['confidence']} "
            f"Q={top['quality']} "
            f"CONFIRM={top['confirmation']}/7"
        )

        if top.get("reasons"):
            print(
                "[REASONS] "
                + ", ".join(top["reasons"])
            )

    else:
        print(
            "[TOP] No qualifying signals"
        )

    return signals
