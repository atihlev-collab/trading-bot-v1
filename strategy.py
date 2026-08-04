from indicators import (
    ema,
    rsi,
    atr,
    momentum,
    volume_ma,
    atr_percent,
    trend_strength,
    macd,
    bollinger,
    vwap,
)

from config import *


class StrategyEngine:

    def __init__(self):
        pass

    def analyze(
        self,
        symbol,
        df15,
        df1h,
        df4h,
    ):

        m15 = df15.copy()
        h1 = df1h.copy()
        h4 = df4h.copy()

        # ==========================
        # Indicators
        # ==========================

        for df in (m15, h1, h4):

            df["ema20"] = ema(df["close"], EMA_FAST)
            df["ema50"] = ema(df["close"], EMA_SLOW)
            df["ema200"] = ema(df["close"], EMA_TREND)

            df["rsi"] = rsi(df["close"], RSI_PERIOD)

            df["atr"] = atr(df, ATR_PERIOD)

            df["atr_pct"] = atr_percent(
                df["close"],
                df["atr"],
            )

            df["momentum"] = momentum(
                df["close"],
            )

            df["volume_ma"] = volume_ma(
                df["volume"],
            )

            df["trend_strength"] = trend_strength(
                df["ema20"],
                df["ema50"],
            )

            (
                df["macd"],
                df["macd_signal"],
                df["macd_hist"],
            ) = macd(df["close"])

            (
                df["bb_upper"],
                df["bb_mid"],
                df["bb_lower"],
            ) = bollinger(df["close"])

            df["vwap"] = vwap(df)

        row15 = m15.iloc[-2]
        row1h = h1.iloc[-2]
        row4h = h4.iloc[-2]

        score = 0
        reasons = []

        # ==========================================
        # TREND FILTERS
        # ==========================================

        trend15 = (
            row15["ema20"] >
            row15["ema50"] >
            row15["ema200"]
        )

        trend1h = (
            row1h["ema20"] >
            row1h["ema50"] >
            row1h["ema200"]
        )

        trend4h = (
            row4h["ema20"] >
            row4h["ema50"] >
            row4h["ema200"]
        )

        if trend15:
            score += 12
        else:
            reasons.append("15M_TREND")

        if trend1h:
            score += 16
        else:
            reasons.append("1H_TREND")

        if trend4h:
            score += 20
        else:
            reasons.append("4H_TREND")

        if trend15 and trend1h:
            score += 5

        if trend15 and trend1h and trend4h:
            score += 8

        # ==========================================
        # RSI
        # ==========================================

        if RSI_MIN <= row15["rsi"] <= RSI_MAX:
            score += 8
        else:
            reasons.append("RSI")

        # ==========================================
        # MOMENTUM
        # ==========================================

        if row15["momentum"] > MIN_MOMENTUM:
            score += 8
        else:
            reasons.append("MOMENTUM")

        # ==========================================
        # VOLUME
        # ==========================================

        if (
            row15["volume"] >
            row15["volume_ma"] * VOLUME_MULTIPLIER
        ):
            score += 10
        else:
            reasons.append("LOW_VOLUME")

        # ==========================================
        # ATR
        # ==========================================

        if (
            MIN_ATR_PERCENT <=
            row15["atr_pct"] <=
            MAX_ATR_PERCENT
        ):
            score += 6
        else:
            reasons.append("ATR")

        # ==========================================
        # TREND STRENGTH
        # ==========================================

        if (
            row15["trend_strength"] >
            MIN_TREND_STRENGTH
        ):
            score += 8
        else:
            reasons.append("WEAK_TREND")

        # ==========================================
        # MACD
        # ==========================================

        if (
            row15["macd"] >
            row15["macd_signal"]
        ):
            score += 8
        else:
            reasons.append("MACD")

        if (
            row15["macd"] >
            row15["macd_signal"]
            and
            row15["momentum"] > MIN_MOMENTUM
        ):
            score += 4

        # ==========================================
        # VWAP
        # ==========================================

        if (
            row15["close"] >
            row15["vwap"]
        ):
            score += 6
        else:
            reasons.append("VWAP")

        # ==========================================
        # BOLLINGER
        # ==========================================

        if (
            row15["close"] <
            row15["bb_upper"]
        ):
            score += 4
        else:
            reasons.append("BB_UPPER")

        # ==========================================
        # PRICE ABOVE EMA20
        # ==========================================

        if row15["close"] > row15["ema20"]:
            score += 5
        else:
            reasons.append("EMA20")

        # ==========================================
        # CANDLE FILTER
        # ==========================================

        candle_gain = (
            row15["close"] - row15["open"]
        ) / row15["open"]

        if candle_gain <= MAX_GREEN_CANDLE:
            score += 5
        else:
            reasons.append("BIG_GREEN")

        # ==========================================
        # EXTRA BONUS
        # ==========================================

        if (
            trend15
            and trend1h
            and row15["macd"] > row15["macd_signal"]
            and row15["close"] > row15["vwap"]
        ):
            score += 5

        confidence = round(score, 1)

        # ==========================================
        # QUALITY
        # ==========================================

        if confidence >= BUY_SCORE:
            quality = "A+"
            signal = "BUY"

        elif confidence >= WATCH_SCORE:
            quality = "A"
            signal = "WATCH"

        elif confidence >= IGNORE_SCORE:
            quality = "B"
            signal = "WATCH"

        else:
            quality = "C"
            signal = "WAIT"

        print(
            f"[RESULT] {symbol} "
            f"score={score} "
            f"signal={signal} "
            f"reasons={reasons}"
        )
        
        return {

            "symbol": symbol,

            "signal": signal,

            "quality": quality,

            "score": int(score),

            "confidence": float(confidence),

            "rank": 0,

            "trend_strength": float(
                row15["trend_strength"]
            ),

            "momentum": float(
                row15["momentum"]
            ),

            "volume": float(
                row15["volume"]
            ),

            "volume_ma": float(
                row15["volume_ma"]
            ),

            "rsi": float(
                row15["rsi"]
            ),

            "atr": float(
                row15["atr"]
            ),

            "atr_pct": float(
                row15["atr_pct"]
            ),

            "close": float(
                row15["close"]
            ),

            "reasons": reasons,

            "candle_time": row15[
                "open_time"
            ].isoformat(),

        }
