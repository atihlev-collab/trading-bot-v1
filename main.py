import logging
import time

from config import START_BALANCE, MAX_OPEN_POSITIONS, SCAN_SECONDS, BUY_SCORE
from market_data import get_price
from scanner import scan_market
from paper_trader import PaperTrader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("TradingBotV4")


def print_account(trader):
    stats = trader.stats()
    log.info(
        "ACCOUNT | Balance=%.2f | Equity=%.2f | OpenPnL=%+.2f | "
        "Realized=%+.2f | Trades=%d | WR=%.1f%% | PF=%.2f | Positions=%d",
        stats["balance"], stats["equity"], stats["open_pnl"],
        stats["realized"], stats["trades"], stats["win_rate"],
        stats["profit_factor"], stats["positions"],
    )


def update_open_positions(trader):
    closed = []
    for symbol in list(trader.positions.keys()):
        try:
            price = get_price(symbol)
            if price is None or price <= 0:
                continue
            result = trader.update_position(symbol, price)
            if result:
                closed.append(result)
        except Exception as exc:
            log.warning("POSITION UPDATE ERROR | %s | %s", symbol, exc)
    return closed


def select_buys(signals):
    buys = []
    for signal in signals or []:
        if signal.get("signal") != "BUY":
            continue

        quality = signal.get("quality", "")
        score = float(signal.get("score", 0) or 0)

        if quality not in ("A+", "A", "B"):
            continue
        if score < max(70, int(BUY_SCORE)):
            continue

        buys.append(signal)

    buys.sort(
        key=lambda x: (
            2 if x.get("quality") == "A+" else
            1 if x.get("quality") == "A" else 0,
            float(x.get("score", 0) or 0),
            float(x.get("confidence", 0) or 0),
            float(x.get("confirmations", 0) or 0),
            float(x.get("quality_factor", 0) or 0),
        ),
        reverse=True,
    )
    return buys


def main():
    trader = PaperTrader()

    log.info("=" * 70)
    log.info("TRADING BOT V4 STARTED")
    log.info("=" * 70)
    log.info("Start balance: %.2f USDT", START_BALANCE)
    log.info("Risk/trade: %.2f%%", trader.risk_percent)
    log.info("Max position value: %.1f%%", trader.max_position_pct * 100)
    log.info("Max open positions: %d", MAX_OPEN_POSITIONS)
    log.info("BUY score threshold: %d", max(70, int(BUY_SCORE)))
    log.info("=" * 70)

    while True:
        started = time.time()

        try:
            closed = update_open_positions(trader)

            for trade in closed:
                log.info(
                    "CLOSED | %s | Reason=%s | PnL=%+.4f",
                    trade["symbol"], trade["reason"], trade["pnl"],
                )

            signals = scan_market() or []
            log.info(
                "SCAN | %d signals | open positions=%d/%d",
                len(signals), len(trader.positions), MAX_OPEN_POSITIONS,
            )

            for signal in select_buys(signals):
                if len(trader.positions) >= MAX_OPEN_POSITIONS:
                    break

                symbol = signal.get("symbol")
                if not symbol or trader.has_position(symbol):
                    continue

                if trader.try_open_position(symbol, signal):
                    log.info(
                        "OPENED | %s | Score=%s | Conf=%s | Quality=%s",
                        symbol, signal.get("score", 0),
                        signal.get("confidence", 0), signal.get("quality", ""),
                    )

            print_account(trader)

        except KeyboardInterrupt:
            log.info("Bot stopped by user.")
            break
        except Exception as exc:
            log.exception("MAIN LOOP ERROR | %s", exc)

        elapsed = time.time() - started
        time.sleep(max(5, SCAN_SECONDS - int(elapsed)))


if __name__ == "__main__":
    main()
