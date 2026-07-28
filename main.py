import time
from datetime import datetime, timezone

from config import (
    SYMBOLS,
    SCAN_SECONDS,
    MAX_OPEN_POSITIONS,
    DAILY_LOSS_LIMIT_PCT,
    START_BALANCE,
)

from database import (
    init_db,
    get_positions,
    get_position,
    signal_seen,
    save_signal,
    today_pnl,
)

from market_data import get_candles, get_price
from strategy import analyze
from paper_trader import paper_buy, paper_sell
from report import print_report


last_scan_candle = {}
last_report = None


def now():
    return datetime.now(timezone.utc)


def manage_positions():
    changed = False

    for p in get_positions():
        try:
            price = get_price(p["symbol"])

            if price <= p["stop"]:
                result = paper_sell(p["symbol"], price, "STOP")
                if result:
                    changed = True
                    print(
                        f"🔴 STOP {p['symbol']} | "
                        f"Exit={result[0]:.6f} "
                        f"P/L={result[1]:+.4f}"
                    )

            elif price >= p["target"]:
                result = paper_sell(p["symbol"], price, "TARGET")
                if result:
                    changed = True
                    print(
                        f"🟢 TARGET {p['symbol']} | "
                        f"Exit={result[0]:.6f} "
                        f"P/L={result[1]:+.4f}"
                    )

        except Exception as e:
            print("❌ Position error:", p["symbol"], e)

    return changed


def scan():

    date_prefix = now().date().isoformat()

    daily = today_pnl(date_prefix)

    if daily <= -(START_BALANCE * DAILY_LOSS_LIMIT_PCT):
        print("⛔ Daily loss limit reached.")
        return False

    trade_opened = False

    for symbol in SYMBOLS:

        if len(get_positions()) >= MAX_OPEN_POSITIONS:
            break

        if get_position(symbol):
            continue

        try:

            df = get_candles(symbol)

            candle_time = df.iloc[-2]["open_time"].isoformat()

            if last_scan_candle.get(symbol) == candle_time:
                continue

            last_scan_candle[symbol] = candle_time

            a = analyze(df)

            if a["signal"] != "BUY":
                print(f"{symbol} -> WAIT ({a.get('score',0)}/5)")
                continue

            if signal_seen(symbol, candle_time):
                continue

            save_signal(
                symbol,
                candle_time,
                a["score"],
                a["rsi"],
                now().isoformat(),
            )

            price = get_price(symbol)

            trade = paper_buy(symbol, price, a["atr"])

            if trade:

                trade_opened = True

                entry, qty, stop, target = trade

                print("=" * 60)
                print(f"🟢 PAPER BUY {symbol}")
                print(f"Entry : {entry:.6f}")
                print(f"Qty   : {qty:.8f}")
                print(f"Stop  : {stop:.6f}")
                print(f"Target: {target:.6f}")
                print(f"Score : {a['score']}/5")
                print(f"RSI   : {a['rsi']:.1f}")
                print("=" * 60)

        except Exception as e:
            print("❌ Scan error:", symbol, e)

    return trade_opened


def main():

    global last_report

    init_db()

    print("=" * 50)
    print("TRADING BOT V1.1")
    print("PAPER MODE ONLY")
    print("Start balance: 50 USDT")
    print("=" * 50)

    print_report()

    while True:

        position_changed = manage_positions()

        trade_opened = scan()

        current_time = now()

        if (
            last_report is None
            or (current_time - last_report).total_seconds() >= 1800
            or trade_opened
            or position_changed
        ):
            print_report()
            last_report = current_time

        time.sleep(SCAN_SECONDS)


if __name__ == "__main__":
    main()
