import time
import traceback
from datetime import datetime

from config import (
    SYMBOLS,
    SCAN_SECONDS,
    MAX_OPEN_POSITIONS,
)

from market_data import (
    get_candles,
    get_price,
)

from strategy import analyze

from paper_trader import (
    PaperTrader,
)

from report import (
    print_report,
)

from database import (
    init_db,
)


# ===========================================
# Initialize
# ===========================================

init_db()

trader = PaperTrader()

last_scan = {}

cooldown = {}
COOLDOWN_SECONDS = 7200   # 2 часа

print("=" * 60)
print("Trading Bot V2 - PAPER MODE")
from datetime import datetime, UTC
print("=" * 60)

def scan_symbol(symbol):

    df = get_candles(symbol)

    signal = analyze(df)

    candle_time = signal.get("candle_time")

    if candle_time is None:
        return None

    if last_scan.get(symbol) == candle_time:
        return None

    last_scan[symbol] = candle_time

    if signal["signal"] != "BUY":
        return None

    if signal["confidence"] < 75:
        return None

    if trader.has_position(symbol):
        return None

    if symbol in cooldown:
        if time.time() - cooldown[symbol] < COOLDOWN_SECONDS:
            return

    signal["symbol"] = symbol
    return signal

# ===========================================
# Position Management
# ===========================================

def manage_positions():   

    if not trader.positions:
        return

    closed = []

    for symbol in list(trader.positions.keys()):

        try:
            price = get_price(symbol)

            result = trader.update_position(
                symbol,
                price,
            )

           if result:

    print(
        f"[CLOSE] {symbol} "
        f"{result['reason']} "
        f"PnL={result['pnl']:.2f} USDT"
    )

    if result["pnl"] < 0:
        cooldown[symbol] = time.time()

    closed.append(symbol)

        except Exception as e:
            print(f"[POSITION ERROR] {symbol}: {e}")

    return closed


# ===========================================
# Scan Market
# ===========================================

def scan_market():

    if len(trader.positions) >= MAX_OPEN_POSITIONS:
        return

    signals = []

    for symbol in SYMBOLS:

        try:

            signal = scan_symbol(symbol)

            if signal:
                signals.append(signal)

        except Exception as e:

            print(f"[SCAN ERROR] {symbol}")
            print(e)

    signals.sort(
        key=lambda x: (x["confidence"], x.get("score", 0)),
        reverse=True,
    )

    free_slots = MAX_OPEN_POSITIONS - len(trader.positions)

    for signal in signals[:free_slots]:

        print(
            f"[{signal['symbol']}] BUY "
            f"Score={signal.get('score',0)} "
            f"Confidence={signal['confidence']}%"
        )

        trader.try_open_position(signal["symbol"], signal)


# ===========================================
# Reports
# ===========================================

last_report = time.time()

REPORT_INTERVAL = 60 * 30


def maybe_report():

    global last_report

    now = time.time()

    if now - last_report < REPORT_INTERVAL:
        return

    print()

    print_report(trader)

    print()

    last_report = now

# ===========================================
# Main Loop
# ===========================================

def main():

    print()
    print("Bot is running...")
    print()

    while True:

        try:

            # 1. Manage open positions
            manage_positions()

            # 2. Scan all markets
            scan_market()

            # 3. Print statistics
            maybe_report()

            # 4. Wait until next scan
            time.sleep(SCAN_SECONDS)

        except KeyboardInterrupt:

            print()
            print("Bot stopped.")
            break

        except Exception:

            print()
            print("=" * 60)
            print("MAIN LOOP ERROR")
            traceback.print_exc()
            print("=" * 60)
            print()

            time.sleep(10)


# ===========================================
# Start
# ===========================================

if __name__ == "__main__":

    main()
