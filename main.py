import time
import traceback
import config

from scanner import scan_market
from paper_trader import PaperTrader
from report import print_report
from database import init_db, save_trade
from logger import info, warning, error, signal
from market_data import get_price

init_db()
trader = PaperTrader()
last_report = time.time()
REPORT_SECONDS = config.REPORT_INTERVAL_MINUTES * 60
cooldown = {}
COOLDOWN_SECONDS = config.COOLDOWN_HOURS * 3600

info("=" * 65)
info("Trading Bot V4 Started")
info(f"Start balance: {trader.start_balance:.2f} USDT")
info(f"Risk/trade: {trader.risk_percent:.1f}%")
info(f"Max positions: {trader.max_open_positions}")
info("=" * 65)

def manage_positions():
    for symbol in list(trader.positions.keys()):
        try:
            price = get_price(symbol)
            result = trader.update_position(symbol, price)
            if result:
                save_trade(result)
                if result["pnl"] < 0:
                    cooldown[symbol] = time.time()
                    warning(f"[LOSS] {symbol} {result['pnl']:+.4f} USDT")
                else:
                    info(f"[WIN] {symbol} {result['pnl']:+.4f} USDT")
        except Exception as exc:
            error(f"POSITION ERROR {symbol}: {exc}")

def scan():
    if trader.free_slots() <= 0:
        info("No free slots")
        return

    signals = scan_market()
    info(f"scan_market returned {len(signals)} signals")

    for s in signals:
        if trader.free_slots() <= 0:
            break
        symbol = s["symbol"]

        if symbol in cooldown and time.time() - cooldown[symbol] < COOLDOWN_SECONDS:
            continue
        if s["signal"] != "BUY" or s["confidence"] < config.BUY_SCORE:
            continue

        if trader.try_open_position(symbol, s):
            signal(
                f"{symbol} BUY Score={s['score']} "
                f"Confidence={s['confidence']} Quality={s['quality']}"
            )

def main():
    while True:
        try:
            info("=== LOOP START ===")
            manage_positions()

            stats = trader.stats()
            print(
                f"BALANCE: {stats['balance']:.2f} | "
                f"EQUITY: {stats['equity']:.2f} | "
                f"OPEN_PNL: {stats['open_pnl']:+.2f} | "
                f"POSITIONS: {stats['positions']}"
            )

            scan()

            if time.time() - last_report >= REPORT_SECONDS:
                print_report(trader)
                globals()["last_report"] = time.time()

            time.sleep(config.SCAN_SECONDS)

        except KeyboardInterrupt:
            info("Bot stopped.")
            break
        except Exception as exc:
            error(f"MAIN LOOP ERROR: {exc}")
            traceback.print_exc()
            time.sleep(10)

if __name__ == "__main__":
    main()
