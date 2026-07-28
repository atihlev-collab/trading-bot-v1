from database import stats, get_positions
from market_data import get_price
from config import START_BALANCE

def print_report(trader=None):

    cash, realized, count, wins, pnl, pf = stats()

    positions = get_positions()

    equity = cash

    unrealized = 0

    for p in positions:

        try:
            price = get_price(p["symbol"])
        except Exception:
            price = p["entry"]

        value = price * p["qty"]

        equity += value

        unrealized += (price - p["entry"]) * p["qty"]

    ret = ((equity / START_BALANCE) - 1) * 100

    win_rate = (wins / count * 100) if count else 0

    pf_text = "∞" if pf == float("inf") else f"{pf:.2f}"

    print()
    print("=" * 60)
    print("Trading Bot V2")
    print("=" * 60)

    print(f"Start Balance : {START_BALANCE:.2f} USDT")
    print(f"Cash          : {cash:.2f} USDT")
    print(f"Equity        : {equity:.2f} USDT")
    print(f"Open P/L      : {unrealized:+.2f} USDT")
    print(f"Realized P/L  : {realized:+.2f} USDT")
    print(f"Return        : {ret:+.2f}%")

    print()

    print(f"Trades        : {count}")
    print(f"Wins          : {wins}")
    print(f"Win Rate      : {win_rate:.1f}%")
    print(f"Profit Factor : {pf_text}")
    print(f"Open Positions: {len(positions)}")

    print("=" * 60)
    print()
