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
# QUALITY SETTINGS
# =========================================================

QUALITY_SCORE = getattr(config, "QUALITY_SCORE", 90)
REQUIRED_QUALITY = getattr(config, "REQUIRED_QUALITY", "A+")


# =========================================================
# STARTUP
# =========================================================

info("=" * 65)
info("Trading Bot V4 Started")
info(f"Start balance: {trader.start_balance:.2f} USDT")
info(f"Risk/trade: {trader.risk_percent:.1f}%")
info(f"Max positions: {trader.max_open_positions}")
info(f"Quality mode: Score >= {QUALITY_SCORE}")
info(f"Required quality: {REQUIRED_QUALITY}")
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

                pnl = result["pnl"]

                if pnl < 0:

                    cooldown[symbol] = time.time()

                    warning(
                        f"[LOSS] {symbol} {pnl:+.4f} USDT"
                    )

                else:

                    info(
                        f"[WIN] {symbol} {pnl:+.4f} USDT"
                    )

        except Exception as exc:

            error(
                f"POSITION ERROR {symbol}: {exc}"
            )


# =========================================================
# QUALITY CHECK
# =========================================================

def is_quality_setup(s):

    if not isinstance(s, dict):
        return False

    signal_type = str(
        s.get("signal", "")
    ).upper()

    score = float(
        s.get("score", 0) or 0
    )

    quality = str(
        s.get("quality", "")
    ).upper().strip()

    symbol = s.get(
        "symbol",
        "UNKNOWN"
    )

    # -----------------------------------------------------
    # MUST BE BUY
    # -----------------------------------------------------

    if signal_type != "BUY":

        info(
            f"[SKIP] {symbol} "
            f"signal={signal_type}"
        )

        return False

    # -----------------------------------------------------
    # SCORE
    # -----------------------------------------------------

    if score < QUALITY_SCORE:

        info(
            f"[SKIP] {symbol} "
            f"Score={score:.0f} < {QUALITY_SCORE}"
        )

        return False

    # -----------------------------------------------------
    # QUALITY
    # -----------------------------------------------------

    if quality != REQUIRED_QUALITY.upper():

        info(
            f"[SKIP] {symbol} "
            f"Quality={quality} "
            f"required={REQUIRED_QUALITY}"
        )

        return False

    # -----------------------------------------------------
    # PASSED
    # -----------------------------------------------------

    info(
        f"[QUALITY PASS] {symbol} "
        f"Score={score:.0f} "
        f"Quality={quality}"
    )

    return True


# =========================================================
# SCAN
# =========================================================

def scan():

    # -----------------------------------------------------
    # POSITION LIMIT
    # -----------------------------------------------------

    if trader.free_slots() <= 0:

        info(
            "[SCAN] No free position slots"
        )

        return

    # -----------------------------------------------------
    # MARKET SCAN
    # -----------------------------------------------------

    signals = scan_market()

    if signals is None:
        signals = []

    info(
        f"scan_market returned "
        f"{len(signals)} signals"
    )

    if not signals:

        return

    # -----------------------------------------------------
    # SHOW TOP SIGNAL
    # -----------------------------------------------------

    try:

        top = max(
            signals,
            key=lambda x: float(
                x.get("score", 0) or 0
            )
        )

        info(
            f"[TOP] "
            f"{top.get('symbol', 'UNKNOWN')} "
            f"{top.get('signal', 'NONE')} "
            f"Score={top.get('score', 0)} "
            f"Confidence={top.get('confidence', 0)} "
            f"Quality={top.get('quality', 'N/A')}"
        )

    except Exception:

        top = None


    # -----------------------------------------------------
    # SORT BY SCORE
    # -----------------------------------------------------

    signals = sorted(
        signals,
        key=lambda x: float(
            x.get("score", 0) or 0
        ),
        reverse=True
    )


    # -----------------------------------------------------
    # PROCESS SIGNALS
    # -----------------------------------------------------

    opened = 0
    quality_found = False

    for s in signals:

        # Stop if no positions available

        if trader.free_slots() <= 0:

            info(
                "[SCAN] Max positions reached"
            )

            break


        symbol = s.get("symbol")

        if not symbol:

            continue


        # -------------------------------------------------
        # QUALITY FILTER
        # -------------------------------------------------

        if not is_quality_setup(s):

            continue

        quality_found = True


        # -------------------------------------------------
        # COOLDOWN
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
                ) / 3600

                info(
                    f"[COOLDOWN] {symbol} "
                    f"{remaining:.2f}h remaining"
                )

                continue

            else:

                del cooldown[symbol]


        # -------------------------------------------------
        # OPEN POSITION
        # -------------------------------------------------

        try:

            opened_position = (
                trader.try_open_position(
                    symbol,
                    s
                )
            )

        except Exception as exc:

            error(
                f"[OPEN ERROR] "
                f"{symbol}: {exc}"
            )

            continue


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if opened_position:

            opened += 1

            signal(
                f"{symbol} BUY "
                f"Score={s.get('score', 0)} "
                f"Confidence={s.get('confidence', 0)} "
                f"Quality={s.get('quality', 'N/A')}"
            )

        else:

            warning(
                f"[OPEN BLOCKED] {symbol}"
            )


    # -----------------------------------------------------
    # FINAL SCAN STATUS
    # -----------------------------------------------------

    if not quality_found:

        info(
            "[QUALITY] "
            "No valid A+ BUY setup found this scan"
        )

    elif opened == 0:

        info(
            "[QUALITY] A+ setup found, "
            "but no position was opened"
        )

    else:

        info(
            f"[QUALITY] Opened {opened} "
            f"A+ position(s)"
        )


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    global last_report

    while True:

        try:

            # =============================================
            # LOOP
            # =============================================

            info("=== LOOP START ===")


            # =============================================
            # MANAGE OPEN POSITIONS
            # =============================================

            manage_positions()


            # =============================================
            # ACCOUNT STATUS
            # =============================================

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


            # =============================================
            # SCAN MARKET
            # =============================================

            scan()


            # =============================================
            # PERIODIC REPORT
            # =============================================

            if (
                time.time()
                - last_report
                >= REPORT_SECONDS
            ):

                print_report(trader)

                last_report = time.time()


            # =============================================
            # WAIT
            # =============================================

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
                f"MAIN LOOP ERROR: {exc}"
            )

            traceback.print_exc()

            time.sleep(10)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()
