import math

from config import (
    SYMBOLS,
    LOWER_TIMEFRAME,
    HIGHER_TIMEFRAME,
    EMA_FAST,
    EMA_SLOW,
    EMA_TREND,
    RSI_PERIOD,
    ATR_PERIOD,
    MIN_ATR_PERCENT,
    MAX_ATR_PERCENT,
    VOLUME_PERIOD,
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
# TRADING BOT V5 - QUALITY SCANNER
# Малко сигнали / висока конفلуенция
# =========================================================


MIN_BUY_SCORE = max(82, BUY_SCORE)

# Не позволяваме прекалено слаб ADX
MIN_ADX = 18

# Минимален резултат, за да се покаже WATCH
MIN_WATCH_SCORE = 68


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

        if b <= 0:
            return 0.0

        return a / b

    except Exception:
        return 0.0


# =========================================================
# ANALYZE SYMBOL
# =========================================================

def analyze_symbol(symbol):

    try:

        # -------------------------------------------------
        # DATA
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

        low_fast = ema(lc, EMA_FAST)
        low_slow = ema(lc, EMA_SLOW)
        low_trend = ema(lc, EMA_TREND)

        high_fast = ema(hc, EMA_FAST)
        high_slow = ema(hc, EMA_SLOW)
        high_trend = ema(hc, EMA_TREND)

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

        macd_line, macd_signal, macd_hist = macd(lc)

        adx_values = adx(
            low,
            14
        )

        low_ts = trend_strength(
            low_fast,
            low_slow
        )

        # -------------------------------------------------
        # CURRENT VALUES
        # -------------------------------------------------

        i = -1

        price = _num(lc.iloc[i])
        atr_now = _num(low_atr.iloc[i])
        rsi_now = _num(low_rsi.iloc[i])
        mom_now = _num(low_mom.iloc[i])
        ts_now = _num(low_ts.iloc[i])
        adx_now = _num(adx_values.iloc[i])
        hist_now = _num(macd_hist.iloc[i])

        volume_now = _num(
            low["volume"].iloc[i]
        )

        volume_average = _num(
            vol_ma.iloc[i]
        )

        if price is None or price <= 0:
            return None

        if atr_now is None:
            return None

        if rsi_now is None:
            return None

        if mom_now is None:
            return None

        if ts_now is None:
            return None

        if adx_now is None:
            adx_now = 0.0

        if hist_now is None:
            hist_now = 0.0

        if volume_now is None:
            volume_now = 0.0

        if volume_average is None:
            volume_average = 0.0

        # -------------------------------------------------
        # ATR
        # -------------------------------------------------

        atr_pct = atr_now / price

        if not (
            MIN_ATR_PERCENT
            <= atr_pct
            <= MAX_ATR_PERCENT
        ):
            return None

        # -------------------------------------------------
        # VOLUME
        # -------------------------------------------------

        volume_ratio = _safe_ratio(
            volume_now,
            volume_average
        )

        # -------------------------------------------------
        # TREND
        # -------------------------------------------------

        htf_bull = (
            float(hc.iloc[i])
            > float(high_trend.iloc[i])
            and
            float(high_fast.iloc[i])
            > float(high_slow.iloc[i])
        )

        ltf_bull = (
            price
            > float(low_trend.iloc[i])
            and
            float(low_fast.iloc[i])
            > float(low_slow.iloc[i])
        )

        # -------------------------------------------------
        # CANDLE
        # -------------------------------------------------

        candle_open = _num(
            low["open"].iloc[i]
        )

        candle_close = _num(
            low["close"].iloc[i]
        )

        candle_high = _num(
            low["high"].iloc[i]
        )

        candle_low = _num(
            low["low"].iloc[i]
        )

        if candle_open is None:
            candle_open = price

        if candle_close is None:
            candle_close = price

        if candle_high is None:
            candle_high = max(
                candle_open,
                candle_close
            )

        if candle_low is None:
            candle_low = min(
                candle_open,
                candle_close
            )

        candle_body = abs(
            candle_close - candle_open
        ) / candle_open

        candle_range = max(
            candle_high - candle_low,
            1e-12
        )

        body_ratio = (
            abs(candle_close - candle_open)
            / candle_range
        )

        green_candle = (
            candle_close > candle_open
        )

        # =================================================
        # QUALITY SCORE
        # =================================================

        score = 0
        reasons = []

        # -------------------------------------------------
        # 1. HIGHER TIMEFRAME TREND
        # -------------------------------------------------

        if htf_bull:

            score += 25
            reasons.append("HTF")

        # -------------------------------------------------
        # 2. LOWER TIMEFRAME TREND
        # -------------------------------------------------

        if ltf_bull:

            score += 20
            reasons.append("LTF")

        # -------------------------------------------------
        # 3. RSI
        # -------------------------------------------------

        # Sweet spot: bullish but not overbought
        if 52 <= rsi_now <= 68:

            score += 15
            reasons.append("RSI")

        elif 48 <= rsi_now < 52:

            score += 8

        elif 68 < rsi_now <= 72:

            score += 7

        # Above 72 gets no points,
        # but does NOT automatically kill the setup.

        # -------------------------------------------------
        # 4. MOMENTUM
        # -------------------------------------------------

        if mom_now >= 0.006:

            score += 12
            reasons.append("MOM")

        elif mom_now >= 0.003:

            score += 9
            reasons.append("MOM+")

        elif mom_now >= 0.001:

            score += 5

        # Negative momentum = 0

        # -------------------------------------------------
        # 5. ADX
        # -------------------------------------------------

        if adx_now >= 30:

            score += 15
            reasons.append("ADX")

        elif adx_now >= 25:

            score += 12
            reasons.append("ADX+")

        elif adx_now >= 20:

            score += 8

        elif adx_now >= MIN_ADX:

            score += 4

        # -------------------------------------------------
        # 6. MACD
        # -------------------------------------------------

        if hist_now > 0:

            score += 8
            reasons.append("MACD")

        # -------------------------------------------------
        # 7. VOLUME
        # -------------------------------------------------

        if volume_ratio >= 1.50:

            score += 10
            reasons.append("VOL")

        elif volume_ratio >= 1.20:

            score += 8
            reasons.append("VOL+")

        elif volume_ratio >= 1.00:

            score += 4

        # Low volume does not automatically reject.
        # It simply doesn't receive points.

        # -------------------------------------------------
        # 8. GREEN CANDLE / BODY
        # -------------------------------------------------

        if green_candle and body_ratio >= 0.50:

            score += 5
            reasons.append("CANDLE")

        elif green_candle:

            score += 2

        # -------------------------------------------------
        # MAX SCORE
        # -------------------------------------------------

        score = min(
            int(score),
            100
        )

        # =================================================
        # CONFIRMATION COUNT
        # =================================================

        confirmations = 0

        if htf_bull:
            confirmations += 1

        if ltf_bull:
            confirmations += 1

        if adx_now >= 25:
            confirmations += 1

        if hist_now > 0:
            confirmations += 1

        if volume_ratio >= 1.20:
            confirmations += 1

        if mom_now >= 0.003:
            confirmations += 1

        if 52 <= rsi_now <= 68:
            confirmations += 1

        # =================================================
        # QUALITY FILTERS
        # =================================================

        # Strong setups should have trend alignment.
        trend_alignment = (
            htf_bull and ltf_bull
        )

        # Alternative:
        # very strong LTF + momentum + ADX
        aggressive_alignment = (
            ltf_bull
            and mom_now >= 0.006
            and adx_now >= 25
            and hist_now > 0
        )

        valid_alignment = (
            trend_alignment
            or aggressive_alignment
        )

        # -------------------------------------------------
        # WATCH
        # -------------------------------------------------

        if (
            score >= MIN_WATCH_SCORE
            and valid_alignment
        ):

            signal = "WATCH"

        else:

            signal = None

        # -------------------------------------------------
        # BUY
        # -------------------------------------------------

        if (
            score >= MIN_BUY_SCORE
            and confirmations >= 5
            and valid_alignment
            and adx_now >= MIN_ADX
            and mom_now > 0
            and hist_now > 0
        ):

            signal = "BUY"

        # =================================================
        # QUALITY
        # =================================================

        if score >= 90:

            quality = "A+"

        elif score >= 85:

            quality = "A"

        elif score >= 78:

            quality = "B+"

        elif score >= 72:

            quality = "B"

        else:

            quality = "C"

        # =================================================
        # RESULT
        # =================================================

        if signal is None:
            return None

        return {
            "symbol": symbol,

            "signal": signal,

            "score": score,

            "confidence": score,

            "quality": quality,

            "close": price,

            "atr": atr_now,

            "atr_pct": atr_pct,

            "trend_strength": ts_now,

            "momentum": mom_now,

            "volume": volume_now,

            "volume_ma": volume_average,

            "volume_ratio": volume_ratio,

            "rsi": rsi_now,

            "adx": adx_now,

            "macd_hist": hist_now,

            "htf_bull": htf_bull,

            "ltf_bull": ltf_bull,

            "confirmations": confirmations,

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

    buys = 0

    watches = 0

    for symbol in SYMBOLS:

        checked += 1

        result = analyze_symbol(symbol)

        if result is None:
            continue

        signals.append(result)

        if result["signal"] == "BUY":

            buys += 1

        elif result["signal"] == "WATCH":

            watches += 1

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    signals.sort(
        key=lambda x: (
            x["signal"] == "BUY",
            x["score"],
            x["confirmations"],
            x["momentum"],
            x["volume_ratio"],
        ),
        reverse=True
    )

    # -----------------------------------------------------
    # LOG
    # -----------------------------------------------------

    print(
        f"[SCAN] Checked={checked} "
        f"Candidates={len(signals)} "
        f"BUY={buys} "
        f"WATCH={watches}"
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
            f"CONF={top['confirmations']}/7 "
            f"Q={top['quality']}"
        )

        if top.get("reasons"):

            print(
                "[REASONS] "
                + ", ".join(top["reasons"])
            )

    return signals
