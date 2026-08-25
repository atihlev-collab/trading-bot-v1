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
        if b is not None and float(b) > 0:
            return float(a) / float(b)
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

        # =========================
        # INDICATORS
        # =========================

        low_fast = ema(lc, EMA_FAST)
        low_slow = ema(lc, EMA_SLOW)
        low_trend = ema(lc, EMA_TREND)

        high_fast = ema(hc, EMA_FAST)
        high_slow = ema(hc, EMA_SLOW)
        high_trend = ema(hc, EMA_TREND)

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
        atr_now = _num(low_atr.iloc[i])
        rsi_now = _num(low_rsi.iloc[i])
        mom_now = _num(low_mom.iloc[i])

        trend_now = _num(
            trend_strength(
                low_fast,
                low_slow
            ).iloc[i]
        )

        adx_now = _num(adx_v.iloc[i]) or 0.0
        macd_now = _num(macd_hist.iloc[i]) or 0.0

        volume_now = (
            _num(low["volume"].iloc[i])
            or 0.0
        )

        volume_average = (
            _num(vol_ma.iloc[i])
            or 0.0
        )

        if (
            price is None
            or price <= 0
            or atr_now is None
            or atr_now <= 0
            or rsi_now is None
            or mom_now is None
            or trend_now is None
        ):
            return None

        # =========================
        # ATR FILTER
        # =========================

        atr_pct = atr_now / price

        if not (
            MIN_ATR_PERCENT
            <= atr_pct
            <= MAX_ATR_PERCENT
        ):
            return None

        # =========================
        # HTF / LTF TREND
        # =========================

        high_close = _num(hc.iloc[i])
        high_trend_now = _num(high_trend.iloc[i])
        high_fast_now = _num(high_fast.iloc[i])
        high_slow_now = _num(high_slow.iloc[i])

        low_trend_now = _num(low_trend.iloc[i])
        low_fast_now = _num(low_fast.iloc[i])
        low_slow_now = _num(low_slow.iloc[i])

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

        htf_bull = (
            high_close > high_trend_now
            and high_fast_now > high_slow_now
        )

        ltf_bull = (
            price > low_trend_now
            and low_fast_now > low_slow_now
        )

        # =========================
        # CANDLE / VOLUME
        # =========================

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

        # =========================
        # SCORE
        # =========================

        score = 0
        reasons = []

        # HTF
        if htf_bull:
            score += 20
            reasons.append("HTF")

        # LTF
        if ltf_bull:
            score += 20
            reasons.append("LTF")

        # RSI
        if 55 <= rsi_now <= 65:
            score += 15
            reasons.append("RSI+")

        elif RSI_MIN <= rsi_now <= RSI_MAX:
            score += 10
            reasons.append("RSI")

        elif 45 <= rsi_now < RSI_MIN:
            score += 5
            reasons.append("RSI-WEAK")

        # Momentum
        if mom_now >= 0.006:
            score += 15
            reasons.append("MOM+")

        elif mom_now >= max(
            0.003,
            MIN_MOMENTUM
        ):
            score += 10
            reasons.append("MOM")

        elif mom_now >= MIN_MOMENTUM * 0.75:
            score += 5
            reasons.append("MOM-WEAK")

        # ADX
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
            reasons.append("ADX-LOW")

        # MACD
        if macd_now > 0:
            score += 10
            reasons.append("MACD")

        elif macd_now >= 0:
            score += 5
            reasons.append("MACD-FLAT")

        # Volume
        if vol_ratio >= 1.50:
            score += 10
            reasons.append("VOL+")

        elif vol_ratio >= 1.20:
            score += 7
            reasons.append("VOL")

        elif vol_ratio >= 1.00:
            score += 4
            reasons.append("VOL-NORMAL")

        # Candle
        if candle_body <= MAX_GREEN_CANDLE * 0.70:
            score += 5
            reasons.append("CANDLE")

        elif candle_body <= MAX_GREEN_CANDLE:
            score += 3
            reasons.append("CANDLE-WEAK")

        # =========================
        # PENALTIES
        # =========================

        if rsi_now > 68:
            score -= 8
            reasons.append("RSI-HIGH")

        if candle_body > MAX_GREEN_CANDLE:
            score -= 8
            reasons.append("CANDLE-LARGE")

        if macd_now < 0:
            score -= 6

        if mom_now < MIN_MOMENTUM * 0.75:
            score -= 6

        score = max(
            0,
            min(100, int(round(score)))
        )

        # =========================
        # QUALITY
        # =========================

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

        # =========================
        # CONFIRMATIONS
        # =========================

        confirmations = 0

        if htf_bull:
            confirmations += 1

        if ltf_bull:
            confirmations += 1

        if 52 <= rsi_now <= 68:
            confirmations += 1

        if mom_now >= 0.003:
            confirmations += 1

        if adx_now >= 20:
            confirmations += 1

        if macd_now > 0:
            confirmations += 1

        if vol_ratio >= 1.20:
            confirmations += 1

        confidence = round(
            (confirmations / 7) * 100
        )

        # =========================
        # QUALITY FACTOR
        # =========================

        quality_factor = (
            confidence / 100.0
        )

        if quality == "A+":
            quality_factor += 0.15

        elif quality == "A":
            quality_factor += 0.10

        elif quality == "B":
            quality_factor += 0.05

        quality_factor = max(
            0.35,
            min(1.0, quality_factor)
        )

        # =========================
        # BUY CONDITIONS
        # =========================

        buy_score = max(
            70,
            int(BUY_SCORE)
        )

        buy_ok = (
            score >= buy_score
            and confidence >= 85
            and htf_bull
            and ltf_bull
            and adx_now >= 20
            and macd_now > 0
            and vol_ratio >= 1.15
            and mom_now >= 0.003
            and rsi_now <= 68
            and candle_body <= MAX_GREEN_CANDLE
        )

        if buy_ok:
            signal_type = "BUY"

        elif score >= 75:
            signal_type = "WATCH"

        else:
            return None

        # =========================
        # RESULT
        # =========================

        return {
            "symbol": symbol,
            "signal": signal_type,

            "score": score,
            "confidence": confidence,
            "quality": quality,

            "confirmations": confirmations,
            "quality_factor": quality_factor,

            "close": price,
            "atr": atr_now,
            "atr_pct": atr_pct,

            "trend_strength": trend_now,
            "momentum": mom_now,

            "volume": volume_now,
            "volume_ma": volume_average,
            "volume_ratio": vol_ratio,

            "rsi": rsi_now,
            "adx": adx_now,
            "macd_hist": macd_now,

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

    # =========================
    # SORT
    # =========================

    signals.sort(
        key=lambda x: (
            x.get("quality_factor", 0),
            x.get("score", 0),
            x.get("confidence", 0),
            x.get("confirmations", 0),
            x.get("adx", 0),
            x.get("momentum", 0),
            x.get("volume_ratio", 0),
        ),
        reverse=True,
    )

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
            f"Q={top['quality']} "
            f"CONFIRM={top['confirmations']}/7"
        )

        if top.get("reasons"):
            print(
                "[REASONS] "
                + ", ".join(top["reasons"])
            )

    return signals
