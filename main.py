import time
import traceback
from datetime import datetime

from config import (
    SYMBOLS,
    SCAN_SECONDS,
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

print("=" * 60)
print("Trading Bot V2 - PAPER MODE")
from datetime import datetime, UTC
print("=" * 60)

def scan_symbol(symbol):

    df = get_candles(symbol)

    signal = analyze(df)

    candle_time = signal.get("candle_time")

    if candle_time is None:
        return

    if last_scan.get(symbol) == candle_time:
        return

    last_scan[symbol] = candle_time

    print(
        f"[{symbol}] "
        f"{signal['signal']} "
        f"Score={signal.get('score',0)} "
        f"Confidence={signal.get('confidence',0)}%"
    )

    if signal["signal"] != "BUY":
        return

    print(f"[TRY OPEN] {symbol}")

    trader.try_open_position(
        symbol,
        signal,
    )

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

                closed.append(symbol)

        except Exception as e:
            print(f"[POSITION ERROR] {symbol}: {e}")

    return closed


# ===========================================
# Scan Market
# ===========================================

def scan_market():

    for symbol in SYMBOLS:

        try:
            scan_symbol(symbol)

        except Exception as e:

            print(f"[SCAN ERROR] {symbol}")

            print(e)


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
    print("Bot is running... VERSION TEST 123")
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
