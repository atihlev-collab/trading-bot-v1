#===========================================
# Trading Bot V5 - SCANNER
# ==========================================

import numpy as np

from config import (
    SYMBOLS,
    LOWER_TIMEFRAME,
    HIGHER_TIMEFRAME,
    RSI_MIN,
    RSI_MAX,
    RSI_HARD_MAX,
    MIN_ATR_PERCENT,
    MAX_ATR_PERCENT,
    VOLUME_MULTIPLIER,
    STRONG_VOLUME_RATIO,
    MIN_MOMENTUM,
    STRONG_MOMENTUM,
    MIN_TREND_STRENGTH,
    STRONG_TREND_STRENGTH,
    MAX_GREEN_CANDLE,
    MAX_ENTRY_CANDLE,
    BUY_SCORE,
    WATCH_SCORE,
    IGNORE_SCORE,
    MIN_BUY_CONFIRMATIONS,
)

from market_data import get_multi_tf
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


# ==========================================
# HELPERS
# ==========================================

def _safe_float(value, default=0.0):
    try:
        value = float(value)
        if np.isfinite(value):
            return value
    except Exception:
        pass

    return default


def _quality(score):
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 82:
        return "B"
    if score >= 72:
        return "C"
    return "D"


# ==========================================
# PREPARE DATA
# ==========================================

def _prepare(df):
    df = df.copy()

    if len(df) < 220:
        return None

    df["ema20"] = ema(df["close"], 20)
    df["ema50"] = ema(df["close"], 50)
    df["ema200"] = ema(df["close"], 200)

    df["rsi"] = rsi(df["close"], 14)

    df["atr"] = atr(df, 14)

    df["momentum"] = momentum(df["close"], 5)

    df["volume_ma"] = volume_ma(df["volume"], 20)

    df["volume_ratio"] = (
        df["volume"]
        / df["volume_ma"].replace(0, np.nan)
    )

    df["trend_strength"] = trend_strength(
        df["ema20"],
        df["ema50"],
    )

    _, _, df["macd_hist"] = macd(df["close"])

    df["adx"] = adx(df, 14)

    df["atr_pct"] = (
        df["atr"]
        / df["close"].replace(0, np.nan)
    )

    df["candle_body"] = (
        (df["close"] - df["open"])
        / df["open"].replace(0, np.nan)
    )

    return df


# ==========================================
# ANALYZE SYMBOL
# ==========================================

def analyze_symbol(symbol):
    try:
        data = get_multi_tf(symbol)

        low = _prepare(data[LOWER_TIMEFRAME])
        high = _prepare(data[HIGHER_TIMEFRAME])

        if low is None or high is None:
            return None

        if len(low) < 220 or len(high) < 220:
            return None

        # get_candles() already removes the still-forming candle;
        # the final row is therefore the latest fully closed candle.
        l = low.iloc[-1]
        h = high.iloc[-1]

        price = _safe_float(l["close"])

        if price <= 0:
            return None

        atr_now = _safe_float(l["atr"])
        atr_pct = _safe_float(l["atr_pct"])

        r = _safe_float(l["rsi"])
        mom = _safe_float(l["momentum"])
        vol_ratio = _safe_float(l["volume_ratio"])

        ts = _safe_float(l["trend_strength"])
        adx_now = _safe_float(l["adx"])
        hist_now = _safe_float(l["macd_hist"])

        candle_body = _safe_float(l["candle_body"])

        # ======================================
        # FILTER STATUS
        # ======================================
        # Keep these as entry-quality checks instead of rejecting a symbol
        # before it can be scored. This lets the scanner report WATCH setups
        # and, when there are no candidates, show why each symbol was ignored.
        atr_valid = (
            MIN_ATR_PERCENT
            <= atr_pct
            <= MAX_ATR_PERCENT
        )

        # ======================================
        # TREND
        # ======================================

        htf_bull = (
            h["close"] > h["ema200"]
            and h["ema20"] > h["ema50"]
        )

        ltf_bull = (
            price > l["ema200"]
            and l["ema20"] > l["ema50"]
        )

        # Trend misalignment is a BUY blocker, not a reason to skip scoring.
        # Some symbols can still be useful WATCH candidates.

        # ======================================
        # CONDITIONS
        # ======================================

        conditions = {
            "HTF": htf_bull,
            "LTF": ltf_bull,
            "RSI": RSI_MIN <= r <= RSI_MAX,
            "MOM": mom >= MIN_MOMENTUM,
            "TREND": ts >= MIN_TREND_STRENGTH,
            "VOLUME": vol_ratio >= VOLUME_MULTIPLIER,
            "MACD": hist_now > 0,
            "ADX": adx_now >= 20,
            "CANDLE": (
                0 < candle_body <= MAX_GREEN_CANDLE
            ),
        }

        confirmations = sum(
            1 for value in conditions.values()
            if value
        )

        # ======================================
        # SCORE
        # ======================================

        score = 0
        reasons = []

        # Trend = strongest component.
        if htf_bull:
            score += 18
            reasons.append("HTF")

        if ltf_bull:
            score += 18
            reasons.append("LTF")

        # RSI.
        if RSI_MIN <= r <= RSI_MAX:
            score += 10
            reasons.append("RSI")

            if 55 <= r <= 63:
                score += 3
                reasons.append("RSI+")

        elif r < RSI_MIN:
            score += 3
            reasons.append("RSI-LOW")

        # Momentum.
        if mom >= STRONG_MOMENTUM:
            score += 12
            reasons.append("MOM++")
        elif mom >= MIN_MOMENTUM:
            score += 8
            reasons.append("MOM+")

        # Trend strength.
        if ts >= STRONG_TREND_STRENGTH:
            score += 10
            reasons.append("TREND++")
        elif ts >= MIN_TREND_STRENGTH:
            score += 6
            reasons.append("TREND+")

        # ADX.
        if adx_now >= 25:
            score += 10
            reasons.append("ADX+")
        elif adx_now >= 20:
            score += 6
            reasons.append("ADX")

        # MACD.
        if hist_now > 0:
            score += 8
            reasons.append("MACD")

            if hist_now > abs(
                _safe_float(
                    low["macd_hist"].iloc[-2]
                )
            ):
                score += 2
                reasons.append("MACD+")

        # Volume.
        if vol_ratio >= STRONG_VOLUME_RATIO:
            score += 10
            reasons.append("VOL++")
        elif vol_ratio >= VOLUME_MULTIPLIER:
            score += 6
            reasons.append("VOL+")

        # Candle.
        if 0 < candle_body <= MAX_GREEN_CANDLE:
            score += 5
            reasons.append("CANDLE")

        # ======================================
        # SCORE CAP
        # ======================================

        score = min(score, 100)

        # ======================================
        # QUALITY
        # ======================================

        quality = _quality(score)

        # ======================================
        # CONFIDENCE
        # ======================================

        confidence = round(
            (
                confirmations
                / len(conditions)
            ) * 100
        )

        # ======================================
        # BUY FILTER
        # ======================================

        # The score and confirmation count are the flexible filters.
        # Keep trend direction, minimum momentum and a controlled green
        # entry candle as hard BUY requirements; RSI, volume, MACD, ADX
        # and trend strength otherwise contribute to score/confirmations.
        buy_checks = {
            "score": score >= int(BUY_SCORE),
            "confirmations": confirmations >= int(MIN_BUY_CONFIRMATIONS),
            "htf": htf_bull,
            "ltf": ltf_bull,
            "atr": atr_valid,
            "rsi": r <= RSI_HARD_MAX,
            "momentum": mom >= MIN_MOMENTUM,
            # A small red candle can be a controlled pullback, not an automatic
            # rejection. Reject only an oversized candle in either direction.
            "candle": abs(candle_body) <= min(MAX_GREEN_CANDLE, MAX_ENTRY_CANDLE),
        }

        buy = all(buy_checks.values())

        # Debug only near the BUY area, so the log remains useful.
        if score >= max(int(BUY_SCORE) - 5, 85) or confirmations >= 7:
            failed = [
                name for name, ok in buy_checks.items()
                if not ok
            ]
            print(
                f"[BUY DEBUG] {symbol} | "
                f"score={score}>={int(BUY_SCORE)} "
                f"confidence={confidence} "
                f"confirm={confirmations}>={int(MIN_BUY_CONFIRMATIONS)} "
                f"RSI={r:.1f} "
                f"VOL={vol_ratio:.2f}>={VOLUME_MULTIPLIER} "
                f"MOM={mom:.4f}>={MIN_MOMENTUM} "
                f"TREND={ts:.4f}>={MIN_TREND_STRENGTH} "
                f"ADX={adx_now:.1f} "
                f"CANDLE={candle_body:.4f} "
                f"FAILED={','.join(failed) or 'NONE'} "
                f"FINAL_BUY={buy}",
                flush=True,
            )

        # ======================================
        # WATCH
        # ======================================

        watch = (
            (score >= WATCH_SCORE and confirmations >= 5)
            or (
                score >= max(int(IGNORE_SCORE) - 5, 55)
                and confirmations >= 4
            )
        )

        if buy:
            signal_type = "BUY"

        elif watch:
            signal_type = "WATCH"

        else:
            # Return an explicit rejection reason for aggregate scan diagnostics.
            if not htf_bull and not ltf_bull:
                rejection_reason = "trend_both"
            elif not htf_bull:
                rejection_reason = "trend_htf"
            elif not ltf_bull:
                rejection_reason = "trend_ltf"
            elif not atr_valid:
                rejection_reason = "atr_out_of_range"
            elif r > RSI_HARD_MAX:
                rejection_reason = "rsi_overextended"
            elif mom < MIN_MOMENTUM:
                rejection_reason = "weak_momentum"
            elif abs(candle_body) > min(MAX_GREEN_CANDLE, MAX_ENTRY_CANDLE):
                rejection_reason = "oversized_candle"
            else:
                rejection_reason = "score_or_confirmations"

            return {
                "symbol": symbol,
                "signal": "IGNORE",
                "score": score,
                "confirmations": confirmations,
                "rejection_reason": rejection_reason,
            }

        # ======================================
        # RESULT
        # ======================================

        return {
            "symbol": symbol,
            "signal": signal_type,

            "score": score,
            "confidence": confidence,
            "quality": quality,

            "close": price,

            "atr": atr_now,
            "atr_pct": atr_pct,

            "trend_strength": ts,
            "momentum": mom,

            "volume": _safe_float(l["volume"]),
            "volume_ma": _safe_float(l["volume_ma"]),
            "volume_ratio": vol_ratio,

            "rsi": r,
            "adx": adx_now,
            "macd_hist": hist_now,

            "htf_bull": htf_bull,
            "ltf_bull": ltf_bull,

            "candle_body": candle_body,

            "confirmations": confirmations,
            "max_confirmations": len(conditions),

            "reasons": reasons,
        }

    except Exception as exc:
        print(
            f"[SCAN ERROR] "
            f"{symbol}: {exc}"
        )
        return None


# ==========================================
# MARKET SCANNER
# ==========================================

def scan_market():
    signals = []

    checked = 0
    buy_count = 0
    watch_count = 0
    invalid_data = 0
    rejections = {}

    for symbol in SYMBOLS:
        checked += 1

        result = analyze_symbol(symbol)

        if result is None:
            invalid_data += 1
            continue

        if result.get("signal") == "IGNORE":
            reason = result.get("rejection_reason", "unspecified")
            rejections[reason] = rejections.get(reason, 0) + 1
            continue

        signals.append(result)

        if result["signal"] == "BUY":
            buy_count += 1

        elif result["signal"] == "WATCH":
            watch_count += 1

    # ======================================
    # SORT
    # ======================================

    signals.sort(
        key=lambda x: (
            x.get("signal") == "BUY",
            x.get("score", 0),
            x.get("confidence", 0),
            x.get("adx", 0),
            x.get("momentum", 0),
            x.get("volume_ratio", 0),
        ),
        reverse=True,
    )

    # ======================================
    # LOG
    # ======================================

    scan_message = (
        f"[SCAN] "
        f"Checked={checked} "
        f"Candidates={len(signals)} "
        f"BUY={buy_count} "
        f"WATCH={watch_count}"
    )
    print(scan_message, flush=True)

    filter_parts = [f"{name}={count}" for name, count in sorted(rejections.items())]
    filter_message = (
        f"[SCAN FILTERS] InvalidData={invalid_data} "
        + (" ".join(filter_parts) if filter_parts else "Ignored=0")
    )
    print(filter_message, flush=True)

    import logging
    logging.getLogger("TradingBotV4").info(scan_message)
    logging.getLogger("TradingBotV4").info(filter_message)

    if signals:
        top = signals[0]

        top_message = (
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
            f"CONFIRM="
            f"{top['confirmations']}/"
            f"{top['max_confirmations']}"
        )
        print(top_message, flush=True)

        import logging
        logging.getLogger("TradingBotV4").info(top_message)

        print(
            "[REASONS] "
            + ", ".join(top["reasons"])
        )

    return signals
