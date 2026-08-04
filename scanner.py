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

from logger import info

def scan_symbol(symbol):

    try:

        info(f"{symbol} -> 15m")
        df15 = get_candles(symbol, LOWER_TIMEFRAME)

        info(f"{symbol} -> 1h")
        df1h = get_candles(symbol, HIGHER_TIMEFRAME)

        info(f"{symbol} -> 4h")
        df4h = get_candles(symbol, "4h")

        info(f"{symbol} -> analyze")
        signal = engine.analyze(
            symbol,
            df15,
            df1h,
            df4h,
        )

        info(f"{symbol} -> analyzed")

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

    signals = rank_signals(signals)

    print("=" * 60)
    print(f"TOTAL SIGNALS: {len(signals)}")
    
    for s in signals:
        print(
            s["symbol"],
            s["signal"],
            s["score"],
            s["confidence"]
        )
    
    print("=" * 60)
    
    return signals


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
