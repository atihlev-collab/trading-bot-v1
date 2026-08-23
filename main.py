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
# INIT
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
info("=" * 65)

info(
    f"Start balance: "
    f"{trader.start_balance:.2f} USDT"
)

info(
    f"Risk/trade: "
    f"{trader.risk_percent:.1f}%"
)

info(
    f"Max positions: "
    f"{trader.max_open_positions}"
)

info(
    f"BUY score threshold: "
    f"{config.BUY_SCORE}"
)

info("=" * 65)


# =========================================================
# POSITION MANAGEMENT
# =========================================================

def manage_positions():

    if not trader.positions:
        return

    for symbol in list(trader.positions.keys()):

        try:

            price = get_price(symbol)

            if price is None:
                warning(
                    f"[PRICE] No price for {symbol}"
                )
                continue

            result = trader.update_position(
                symbol,
                price
            )

            if not result:
                continue

            save_trade(result)

            pnl = result["pnl"]

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
                f"[POSITION ERROR] "
                f"{symbol}: {exc}"
            )


# =========================================================
# MARKET SCAN
# =========================================================

def scan():

    # -----------------------------------------------------
    # No free positions
    # -----------------------------------------------------

    if trader.free_slots() <= 0:

        info("[SCAN] No free slots")

        return


    # -----------------------------------------------------
    # Call scanner
    # -----------------------------------------------------

    try:

        signals = scan_market()

    except Exception as exc:

        error(
            f"[SCANNER ERROR] {exc}"
        )

        traceback.print_exc()

        return


    # -----------------------------------------------------
    # Scanner returned nothing
    # -----------------------------------------------------

    if not signals:

        info(
            "[QUALITY] "
            "No candidates returned by scanner"
        )

        return


    info(
        f"scan_market returned "
        f"{len(signals)} signals"
    )


    # =====================================================
    # PROCESS SIGNALS
    # =====================================================

    for s in signals:

        try:

            if trader.free_slots() <= 0:
                break


            symbol = s.get("symbol")

            if not symbol:
                continue


            signal_type = s.get(
                "signal",
                "WAIT"
            )

            score = float(
                s.get("score", 0)
            )

            confidence = float(
                s.get("confidence", 0)
            )

            quality = s.get(
                "quality",
                "C"
            )


            # -------------------------------------------------
            # SHOW TOP SCANNER RESULT
            # -------------------------------------------------

            info(
                f"[TOP] {symbol} "
                f"{signal_type} "
                f"Score={score:.0f} "
                f"Confidence={confidence:.0f} "
                f"Quality={quality}"
            )


            # -------------------------------------------------
            # ONLY BUY SIGNALS CAN OPEN POSITIONS
            # -------------------------------------------------

            if signal_type != "BUY":

                continue


            # -------------------------------------------------
            # SCORE FILTER
            #
            # IMPORTANT:
            # Do NOT require A+ here.
            # BUY_SCORE comes from config.py.
            # -------------------------------------------------

            if score < config.BUY_SCORE:

                info(
                    f"[SKIP] {symbol} "
                    f"Score {score:.0f} "
                    f"< BUY_SCORE "
                    f"{config.BUY_SCORE}"
                )

                continue


            # -------------------------------------------------
            # CONFIDENCE
            #
            # Scanner already calculates confidence.
            # Keep it consistent with BUY score.
            # -------------------------------------------------

            if confidence < config.BUY_SCORE:

                info(
                    f"[SKIP] {symbol} "
                    f"Confidence {confidence:.0f} "
                    f"< {config.BUY_SCORE}"
                )

                continue


            # -------------------------------------------------
            # EXISTING POSITION
            # -------------------------------------------------

            if trader.has_position(symbol):

                info(
                    f"[SKIP] {symbol} "
                    f"already has position"
                )

                continue


            # -------------------------------------------------
            # COOLDOWN AFTER LOSS
            # -------------------------------------------------

            if symbol in cooldown:

                elapsed = (
                    time.time()
                    - cooldown[symbol]
                )

                if elapsed < COOLDOWN_SECONDS:

                    remaining = (
                        COOLDOWN_SECONDS
                        - elapsed
                    )

                    info(
                        f"[COOLDOWN] {symbol} "
                        f"{remaining / 60:.0f} min remaining"
                    )

                    continue

                else:

                    del cooldown[symbol]


            # -------------------------------------------------
            # OPEN POSITION
            # -------------------------------------------------

            opened = trader.try_open_position(
                symbol,
                s
            )


            if opened:

                signal(
                    f"{symbol} BUY "
                    f"Score={score:.0f} "
                    f"Confidence={confidence:.0f} "
                    f"Quality={quality}"
                )

            else:

                warning(
                    f"[OPEN FAILED] "
                    f"{symbol}"
                )


        except Exception as exc:

            error(
                f"[SIGNAL ERROR] "
                f"{exc}"
            )

            traceback.print_exc()


# =========================================================
# REPORT
# =========================================================

def report():

    global last_report

    now = time.time()

    if (
        now - last_report
        >= REPORT_SECONDS
    ):

        try:

            print_report(trader)

        except Exception as exc:

            error(
                f"[REPORT ERROR] {exc}"
            )

        last_report = now


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    info("=== LOOP START ===")

    while True:

        try:

            # =================================================
            # 1. MANAGE OPEN POSITIONS
            # =================================================

            manage_positions()


            # =================================================
            # 2. ACCOUNT STATUS
            # =================================================

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


            # =================================================
            # 3. SCAN MARKET
            # =================================================

            scan()


            # =================================================
            # 4. PERIODIC REPORT
            # =================================================

            report()


            # =================================================
            # 5. WAIT
            # =================================================

            time.sleep(
                config.SCAN_SECONDS
            )


        except KeyboardInterrupt:

            info(
                "Bot stopped."
            )

            break


        except Exception as exc:

            error(
                f"[MAIN LOOP ERROR] "
                f"{exc}"
            )

            traceback.print_exc()

            time.sleep(10)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
