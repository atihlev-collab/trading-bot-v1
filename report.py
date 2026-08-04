from datetime import datetime


def print_report(trader):

    stats = trader.stats()

    print()

    print("=" * 60)

    print("Trading Bot V3")

    print("=" * 60)

    print(
        f"Time          : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"Start Balance : {trader.start_balance:.2f} USDT"
    )

    print(
        f"Cash          : {stats['balance']:.2f} USDT"
    )

    print(
        f"Equity        : {stats['equity']:.2f} USDT"
    )

    print(
        f"Open P/L      : {stats['open_pnl']:+.2f} USDT"
    )

    print(
        f"Realized P/L  : {stats['realized']:+.2f} USDT"
    )

    # ==========================================
    # RETURN
    # ==========================================

    ret = (
        (
            stats["equity"]
            -
            trader.start_balance
        )
        /
        trader.start_balance
    ) * 100

    print(
        f"Return        : {ret:+.2f}%"
    )

    print(
        f"Trades        : {stats['trades']}"
    )

    print(
        f"Wins          : {stats['wins']}"
    )

    print(
        f"Losses        : {stats['losses']}"
    )

    print(
        f"Win Rate      : {stats['win_rate']:.1f}%"
    )

    print(
        f"Profit Factor : {stats['profit_factor']:.2f}"
    )

    print(
        f"Open Positions: {stats['positions']}"
    )

    print(
        f"Daily Loss    : {trader.daily_loss:.2f} USDT"
    )

    print(
        f"Risk / Trade  : {trader.risk_percent:.1f}%"
    )

    print("=" * 60)

    if trader.positions:

        print()

        print("OPEN POSITIONS")

        print("-" * 60)

        for symbol, pos in trader.positions.items():

            print(

                f"{symbol:10}"

                f" Entry={pos['entry']:.4f}"

                f" SL={pos['stop']:.4f}"

                f" TP={pos['take']:.4f}"

            )

        print("-" * 60)

    print()