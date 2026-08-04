import time
import traceback

import config
from config import BUY_SCORE

from scanner import scan_market

from paper_trader import PaperTrader

from report import print_report

from database import (
    init_db,
    save_trade,
)

from logger import *

from market_data import get_price


# ==========================================
# INIT
# ==========================================

init_db()

trader = PaperTrader()

last_report = time.time()

REPORT_SECONDS = 1800

print()

info("=" * 60)
info("Trading Bot V3 Started")
info("=" * 60)

print()

# ==========================================
# POSITION MANAGEMENT
# ==========================================

cooldown = {}

COOLDOWN_SECONDS = 7200


def manage_positions():

    closed = []

    for symbol in list(trader.positions.keys()):

        try:

            price = get_price(symbol)

            result = trader.update_position(

                symbol,

                price,

            )

            if result:

                save_trade(result)

                closed.append(result)

                if result["pnl"] < 0:

                    cooldown[symbol] = time.time()

                if result["pnl"] >= 0:

                    info(

                        f"[WIN] "

                        f"{symbol} "

                        f"{result['pnl']:.2f} USDT"

                    )

                else:

                    warning(

                        f"[LOSS] "

                        f"{symbol} "

                        f"{result['pnl']:.2f} USDT"

                    )

        except Exception as e:

            error(

                f"POSITION ERROR "

                f"{symbol} "

                f"{e}"

            )

    return closed

# ==========================================
# SCAN MARKET
# ==========================================

def scan():

    info(">>> ENTER SCAN")

    if trader.free_slots() <= 0:
        info("No free slots")
        return

    info("Calling scan_market()")
    signals = scan_market()

    info(f"scan_market returned {len(signals)} signals")

    if not signals:
        return

    if trader.free_slots() <= 0:
        return

    signals = scan_market()

    if not signals:
        return

    for trade_signal in signals:

        symbol = trade_signal["symbol"]

        if trader.free_slots() <= 0:
            break

        if trader.has_position(symbol):
            continue

        if symbol in cooldown:

            elapsed = time.time() - cooldown[symbol]

            if elapsed < COOLDOWN_SECONDS:
                continue

        if trade_signal["signal"] != "BUY":
            continue

        if trade_signal["confidence"] < BUY_SCORE:
            continue

        opened = trader.try_open_position(
            symbol,
            trade_signal,
        )
   	

        
        if opened:

            signal_msg = (

                f"{symbol} "

                f"BUY "

                f"Score={trade_signal['score']} "

                f"Confidence={trade_signal['confidence']} "

                f"Quality={trade_signal['quality']}"

            )

            signal(signal_msg)


# ==========================================
# REPORT
# ==========================================

def report():

    global last_report

    now = time.time()

    if now - last_report < REPORT_SECONDS:
        return

    print_report(trader)

    last_report = now


# ==========================================
# MAIN LOOP
# ==========================================

def main():

    info("BOT VERSION 2 - TEST")

    while True:

        info("=== LOOP START ===")
    
        try:
    
            info("manage_positions")
            manage_positions()
    
            info("scan")
            scan()
    
            info("report")
            report()
    
            info("sleep")
            time.sleep(config.SCAN_SECONDS)     

        except KeyboardInterrupt:

            info("Bot stopped.")

            break

        except Exception as e:

            error("MAIN LOOP ERROR")

            error(str(e))

            traceback.print_exc()

            time.sleep(10)


# ==========================================
# START
# ==========================================

if __name__ == "__main__":

    main()
