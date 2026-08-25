import math

from config import (
    SYMBOLS, LOWER_TIMEFRAME, HIGHER_TIMEFRAME,
    EMA_FAST, EMA_SLOW, EMA_TREND,
    RSI_PERIOD, RSI_MIN, RSI_MAX,
    ATR_PERIOD, MIN_ATR_PERCENT, MAX_ATR_PERCENT,
    VOLUME_PERIOD, MIN_MOMENTUM, MAX_GREEN_CANDLE, BUY_SCORE,
)

from indicators import (
    ema, rsi, atr, momentum, volume_ma,
    trend_strength, macd, adx,
)

from market_data import get_candles


def num(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def ratio(a, b):
    a = num(a)
    b = num(b)

    if a is not None and b is not None and b > 0:
        return a / b

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

        _, _, macd_hist = macd(lc)
        adx_v = adx(low, 14)

        i = -1

        price = num(lc.iloc[i])
        atr_now = num(low_atr.iloc[i])
        rsi_now = num(low_rsi.iloc[i])
        mom_now = num(low_mom.iloc[i])
        adx_now = num(adx_v.iloc[i])
        macd_now = num(macd_hist.iloc[i])

        volume_now = num(low["volume"].iloc[i]) or 0.0
        volume_average = num(vol_ma.iloc[i]) or 0.0

        open_price = num(low["open"].iloc[i])

        high_close = num(hc.iloc[i])
        high_fast_now = num(high_fast.iloc[i])
        high_slow_now = num(high_slow.iloc[i])
        high_trend_now = num(high_trend.iloc[i])

        low_fast_now = num(low_fast.iloc[i])
        low_slow_now = num(low_slow.iloc[i])
        low_trend_now = num(low_trend.iloc[i])

        if any(
            x is None
            for x in [
                price,
                atr_now,
                rsi_now,
                mom_now,
                adx_now,
                macd_now,
                open_price,
                high_close,
                high_fast_now,
                high_slow_now,
                high_trend_now,
                low_fast_now,
                low_slow_now,
                low_trend_now,
            ]
        ):
            return None

        if price <= 0 or atr_now <= 0 or open_price <= 0:
            return None

        atr_pct = atr_now / price

        if not (MIN_ATR_PERCENT <= atr_pct <= MAX_ATR_PERCENT):
            return None

        htf_bull = (
            high_close > high_trend_now
            and high_fast_now > high_slow_now
        )

        ltf_bull = (
            price > low_trend_now
            and low_fast_now > low_slow_now
        )

        volume_ratio = ratio(volume_now, volume_average)
        candle_body = abs(price - open_price) / open_price

        score = 0
        reasons = []

        # ---------------------------------------------------------
        # HTF
        # ---------------------------------------------------------

        if htf_bull:
            score += 20
            reasons.append("HTF")
        elif high_close > high_trend_now:
            score += 8
            reasons.append("HTF-WEAK")

        # ---------------------------------------------------------
        # LTF
        # ---------------------------------------------------------

        if ltf_bull:
            score += 20
            reasons.append("LTF")
        elif price > low_trend_now:
            score += 8
            reasons.append("LTF-WEAK")

        # ---------------------------------------------------------
        # RSI
        # ---------------------------------------------------------

        if 52 <= rsi_now <= 64:
            score += 15
            reasons.append("RSI+")

        elif 48 <= rsi_now <= 68:
            score += 10
            reasons.append("RSI")

        elif 44 <= rsi_now < 48:
            score += 4
            reasons.append("RSI-WEAK")

        # ---------------------------------------------------------
        # MOMENTUM
        # ---------------------------------------------------------

        if mom_now >= 0.006:
            score += 15
            reasons.append("MOM+")

        elif mom_now >= max(0.003, MIN_MOMENTUM):
            score += 10
            reasons.append("MOM")

        elif mom_now >= MIN_MOMENTUM * 0.75:
            score += 4
            reasons.append("MOM-WEAK")

        # ---------------------------------------------------------
        # ADX
        # ---------------------------------------------------------

        if adx_now >= 30:
            score += 15
            reasons.append("ADX+")

        elif adx_now >= 25:
            score += 10
            reasons.append("ADX")

        elif adx_now >= 18:
            score += 5
            reasons.append("ADX-WEAK")

        # ---------------------------------------------------------
        # MACD
        # ---------------------------------------------------------

        if macd_now > 0:
            score += 10
            reasons.append("MACD")

        elif macd_now >= 0:
            score += 5
            reasons.append("MACD-FLAT")

        # ---------------------------------------------------------
        # VOLUME
        # ---------------------------------------------------------

        if volume_ratio >= 1.50:
            score += 10
            reasons.append("VOL+")

        elif volume_ratio >= 1.20:
            score += 7
            reasons.append("VOL")

        elif volume_ratio >= 0.95:
            score += 3
            reasons.append("VOL-NORMAL")

        # ---------------------------------------------------------
        # CANDLE
        # ---------------------------------------------------------

        if candle_body <= MAX_GREEN_CANDLE * 0.70:
            score += 5
            reasons.append("CANDLE")

        elif candle_body <= MAX_GREEN_CANDLE:
            score += 3
            reasons.append("CANDLE-WEAK")

        # ---------------------------------------------------------
        # PENALTIES
        # ---------------------------------------------------------

        if rsi_now > 68:
            score -= 10
            reasons.append("RSI-HIGH")

        if candle_body > MAX_GREEN_CANDLE:
            score -= 10
            reasons.append("CANDLE-LARGE")

        if macd_now < 0:
            score -= 7

        if mom_now < MIN_MOMENTUM * 0.75:
            score -= 7

        if adx_now < 15:
            score -= 5
            reasons.append("ADX-LOW")

        score = max(0, min(100, int(round(score))))

        # ---------------------------------------------------------
        # CONFIDENCE
        # ---------------------------------------------------------

        confidence_points = sum(
            [
                htf_bull,
                ltf_bull,
                50 <= rsi_now <= 66,
                mom_now >= 0.003,
                adx_now >= 20,
                macd_now > 0,
                volume_ratio >= 1.10,
            ]
        )

        confidence = round(
            (confidence_points / 7) * 100
        )

        # ---------------------------------------------------------
        # CONFIRMATIONS
        # ---------------------------------------------------------

        strong_trend = htf_bull and ltf_bull

        confirmations = sum(
            [
                strong_trend,
                mom_now >= max(0.0025, MIN_MOMENTUM * 0.90),
                adx_now >= 18,
                macd_now > 0,
                48 <= rsi_now <= 67,
                volume_ratio >= 0.95,
                candle_body <= MAX_GREEN_CANDLE,
            ]
        )

        min_buy = max(78, int(BUY_SCORE))

        # ---------------------------------------------------------
        # SIGNAL
        # ---------------------------------------------------------

        if (
            score >= min_buy
            and confidence >= 71
            and confirmations >= 6
            and strong_trend
            and macd_now > 0
            and 48 <= rsi_now <= 67
        ):
            signal = "BUY"

        elif (
            score >= 70
            and confidence >= 57
            and confirmations >= 4
        ):
            signal = "WATCH"

        else:
            return None

        # ---------------------------------------------------------
        # QUALITY
        # ---------------------------------------------------------

        if score >= 92 and confidence >= 85:
            quality = "A+"

        elif score >= 86 and confidence >= 71:
            quality = "A"

        elif score >= 78:
            quality = "B"

        else:
            quality = "C"

        quality_factor = {
            "A+": 1.0,
            "A": 0.90,
            "B": 0.70,
            "C": 0.40,
        }[quality]

        trend_value = trend_strength(
            low_fast,
            low_slow
        )

        trend_now = num(trend_value.iloc[i])

        if trend_now is None:
            trend_now = 0.0

        return {
            "symbol": symbol,
            "signal": signal,
            "score": score,
            "confidence": confidence,
            "quality": quality,
            "quality_factor": quality_factor,

            "close": price,

            "atr": atr_now,
            "atr_pct": atr_pct,

            "trend_strength": trend_now,

            "momentum": mom_now,

            "volume": volume_now,
            "volume_ma": volume_average,
            "volume_ratio": volume_ratio,

            "rsi": rsi_now,
            "adx": adx_now,
            "macd_hist": macd_now,

            "htf_bull": htf_bull,
            "ltf_bull": ltf_bull,

            "candle_body": candle_body,

            "confirmations": confirmations,

            "reasons": reasons,
        }

    except Exception as exc:
        print(f"[SCAN ERROR] {symbol}: {exc}")
        return None


def scan_market():
    signals = []
    buy_count = 0
    watch_count = 0

    for symbol in SYMBOLS:

        result = analyze_symbol(symbol)

        if result is None:
            continue

        signals.append(result)

        if result["signal"] == "BUY":
            buy_count += 1

        elif result["signal"] == "WATCH":
            watch_count += 1

    signals.sort(
        key=lambda x: (
            x.get("signal") == "BUY",
            x.get("score", 0),
            x.get("confidence", 0),
            x.get("confirmations", 0),
            x.get("adx", 0),
            x.get("momentum", 0),
        ),
        reverse=True,
    )

    print(
        f"[SCAN] "
        f"Checked={len(SYMBOLS)} "
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
