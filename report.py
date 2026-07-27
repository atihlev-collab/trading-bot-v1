from database import stats, get_positions
from market_data import get_price
from config import START_BALANCE

def print_report():
    cash, realized, count, wins, pnl, pf = stats()
    positions = get_positions()
    equity = cash
    for p in positions:
        try:
            equity += get_price(p["symbol"]) * p["qty"]
        except Exception:
            equity += p["entry"] * p["qty"]

    ret = (equity / START_BALANCE - 1) * 100
    win_rate = (wins/count*100) if count else 0
    pf_text = "∞" if pf == float("inf") else f"{pf:.2f}"

    print("\n========== PAPER REPORT ==========")
    print(f"Start:       {START_BALANCE:.2f} USDT")
    print(f"Cash:        {cash:.2f} USDT")
    print(f"Equity:      {equity:.2f} USDT")
    print(f"Return:      {ret:+.2f}%")
    print(f"Realized:    {realized:+.2f} USDT")
    print(f"Trades:      {count}")
    print(f"Win rate:    {win_rate:.1f}%")
    print(f"Profit fact: {pf_text}")
    print(f"Open pos.:   {len(positions)}")
    print("==================================\n")
