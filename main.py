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

REPORT_SECONDS = (
    config.REPORT_INTERVAL_MINUTES * 60
)

cooldown = {}

COOLDOWN_SECONDS = (
    config.COOLDOWN_HOURS * 3600
)


# =========================================================
# STARTUP
# =========================================================

info("=" * 65)
info("Trading Bot V4 Started")
info(f"Start balance: {trader.start_balance:.2f} USDT")
info(f"Risk/trade: {trader.risk_percent:.1f}%")
info(f"Max positions: {trader.max_open_positions}")

# Quality settings
info(
    f"Quality mode: Score >= "
    f"{getattr(config, 'QUALITY_SCORE', 90)}"
)

info(
    f"Required quality: "
    f"{getattr(config, 'REQUIRED_QUALITY', 'A+')}"
)

info("=" * 65)


# =========================================================
# POSITION MANAGEMENT
# =========================================================

def manage_positions():

    for symbol in list(trader.positions.keys()):

        try:

            price = get_price(symbol)

            if price is None:
                continue

            result = trader.update_position(
                symbol,
                price
            )

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
                f"POSITION ERROR "
                f"{symbol}: {exc}"
            )


# =========================================================
# QUALITY CHECK
# =========================================================

def is_quality_buy(s):

    if not s:
        return False

    signal_type = str(
        s.get("signal", "")
    ).upper()

    score = float(
        s.get("score", 0) or 0
    )

    confidence = float(
        s.get("confidence", 0) or 0
    )

    quality = str(
        s.get("quality", "")
    ).upper()

    required_score = float(
        getattr(
            config,
            "QUALITY_SCORE",
            90
        )
    )

    required_quality = str(
        getattr(
            config,
            "REQUIRED_QUALITY",
            "A+"
        )
    ).upper()

    # -----------------------------------------------------
    # REAL BUY SIGNAL
    # -----------------------------------------------------

    if signal_type != "BUY":

        return False

    # -----------------------------------------------------
    # SCORE
    # -----------------------------------------------------

    if score < required_score:

        return False

    # -----------------------------------------------------
    # QUALITY
    # -----------------------------------------------------

    if quality != required_quality:

        return False

    # -----------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------

    if confidence < 85:

        return False

    return True


# =========================================================
# SCAN
# =========================================================

def scan():

    if trader.free_slots() <= 0:

        info("No free slots")

        return

    try:

        signals = scan_market()

    except Exception as exc:

        error(
            f"SCAN ERROR: {exc}"
        )

        return

    info(
        f"scan_market returned "
        f"{len(signals)} signals"
    )

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
        f"[TOP] "
        f"{top.get('symbol')} "
        f"{top.get('signal')} "
        f"Score={top.get('score')} "
        f"Confidence={top.get('confidence')} "
        f"Quality={top.get('quality')}"
    )

    # -----------------------------------------------------
    # FIND QUALITY BUY
    # -----------------------------------------------------

    quality_buys = []

    for s in signals:

        if is_quality_buy(s):

            quality_buys.append(s)

    # -----------------------------------------------------
    # NO QUALITY SIGNAL
    # -----------------------------------------------------

    if not quality_buys:

        info(
            "[QUALITY] No A+ setup "
            "found this scan"
        )

        return

    # -----------------------------------------------------
    # SORT BEST FIRST
    # -----------------------------------------------------

    quality_buys.sort(
        key=lambda x: (
            float(x.get("score", 0) or 0),
            float(x.get("confidence", 0) or 0),
            float(x.get("adx", 0) or 0),
            float(x.get("momentum", 0) or 0),
            float(x.get("volume_ratio", 0) or 0),
        ),
        reverse=True
    )

    # -----------------------------------------------------
    # OPEN POSITIONS
    # -----------------------------------------------------

    for s in quality_buys:

        if trader.free_slots() <= 0:

            break

        symbol = s.get("symbol")

        if not symbol:

            continue

        # -------------------------------------------------
        # COOLDOWN
        # -------------------------------------------------

        if (
            symbol in cooldown
            and
            time.time() - cooldown[symbol]
            < COOLDOWN_SECONDS
        ):

            info(
                f"[COOLDOWN] {symbol}"
            )

            continue

        # -------------------------------------------------
        # FINAL VALIDATION
        # -------------------------------------------------

        if not is_quality_buy(s):

            continue

        info(
            f"[QUALITY BUY] "
            f"{symbol} "
            f"Score={s.get('score')} "
            f"Confidence={s.get('confidence')} "
            f"Quality={s.get('quality')}"
        )

        # -------------------------------------------------
        # OPEN
        # -------------------------------------------------

        try:

            opened = trader.try_open_position(
                symbol,
                s
            )

        except Exception as exc:

            error(
                f"OPEN ERROR "
                f"{symbol}: {exc}"
            )

            continue

        if opened:

            signal(
                f"🔥 {symbol} BUY "
                f"Score={s.get('score')} "
                f"Confidence={s.get('confidence')} "
                f"Quality={s.get('quality')}"
            )

        else:

            warning(
                f"[OPEN FAILED] "
                f"{symbol}"
            )


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    global last_report

    while True:

        try:

            info(
                "=== LOOP START ==="
            )

            # ---------------------------------------------
            # POSITIONS
            # ---------------------------------------------

            manage_positions()

            # ---------------------------------------------
            # STATS
            # ---------------------------------------------

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

            # ---------------------------------------------
            # SCAN
            # ---------------------------------------------

            scan()

            # ---------------------------------------------
            # REPORT
            # ---------------------------------------------

            if (
                time.time() - last_report
                >= REPORT_SECONDS
            ):

                print_report(trader)

                last_report = time.time()

            # ---------------------------------------------
            # WAIT
            # ---------------------------------------------

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
# ENTRY
# =========================================================

if __name__ == "__main__":

    main()
