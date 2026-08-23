import time
import traceback
import config

from scanner import scan_market
from paper_trader import PaperTrader
from report import print_report
from database import init_db, save_trade
from logger import info, warning, error, signal
from market_data import get_price


# =========================================================
# INITIALIZATION
# =========================================================

init_db()

trader = PaperTrader()

last_report = time.time()

REPORT_SECONDS = config.REPORT_INTERVAL_MINUTES * 60

cooldown = {}

COOLDOWN_SECONDS = config.COOLDOWN_HOURS * 3600


# =========================================================
# STARTUP
# =========================================================

info("=" * 65)
info("Trading Bot V4 Started")
info(f"Start balance: {trader.start_balance:.2f} USDT")
info(f"Risk/trade: {trader.risk_percent:.1f}%")
info(f"Max positions: {trader.max_open_positions}")

# Keep this informational only.
# Scanner remains responsible for BUY / WATCH quality.
if hasattr(config, "BUY_SCORE"):
    info(f"BUY score threshold: {config.BUY_SCORE}")

info("=" * 65)


# =========================================================
# POSITION MANAGEMENT
# =========================================================

def manage_positions():

    for symbol in list(trader.positions.keys()):

        try:

            price = get_price(symbol)

            if price is None:
                warning(f"[PRICE] No price for {symbol}")
                continue

            result = trader.update_position(symbol, price)

            if result:

                save_trade(result)

                pnl = result.get("pnl", 0)

                if pnl < 0:

                    cooldown[symbol] = time.time()

                    warning(
                        f"[LOSS] {symbol} "
                        f"{pnl:+.4f} USDT"
                    )

                else:

                    info(
                        f"[WIN] {symbol} "
                        f"{pnl:+.4f} USDT"
                    )

        except Exception as exc:

            error(
                f"POSITION ERROR {symbol}: {exc}"
            )


# =========================================================
# MARKET SCAN
# =========================================================

def scan():

    # -----------------------------------------------------
    # NO FREE POSITION SLOTS
    # -----------------------------------------------------

    if trader.free_slots() <= 0:

        info("No free slots")

        return


    # -----------------------------------------------------
    # RUN SCANNER
    # -----------------------------------------------------

    signals = scan_market()

    info(
        f"scan_market returned "
        f"{len(signals)} signals"
    )


    # -----------------------------------------------------
    # NOTHING FOUND
    # -----------------------------------------------------

    if not signals:

        info(
            "[QUALITY] No candidates "
            "returned by scanner"
        )

        return


    # -----------------------------------------------------
    # SHOW TOP SIGNAL
    # -----------------------------------------------------

    top = signals[0]

    info(
        f"[TOP] {top.get('symbol', '?')} "
        f"{top.get('signal', '?')} "
        f"Score={top.get('score', 0)} "
        f"Confidence={top.get('confidence', 0)} "
        f"Quality={top.get('quality', '?')}"
    )


    # -----------------------------------------------------
    # PROCESS SIGNALS
    # -----------------------------------------------------

    for s in signals:

        # Stop if all slots are occupied
        if trader.free_slots() <= 0:

            info("No free slots")

            break


        symbol = s.get("symbol")

        if not symbol:
            continue


        # -------------------------------------------------
        # COOLDOWN AFTER LOSS
        # -------------------------------------------------

        if symbol in cooldown:

            elapsed = time.time() - cooldown[symbol]

            if elapsed < COOLDOWN_SECONDS:

                remaining = (
                    COOLDOWN_SECONDS - elapsed
                )

                info(
                    f"[COOLDOWN] {symbol} "
                    f"{remaining / 3600:.2f}h remaining"
                )

                continue

            else:

                del cooldown[symbol]


        # -------------------------------------------------
        # SCANNER DECIDES BUY / WATCH
        # -------------------------------------------------

        if s.get("signal") != "BUY":

            continue


        # -------------------------------------------------
        # BUY SCORE
        #
        # This is only the configured BUY threshold.
        # There is NO SECOND A+ QUALITY FILTER here.
        # -------------------------------------------------

        score = s.get("score", 0)

        buy_score = getattr(
            config,
            "BUY_SCORE",
            90
        )

        if score < buy_score:

            info(
                f"[FILTER] {symbol} "
                f"Score={score} < BUY_SCORE={buy_score}"
            )

            continue


        # -------------------------------------------------
        # OPEN POSITION
        # -------------------------------------------------

        try:

            opened = trader.try_open_position(
                symbol,
                s
            )

        except Exception as exc:

            error(
                f"[OPEN ERROR] {symbol}: {exc}"
            )

            continue


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if opened:

            signal(
                f"{symbol} BUY "
                f"Score={s.get('score', 0)} "
                f"Confidence={s.get('confidence', 0)} "
                f"Quality={s.get('quality', '?')}"
            )

        else:

            warning(
                f"[OPEN FAILED] {symbol} "
                f"Score={s.get('score', 0)} "
                f"Confidence={s.get('confidence', 0)} "
                f"Quality={s.get('quality', '?')}"
            )


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    global last_report

    while True:

        try:

            # -------------------------------------------------
            # LOOP START
            # -------------------------------------------------

            info("=== LOOP START ===")


            # -------------------------------------------------
            # MANAGE EXISTING POSITIONS
            # -------------------------------------------------

            manage_positions()


            # -------------------------------------------------
            # ACCOUNT STATUS
            # -------------------------------------------------

            stats = trader.stats()

            print(
                f"BALANCE: "
                f"{stats['balance']:.2f} | "
                f"EQUITY: "
                f"{stats['equity']:.2f} | "
                f"OPEN_PNL: "
                f"{stats['open_pnl']:+.2f} | "
                f"POSITIONS: "
                f"{stats['positions']}"
            )


            # -------------------------------------------------
            # MARKET SCAN
            # -------------------------------------------------

            scan()


            # -------------------------------------------------
            # PERIODIC REPORT
            # -------------------------------------------------

            if (
                time.time() - last_report
                >= REPORT_SECONDS
            ):

                try:

                    print_report(trader)

                except Exception as exc:

                    error(
                        f"REPORT ERROR: {exc}"
                    )

                last_report = time.time()


            # -------------------------------------------------
            # WAIT
            # -------------------------------------------------

            time.sleep(
                config.SCAN_SECONDS
            )


        # =====================================================
        # STOP
        # =====================================================

        except KeyboardInterrupt:

            info("Bot stopped.")

            break


        # =====================================================
        # UNEXPECTED ERROR
        # =====================================================

        except Exception as exc:

            error(
                f"MAIN LOOP ERROR: {exc}"
            )

            traceback.print_exc()

            time.sleep(10)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()
