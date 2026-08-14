from datetime import datetime, timezone

def print_report(trader):
    stats = trader.stats()
    ret = (stats["equity"] - trader.start_balance) / trader.start_balance * 100

    print()
    print("=" * 65)
    print("Trading Bot V4")
    print("=" * 65)
    print(f"Time           : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Start Balance  : {trader.start_balance:.2f} USDT")
    print(f"Cash           : {stats['balance']:.2f} USDT")
    print(f"Equity         : {stats['equity']:.2f} USDT")
    print(f"Open P/L       : {stats['open_pnl']:+.2f} USDT")
    print(f"Realized P/L   : {stats['realized']:+.2f} USDT")
    print(f"Return         : {ret:+.2f}%")
    print(f"Trades         : {stats['trades']}")
    print(f"Wins           : {stats['wins']}")
    print(f"Losses         : {stats['losses']}")
    print(f"Win Rate       : {stats['win_rate']:.1f}%")
    print(f"Profit Factor  : {stats['profit_factor']:.2f}")
    print(f"Open Positions : {stats['positions']}")
    print(f"Daily Loss     : {trader.daily_loss:.2f} USDT")
    print(f"Risk / Trade   : {trader.risk_percent:.1f}%")
    print("=" * 65)

    if trader.positions:
        print("OPEN POSITIONS")
        for symbol, pos in trader.positions.items():
            print(
                f"{symbol:10} Entry={pos['entry']:.6f} "
                f"SL={pos['stop']:.6f} TP={pos['take']:.6f}"
            )
        print("-" * 65)
