# ==========================================
# Trading Bot V4
# Scanner / Signal Engine
# ==========================================

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


def _safe_ratio(value, minimum):
    if minimum <= 0:
        return 0.0

    return value / minimum


# ==========================================
# ANALYZE SYMBOL
# ==========================================

def analyze_symbol(symbol):

    try:

        # ==================================
        # MARKET DATA
        # ==================================

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


        # ==================================
        # PRICE SERIES
        # ==================================

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


        # ==================================
        # CURRENT VALUES
        # ==================================

        i = -1

        price = _num(lc.iloc[i])

        atr_value = _num(
            low_atr.iloc[i]
        )

        rsi_now = _num(
            low_rsi.iloc[i]
        )

        momentum_now = _num(
            low_mom.iloc[i]
        )

        trend_now = _num(
            trend_strength(
                low_fast,
                low_slow,
            ).iloc[i]
        )

        adx_now = _num(
            adx_v.iloc[i]
        )

        macd_hist_now = _num(
            macd_hist.iloc[i]
        )


        if price is None or price <= 0:
            return None

        if atr_value is None or atr_value <= 0:
            return None

        if rsi_now is None:
            return None

        if momentum_now is None:
            return None

        if trend_now is None:
            return None

        if adx_now is None:
            adx_now = 0.0

        if macd_hist_now is None:
            macd_hist_now = 0.0


        # ==================================
        # ATR %
        # ==================================

        atr_pct = (
            atr_value /
            price
        )


        # ==================================
        # VOLUME
        # ==================================

        current_volume = _num(
            low["volume"].iloc[i]
        ) or 0.0

        volume_average = _num(
            vol_ma.iloc[i]
        ) or 0.0

        if volume_average > 0:

            volume_ratio = (
                current_volume /
                volume_average
            )

        else:

            volume_ratio = 0.0


        # ==================================
        # CANDLE
        # ==================================

        open_price = _num(
            low["open"].iloc[i]
        )

        close_price = _num(
            low["close"].iloc[i]
        )

        if (
            open_price is None
            or open_price <= 0
            or close_price is None
        ):
            return None

        candle_body = abs(
            close_price -
            open_price
        ) / open_price


        # ==================================
        # TREND CONDITIONS
        # ==================================

        high_price = _num(
            hc.iloc[i]
        )

        high_trend_value = _num(
            high_trend.iloc[i]
        )

        high_fast_value = _num(
            high_fast.iloc[i]
        )

        high_slow_value = _num(
            high_slow.iloc[i]
        )

        low_fast_value = _num(
            low_fast.iloc[i]
        )

        low_slow_value = _num(
            low_slow.iloc[i]
        )

        low_trend_value = _num(
            low_trend.iloc[i]
        )


        if (
            high_price is None
            or high_trend_value is None
            or high_fast_value is None
            or high_slow_value is None
            or low_fast_value is None
            or low_slow_value is None
            or low_trend_value is None
        ):
            return None


        # ==================================
        # HIGHER TIMEFRAME TREND
        # ==================================

        htf_bull = (
            high_price >
            high_trend_value
            and
            high_fast_value >
            high_slow_value
        )


        # ==================================
        # LOWER TIMEFRAME TREND
        # ==================================

        ltf_bull = (
            price >
            low_trend_value
            and
            low_fast_value >
            low_slow_value
        )


        # ==================================
        # IMPORTANT:
        # DO NOT TRADE AGAINST HTF TREND
        # ==================================

        if not htf_bull:

            return None


        # ==================================
        # SCORE
        # ==================================

        score = 0


        # ==================================
        # 1. HIGHER TIMEFRAME TREND
        # ==================================

        score += 25


        # ==================================
        # 2. LOWER TIMEFRAME TREND
        # ==================================

        if ltf_bull:

            score += 20

        else:

            # Do not immediately reject.
            # Give the market a chance to recover
            # if other factors are very strong.

            score += 5


        # ==================================
        # 3. RSI
        # ==================================

        if RSI_MIN <= rsi_now <= RSI_MAX:

            score += 15

        elif (
            rsi_now >= RSI_MIN - 5
            and
            rsi_now <= RSI_MAX + 5
        ):

            score += 8

        else:

            score += 0


        # ==================================
        # 4. VOLUME
        # ==================================

        if (
            volume_ratio >=
            VOLUME_MULTIPLIER
        ):

            score += 15

        elif volume_ratio >= 1.0:

            score += 9

        elif volume_ratio >= 0.75:

            score += 4


        # ==================================
        # 5. MOMENTUM
        # ==================================

        if momentum_now >= 0.004:

            score += 10

        elif momentum_now >= MIN_MOMENTUM:

            score += 7

        elif momentum_now > 0:

            score += 3


        # ==================================
        # 6. ADX
        # ==================================

        if adx_now >= 25:

            score += 10

        elif adx_now >= 20:

            score += 7

        elif adx_now >= 18:

            score += 4


        # ==================================
        # 7. MACD
        # ==================================

        if macd_hist_now > 0:

            score += 5


        # ==================================
        # ATR FILTER
        # ==================================
        #
        # ATR is important for position sizing.
        # We still reject extreme volatility.
        #

        if (
            atr_pct <
            MIN_ATR_PERCENT
        ):

            return None

        if (
            atr_pct >
            MAX_ATR_PERCENT
        ):

            return None


        # ==================================
        # CANDLE PROTECTION
        # ==================================
        #
        # Avoid buying after an extremely
        # extended candle.
        #

        if (
            candle_body >
            MAX_GREEN_CANDLE
        ):

            # Do not kill the signal completely.
            # Only penalize it.

            score -= 10


        # ==================================
        # ADD TREND QUALITY BONUS
        # ==================================

        if trend_now >= (
            MIN_TREND_STRENGTH * 1.5
        ):

            score += 5


        # ==================================
        # ADD STRONG MOMENTUM BONUS
        # ==================================

        if momentum_now >= 0.008:

            score += 5


        # ==================================
        # ADD STRONG VOLUME BONUS
        # ==================================

        if volume_ratio >= 1.50:

            score += 5


        # ==================================
        # LIMIT SCORE
        # ==================================

        score = max(
            0,
            min(
                int(round(score)),
                100,
            )
        )


        # ==================================
        # QUALITY
        # ==================================

        if score >= 90:

            quality = "A+"

        elif score >= 85:

            quality = "A"

        elif score >= 75:

            quality = "B"

        elif score >= 65:

            quality = "C"

        else:

            quality = "D"


        # ==================================
        # CONFIDENCE
        # ==================================

        confidence = score


        # ==================================
        # SIGNAL
        # ==================================

        if score >= BUY_SCORE:

            signal_type = "BUY"

        elif score >= max(
            BUY_SCORE - 10,
            60,
        ):

            signal_type = "WATCH"

        else:

            signal_type = "WATCH"


        # ==================================
        # FINAL QUALITY PROTECTION
        # ==================================

        # We don't want a BUY against the
        # lower timeframe trend unless the
        # rest of the setup is exceptionally
        # strong.

        if (
            signal_type == "BUY"
            and
            not ltf_bull
            and
            score < 90
        ):

            signal_type = "WATCH"


        # ==================================
        # RESULT
        # ==================================

        return {

            "symbol": symbol,

            "signal": signal_type,

            "score": score,

            "confidence": confidence,

            "quality": quality,

            "close": price,

            "atr": atr_value,

            "atr_percent": atr_pct,

            "trend_strength": trend_now,

            "momentum": momentum_now,

            "volume": current_volume,

            "volume_ma": volume_average,

            "volume_ratio": volume_ratio,

            "rsi": rsi_now,

            "adx": adx_now,

            "macd_hist": macd_hist_now,

            "htf_bull": htf_bull,

            "ltf_bull": ltf_bull,

            "candle_body": candle_body,

        }


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

    buy_count = 0

    watch_count = 0


    for symbol in SYMBOLS:

        checked += 1

        result = analyze_symbol(
            symbol
        )

        if not result:

            continue


        if result["signal"] == "BUY":

            buy_count += 1

        else:

            watch_count += 1


        signals.append(result)


    # ======================================
    # RANK
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
    # DEBUG
    # ======================================

    print(
        f"[SCAN] Checked={checked} "
        f"Candidates={len(signals)} "
        f"BUY={buy_count} "
        f"WATCH={watch_count}"
    )


    # ======================================
    # SHOW TOP CANDIDATES
    # ======================================

    for item in signals[:5]:

        print(

            f"[CANDIDATE] "
            f"{item['symbol']} "
            f"{item['signal']} "
            f"Score={item['score']} "
            f"RSI={item['rsi']:.1f} "
            f"ADX={item['adx']:.1f} "
            f"MOM={item['momentum']:.4f} "
            f"VOL={item['volume_ratio']:.2f} "
            f"HTF={item['htf_bull']} "
            f"LTF={item['ltf_bull']}"

        )


    return signals
