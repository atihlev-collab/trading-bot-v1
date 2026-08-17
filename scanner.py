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


# ==========================================
# SAFE NUMBER
# ==========================================

def _num(value):
    try:
        value = float(value)

        if math.isfinite(value):
            return value

    except Exception:
        pass

    return None


# ==========================================
# ANALYZE SYMBOL
# ==========================================

def analyze_symbol(symbol):

    try:

        low = get_candles(
            symbol,
            LOWER_TIMEFRAME,
        )

        high = get_candles(
            symbol,
            HIGHER_TIMEFRAME,
        )

        if len(low) < 220 or len(high) < 220:
            return None

        lc = low["close"]
        hc = high["close"]

        # ==================================
        # EMA
        # ==================================

        low_fast = ema(
            lc,
            EMA_FAST,
        )

        low_slow = ema(
            lc,
            EMA_SLOW,
        )

        low_trend = ema(
            lc,
            EMA_TREND,
        )

        high_fast = ema(
            hc,
            EMA_FAST,
        )

        high_slow = ema(
            hc,
            EMA_SLOW,
        )

        high_trend = ema(
            hc,
            EMA_TREND,
        )

        # ==================================
        # INDICATORS
        # ==================================

        low_rsi = rsi(
            lc,
            RSI_PERIOD,
        )

        low_atr = atr(
            low,
            ATR_PERIOD,
        )

        low_mom = momentum(
            lc,
            5,
        )

        vol_ma = volume_ma(
            low["volume"],
            VOLUME_PERIOD,
        )

        macd_line, macd_signal, macd_hist = macd(
            lc
        )

        adx_v = adx(
            low,
            14,
        )

        i = -1

        # ==================================
        # CURRENT VALUES
        # ==================================

        price = float(
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
                low_slow,
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

        volume_now = float(
            low["volume"].iloc[i]
        )

        volume_average = float(
            vol_ma.iloc[i]
        )

        # ==================================
        # VALIDATION
        # ==================================

        if price <= 0:
            return None

        if a is None:
            return None

        if r is None:
            return None

        if mom is None:
            return None

        if ts is None:
            return None

        if volume_average <= 0:
            return None

        # ==================================
        # ATR
        # ==================================

        atr_pct = a / price

        if not (
            MIN_ATR_PERCENT
            <= atr_pct
            <= MAX_ATR_PERCENT
        ):
            return None

        # ==================================
        # VOLUME
        # ==================================

        vol_ratio = (
            volume_now
            /
            volume_average
        )

        # ==================================
        # TREND
        # ==================================

        htf_bull = (
            hc.iloc[i]
            > high_trend.iloc[i]
            and
            high_fast.iloc[i]
            > high_slow.iloc[i]
        )

        ltf_bull = (
            price
            > low_trend.iloc[i]
            and
            low_fast.iloc[i]
            > low_slow.iloc[i]
        )

        # ==================================
        # CANDLE
        # ==================================

        open_price = float(
            low["open"].iloc[i]
        )

        if open_price <= 0:
            return None

        candle_body = (
            abs(
                float(
                    low["close"].iloc[i]
                    -
                    low["open"].iloc[i]
                )
            )
            /
            open_price
        )

        # ==================================
        # SCORE ENGINE
        # ==================================

        score = 0

        reasons = []

        # ----------------------------------
        # HTF TREND
        # ----------------------------------

        if htf_bull:

            score += 25
            reasons.append("HTF")

        # ----------------------------------
        # LTF TREND
        # ----------------------------------

        if ltf_bull:

            score += 20
            reasons.append("LTF")

        # ----------------------------------
        # RSI
        # ----------------------------------

        if 52 <= r <= 65:

            score += 15
            reasons.append("RSI")

        elif (
            RSI_MIN
            <= r
            <= RSI_MAX
        ):

            score += 8

        # ----------------------------------
        # VOLUME
        # ----------------------------------

        if vol_ratio >= 1.50:

            score += 15
            reasons.append("VOL")

        elif vol_ratio >= 1.20:

            score += 11

        elif vol_ratio >= 1.00:

            score += 6

        # ----------------------------------
        # MOMENTUM
        # ----------------------------------

        if mom >= 0.005:

            score += 15
            reasons.append("MOM")

        elif mom >= 0.003:

            score += 11

        elif mom >= 0.0015:

            score += 6

        # ----------------------------------
        # ADX
        # ----------------------------------

        if adx_now >= 30:

            score += 10
            reasons.append("ADX")

        elif adx_now >= 25:

            score += 8

        elif adx_now >= 20:

            score += 5

        # ----------------------------------
        # MACD
        # ----------------------------------

        if hist_now > 0:

            score += 5
            reasons.append("MACD")

        # ==================================
        # CANDLE PENALTY
        # ==================================

        if candle_body > MAX_GREEN_CANDLE:

            score -= 15

        # ==================================
        # TREND STRENGTH
        # ==================================

        if ts >= MIN_TREND_STRENGTH:

            score += 5

        # ==================================
        # NORMALIZE
        # ==================================

        score = max(
            0,
            min(
                score,
                100,
            ),
        )

        # ==================================
        # QUALITY
        # ==================================

        if score >= 92:

            quality = "A+"

        elif score >= 88:

            quality = "A"

        elif score >= 82:

            quality = "B+"

        elif score >= 75:

            quality = "B"

        else:

            quality = "C"

        # ==================================
        # BUY FILTER
        #
        # Strong but not impossible.
        # ==================================

        minimum_buy_score = max(
            85,
            BUY_SCORE,
        )

        # Additional quality protection.
        #
        # We don't want a high score based
        # only on trend while momentum,
        # volume and ADX are weak.
        # ==================================

        quality_confirmations = 0

        if vol_ratio >= 1.10:
            quality_confirmations += 1

        if mom >= 0.0025:
            quality_confirmations += 1

        if adx_now >= 22:
            quality_confirmations += 1

        if hist_now > 0:
            quality_confirmations += 1

        if r <= 67:
            quality_confirmations += 1

        if (
            score >= minimum_buy_score
            and
            htf_bull
            and
            ltf_bull
            and
            quality_confirmations >= 4
        ):

            signal_type = "BUY"

        else:

            signal_type = "WATCH"

        # ==================================
        # RESULT
        # ==================================

        result = {

            "symbol": symbol,

            "signal": signal_type,

            "score": score,

            "confidence": score,

            "quality": quality,

            "close": price,

            "atr": a,

            "trend_strength": ts,

            "momentum": mom,

            "volume": volume_now,

            "volume_ma": volume_average,

            "rsi": r,

            "adx": adx_now,

            "volume_ratio": vol_ratio,

            "macd_hist": hist_now,

            "htf_bull": htf_bull,

            "ltf_bull": ltf_bull,

            "reasons": reasons,

        }

        # ==================================
        # LOG STRONG CANDIDATES
        # ==================================

        if score >= 75:

            print(
                f"[CANDIDATE] "
                f"{symbol} "
                f"{signal_type} "
                f"Score={score} "
                f"RSI={r:.1f} "
                f"ADX={adx_now:.1f} "
                f"MOM={mom:.4f} "
                f"VOL={vol_ratio:.2f} "
                f"HTF={htf_bull} "
                f"LTF={ltf_bull} "
                f"CONF={quality_confirmations}/5"
            )

        return result

    except Exception as exc:

        print(
            f"[SCAN ERROR] "
            f"{symbol}: {exc}"
        )

        return None


# ==========================================
# SCAN MARKET
# ==========================================

def scan_market():

    signals = []

    checked = 0

    candidates = 0

    buys = 0

    watches = 0

    for symbol in SYMBOLS:

        checked += 1

        result = analyze_symbol(
            symbol
        )

        if result is None:
            continue

        candidates += 1

        if result["signal"] == "BUY":

            buys += 1

        else:

            watches += 1

        signals.append(result)

    # ======================================
    # SORT
    # ======================================

    signals.sort(
        key=lambda x: (
            x["score"],
            x["confidence"],
            x["momentum"],
            x["volume_ratio"],
        ),
        reverse=True,
    )

    # ======================================
    # ONLY BUY GOES TO TRADER
    # ======================================

    buy_signals = [
        x
        for x in signals
        if x["signal"] == "BUY"
    ]

    print(
        f"[SCAN] "
        f"Checked={checked} "
        f"Candidates={candidates} "
        f"BUY={buys} "
        f"WATCH={watches}"
    )

    # ======================================
    # SHOW TOP WATCH
    #
    # Useful for tuning without opening
    # weak trades.
    # ======================================

    if not buy_signals and signals:

        top = signals[0]

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

    return buy_signals
