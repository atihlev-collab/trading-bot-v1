# ==========================================
# Trading Bot V3
# Scanner
# ==========================================

from config import (
    SYMBOLS,
    LOWER_TIMEFRAME,
    HIGHER_TIMEFRAME,
)

from market_data import (
    get_candles,
)

from strategy import (
    StrategyEngine,
)

from ranking import (
    rank_signals,
)

engine = StrategyEngine()


# ==========================================
# Scan One Symbol
# ==========================================

def scan_symbol(symbol):

    try:

        df15 = get_candles(
            symbol,
            LOWER_TIMEFRAME,
        )

        df1h = get_candles(
            symbol,
            HIGHER_TIMEFRAME,
        )

        df4h = get_candles(
            symbol,
            "4h",
        )

        signal = engine.analyze(

            symbol,

            df15,

            df1h,

            df4h,

        )

        if signal["signal"] == "WAIT":
            return None

        return signal

    except Exception as e:

        print(f"[SCAN ERROR] {symbol}: {e}")

        return None


# ==========================================
# Scan Market
# ==========================================

def scan_market():

    signals = []

    for symbol in SYMBOLS:

        signal = scan_symbol(symbol)

        if signal:

            signals.append(signal)

    return rank_signals(signals)


# ==========================================
# Best Signal
# ==========================================

def best_signal():

    signals = scan_market()

    if not signals:

        return None

    return signals[0]


# ==========================================
# Top Signals
# ==========================================

def top_signals(limit=5):

    signals = scan_market()

    return signals[:limit]