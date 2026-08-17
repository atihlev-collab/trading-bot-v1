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


# ==========================================================
# SAFE NUMBER
# ==========================================================

def _num(value):
    try:
        value = float(value)
        if math.isfinite(value):
            return value
        return None
    except Exception:
        return None


# ==========================================================
# ANALYZE SYMBOL
# ==========================================================

def analyze_symbol(symbol):

    try:

        low = get_candles(
            symbol,
            LOWER_TIMEFRAME
        )

        high = get_candles(
            symbol,
            HIGHER_TIMEFRAME
        )

        if len(low) < 220 or len(high) < 220:
            return None

        lc = low["close"]
        hc = high["close"]

        # ==================================================
        # EMAs
        # ==================================================

        low_fast = ema(lc, EMA_FAST)
        low_slow = ema(lc, EMA_SLOW)
        low_trend = ema(lc, EMA_TREND)

        high_fast = ema(hc, EMA_FAST)
        high_slow = ema(hc, EMA_SLOW)
        high_trend = ema(hc, EMA_TREND)

        # ==================================================
        # INDICATORS
        # ==================================================

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

        adx_v = adx(
            low,
            14
        )

        i = -1

        # ==================================================
        # PRICE / ATR
        # ==================================================

        price = _num(
            lc.iloc[i]
        )

        atr_value = _num(
            low_atr.iloc[i]
        )

        if price is None or price <= 0:
            return None

        if atr_value is None or atr_value <= 0:
            return None

        atr_pct = atr_value / price

        # ==================================================
        # VOLUME
        # ==================================================

        current_volume = _num(
            low["volume"].iloc[i]
        )

        volume_average = _num(
            vol_ma.iloc[i]
        )

        if current_volume is None:
            return None

        if volume_average is None or volume_average <= 0:
            return None

        volume_ratio = (
            current_volume /
            volume_average
        )

        # ==================================================
        # MOMENTUM
        # ==================================================

        momentum_now = _num(
            low_mom.iloc[i]
        )

        if momentum_now is None:
            return None

        # ==================================================
        # TREND STRENGTH
        # ==================================================

        trend_value = _num(
            trend_strength(
                low_fast,
                low_slow
            ).iloc[i]
        )

        if trend_value is None:
            return None

        # ==================================================
        # RSI
        # ==================================================

        rsi_now = _num(
            low_rsi.iloc[i]
        )

        if rsi_now is None:
            return None

        # ==================================================
        # ADX
        # ==================================================

        adx_now = _num(
            adx_v.iloc[i]
        )

        if adx_now is None:
            adx_now = 0.0

        # ==================================================
        # MACD
        # ==================================================

        hist_now = _num(
            macd_hist.iloc[i]
        )

        if hist_now is None:
            hist_now = 0.0

        # ==================================================
        # HIGHER TIMEFRAME TREND
        # ==================================================

        high_trend_value = _num(
            high_trend.iloc[i]
        )

        high_fast_value = _num(
            high_fast.iloc[i]
        )

        high_slow_value = _num(
            high_slow.iloc[i]
        )

        if (
            high_trend_value is None
            or high_fast_value is None
            or high_slow_value is None
        ):
            return None

        htf_bull = (
            float(hc.iloc[i]) > high_trend_value
            and high_fast_value > high_slow_value
        )

        # ==================================================
        # LOWER TIMEFRAME TREND
        # ==================================================

        low_trend_value = _num(
            low_trend.iloc[i]
        )

        low_fast_value = _num(
            low_fast.iloc[i]
        )

        low_slow_value = _num(
            low_slow.iloc[i]
        )

        if (
            low_trend_value is None
            or low_fast_value is None
            or low_slow_value is None
        ):
            return None

        ltf_bull = (
            price > low_trend_value
            and low_fast_value > low_slow_value
        )

        # ==================================================
        # CANDLE BODY
        # ==================================================

        open_price = _num(
            low["open"].iloc[i]
        )

        close_price = _num(
            low["close"].iloc[i]
        )

        if (
            open_price is None
            or close_price is None
            or open_price <= 0
        ):
            return None

        candle_body = (
            abs(close_price - open_price)
            / open_price
        )

        # ==================================================
        # HARD MARKET QUALITY FILTERS
        # ==================================================

        if not (
            MIN_ATR_PERCENT
            <= atr_pct
            <= MAX_ATR_PERCENT
        ):
            return None

        if not (
            RSI_MIN
            <= rsi_now
            <= RSI_MAX
        ):
            return None

        if momentum_now < MIN_MOMENTUM:
            return None

        if trend_value < MIN_TREND_STRENGTH:
            return None

        if candle_body > MAX_GREEN_CANDLE:
            return None

        # ==================================================
        # SCORE
        # ==================================================

        score = 0

        # HTF trend
        if htf_bull:
            score += 25

        # LTF trend
        if ltf_bull:
            score += 20

        # RSI
        if 55 <= rsi_now <= 65:
            score += 15
        elif 52 <= rsi_now <= 68:
            score += 10
        else:
            score += 5

        # Volume
        if volume_ratio >= 1.50:
            score += 15
        elif volume_ratio >= 1.10:
            score += 10
        else:
            score += 5

        # Momentum
        if momentum_now >= 0.006:
            score += 10
        elif momentum_now >= 0.003:
            score += 7
        else:
            score += 3

        # ADX
        if adx_now >= 30:
            score += 10
        elif adx_now >= 22:
            score += 7
        else:
            score += 3

        # MACD
        if hist_now > 0:
            score += 5

        score = min(
            int(score),
            100
        )

        # ==================================================
        # CONFIRMATION SYSTEM
        # ==================================================

        confirmations = 0

        if htf_bull:
            confirmations += 1

        if ltf_bull:
            confirmations += 1

        if adx_now >= 22:
            confirmations += 1

        if volume_ratio >= 1.10:
            confirmations += 1

        if hist_now > 0:
            confirmations += 1

        # ==================================================
        # BUY RULE
        #
        # QUALITY > QUANTITY
        # ==================================================

        buy_signal = (
            score >= max(
                BUY_SCORE,
                85
            )
            and htf_bull
            and ltf_bull
            and adx_now >= 22
            and volume_ratio >= 1.10
            and hist_now > 0
            and confirmations >= 4
        )

        # ==================================================
        # SIGNAL TYPE
        # ==================================================

        if buy_signal:

            signal_type = "BUY"

        elif score >= 70:

            signal_type = "WATCH"

        else:

            signal_type = "NONE"

        # ==================================================
        # QUALITY
        # ==================================================

        if score >= 90 and confirmations >= 5:
            quality = "A+"

        elif score >= 85 and confirmations >= 4:
            quality = "A"

        elif score >= 75:
            quality = "B"

        else:
            quality = "C"

        # ==================================================
        # RESULT
        # ==================================================

        return {
            "symbol": symbol,
            "signal": signal_type,

            "score": score,
            "confidence": score,
            "quality": quality,

            "confirmations": confirmations,

            "close": price,
            "atr": atr_value,

            "trend_strength": trend_value,
            "momentum": momentum_now,

            "volume": current_volume,
            "volume_ma": volume_average,
            "volume_ratio": volume_ratio,

            "rsi": rsi_now,
            "adx": adx_now,

            "macd_hist": hist_now,

            "htf_bull": htf_bull,
            "ltf_bull": ltf_bull,
        }

    except Exception as exc:

        print(
            f"[SCAN ERROR] {symbol}: {exc}"
        )

        return None


# ==========================================================
# SCAN MARKET
# ==========================================================

def scan_market():

    signals = []

    checked = 0
    candidates = 0
    buy_count = 0
    watch_count = 0

    for symbol in SYMBOLS:

        checked += 1

        result = analyze_symbol(
            symbol
        )

        if not result:
            continue

        if result["signal"] == "NONE":
            continue

        candidates += 1

        if result["signal"] == "BUY":

            buy_count += 1

            print(
                f"[CANDIDATE] "
                f"{symbol} BUY "
                f"Score={result['score']} "
                f"RSI={result['rsi']:.1f} "
                f"ADX={result['adx']:.1f} "
                f"MOM={result['momentum']:.4f} "
                f"VOL={result['volume_ratio']:.2f} "
                f"HTF={result['htf_bull']} "
                f"LTF={result['ltf_bull']} "
                f"CONF={result['confirmations']}/5"
            )

            signals.append(result)

        elif result["signal"] == "WATCH":

            watch_count += 1

            signals.append(result)

    # ======================================================
    # SORT
    # ======================================================

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

    # ======================================================
    # LOGGING
    # ======================================================

    print(
        f"[SCAN] "
        f"Checked={checked} "
        f"Candidates={candidates} "
        f"BUY={buy_count} "
        f"WATCH={watch_count}"
    )

    # ======================================================
    # TOP WATCH
    # ======================================================

    watch_only = [
        x for x in signals
        if x["signal"] == "WATCH"
    ]

    if watch_only and buy_count == 0:

        top = watch_only[0]

        print(
            f"[TOP WATCH] "
            f"{top['symbol']} "
            f"Score={top['score']} "
            f"RSI={top['rsi']:.1f} "
            f"ADX={top['adx']:.1f} "
            f"MOM={top['momentum']:.4f} "
            f"VOL={top['volume_ratio']:.2f} "
            f"HTF={top['htf_bull']} "
            f"LTF={top['ltf_bull']}"
        )

    # ======================================================
    # IMPORTANT:
    # RETURN ONLY BUY SIGNALS TO TRADING ENGINE
    # ======================================================

    buy_signals = [
        x for x in signals
        if x["signal"] == "BUY"
    ]

    return buy_signals
