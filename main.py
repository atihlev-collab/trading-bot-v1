import time
from datetime import datetime, timezone
from config import (
    SYMBOLS, SCAN_SECONDS, MAX_OPEN_POSITIONS,
    DAILY_LOSS_LIMIT_PCT, START_BALANCE
)
from database import (
    init_db, get_positions, get_position, signal_seen,
    save_signal, today_pnl
)
from market_data import get_candles, get_price
from strategy import analyze
from paper_trader import paper_buy, paper_sell
from report import print_report

def now():
    return datetime.now(timezone.utc)

def manage_positions():
    for p in get_positions():
        try:
            price = get_price(p["symbol"])
            if price <= p["stop"]:
                result = paper_sell(p["symbol"], price, "STOP")
                if result:
                    print(f"🔴 STOP {p['symbol']} @ {result[0]:.6f} P/L={result[1]:+.4f}")
            elif price >= p["target"]:
                result = paper_sell(p["symbol"], price, "TARGET")
                if result:
                    print(f"🟢 TARGET {p['symbol']} @ {result[0]:.6f} P/L={result[1]:+.4f}")
        except Exception as e:
            print("Position error:", p["symbol"], e)

def scan():
    date_prefix = now().date().isoformat()
    daily = today_pnl(date_prefix)
    if daily <= -(START_BALANCE * DAILY_LOSS_LIMIT_PCT):
        print("⛔ Daily loss limit reached. No new entries today.")
        return

    for symbol in SYMBOLS:
        if len(get_positions()) >= MAX_OPEN_POSITIONS:
            break
        if get_position(symbol):
            continue

        try:
            df = get_candles(symbol)
            a = analyze(df)
            if a["signal"] != "BUY":
                continue
            if signal_seen(symbol, a["candle_time"]):
                continue

            save_signal(symbol, a["candle_time"], a["score"], a["rsi"], now().isoformat())
            price = get_price(symbol)
            trade = paper_buy(symbol, price, a["atr"])
            if trade:
                entry, qty, stop, target = trade
                print(
                    f"🟢 PAPER BUY {symbol} | entry={entry:.6f} qty={qty:.8f} "
                    f"stop={stop:.6f} target={target:.6f} "
                    f"score={a['score']}/5 RSI={a['rsi']:.1f}"
                )
        except Exception as e:
            print("Scan error:", symbol, e)

def main():
    init_db()
    print("==============================================")
    print(" TRADING BOT V1 — PAPER MODE ONLY")
    print(" Virtual start balance: 50 USDT")
    print(" NO API KEY | NO REAL ORDERS | NO LEVERAGE")
    print("==============================================")
    print_report()

    while True:
        manage_positions()
        scan()
        print_report()
        time.sleep(SCAN_SECONDS)

if __name__ == "__main__":
    main()
