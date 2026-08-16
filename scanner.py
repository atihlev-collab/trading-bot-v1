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
# HELPERS
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

        macd_line, macd_signal, macd_hist = macd(lc)

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
        # BASIC VALIDATION
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
        #
        # We want real participation.
        # ==================================

        vol_ratio = (
            volume_now
            / volume_average
        )

        if vol_ratio < max(
            VOLUME_MULTIPLIER,
            1.10,
        ):
            return None

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

        if not htf_bull:
            return None

        if not ltf_bull:
            return None

        # ==================================
        # RSI
        #
        # Avoid buying an already exhausted
        # move.
        # ==================================

        rsi_min = max(
            RSI_MIN,
            52,
        )

        rsi_max = min(
            RSI_MAX,
            65,
        )

        if not (
            rsi_min
            <= r
            <= rsi_max
        ):
            return None

        # ==================================
        # MOMENTUM
        # ==================================

        momentum_min = max(
            MIN_MOMENTUM,
            0.003,
        )

        if mom < momentum_min:
            return None

        # ==================================
        # TREND STRENGTH
        # ==================================

        if ts < MIN_TREND_STRENGTH:
            return None

        # ==================================
        # MACD
        # ==================================

        if hist_now <= 0:
            return None

        # ==================================
        # ADX
        # ==================================

        if adx_now < 22:
            return None

        # ==================================
        # CURRENT CANDLE
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

        # Don't buy a huge green candle.
        if candle_body > MAX_GREEN_CANDLE:
            return None

        # ==================================
        # SCORE
        # ==================================

        score = 0

        # HTF trend
        score += 25

        # LTF trend
        score += 20

        # RSI quality
        if 55 <= r <= 62:
            score += 15
        else:
            score += 10

        # Volume
        if vol_ratio >= 1.50:
            score += 15

        elif vol_ratio >= 1.25:
            score += 12

        else:
            score += 8

        # Momentum
        if mom >= 0.005:
            score += 15

        elif mom >= 0.004:
            score += 12

        else:
            score += 8

        # ADX
        if adx_now >= 30:
            score += 10

        elif adx_now >= 25:
            score += 8

        else:
            score += 5

        # MACD
        if hist_now > 0:
            score += 5

        score = min(
            score,
            100,
        )

        # ==================================
        # QUALITY
        # ==================================

        if score >= 92:
            quality = "A+"

        elif score >= 88:
            quality = "A"

        elif score >= 85:
            quality = "B+"

        else:
            quality = "B"

        # ==================================
        # FINAL BUY FILTER
        #
        # Only high-quality signals.
        # ==================================

        minimum_buy_score = max(
            BUY_SCORE,
            88,
        )

        if score < minimum_buy_score:
            signal_type = "WATCH"

        else:
            signal_type = "BUY"

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
        }

        # ==================================
        # DEBUG CANDIDATE
        # ==================================

        if signal_type == "BUY":

            print(
                f"[CANDIDATE] "
                f"{symbol} "
                f"BUY "
                f"Score={score} "
                f"RSI={r:.1f} "
                f"ADX={adx_now:.1f} "
                f"MOM={mom:.4f} "
                f"VOL={vol_ratio:.2f} "
                f"HTF=True "
                f"LTF=True"
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
            x["momentum"],
            x["volume"],
        ),
        reverse=True,
    )

    # ======================================
    # ONLY BUY SIGNALS GO TO TRADER
    #
    # WATCH remains available for debugging,
    # but will not open a position.
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

    return buy_signals
