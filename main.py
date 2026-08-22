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
# SETTINGS — QUALITY MODE
# =========================================================

# Само наистина силни сигнали
MIN_BUY_SCORE = 90

# A+ е предпочитаното качество
REQUIRED_QUALITY = "A+"

# Минимална увереност
MIN_CONFIDENCE = 90

# Само една нова позиция от един scan
MAX_NEW_TRADES_PER_SCAN = 1


# =========================================================
# START LOG
# =========================================================

info("=" * 65)
info("Trading Bot V4 Started")
info(f"Start balance: {trader.start_balance:.2f} USDT")
info(f"Risk/trade: {trader.risk_percent:.1f}%")
info(f"Max positions: {trader.max_open_positions}")
info(f"Quality mode: Score >= {MIN_BUY_SCORE}")
info(f"Required quality: {REQUIRED_QUALITY}")
info("=" * 65)


# =========================================================
# POSITION MANAGEMENT
# =========================================================

def manage_positions():

    for symbol in list(trader.positions.keys()):

        try:

            price = get_price(symbol)

            result = trader.update_position(symbol, price)

            if result:

                save_trade(result)

                if result["pnl"] < 0:

                    cooldown[symbol] = time.time()

                    warning(
                        f"[LOSS] {symbol} "
                        f"{result['pnl']:+.4f} USDT"
                    )

                else:

                    info(
                        f"[WIN] {symbol} "
                        f"{result['pnl']:+.4f} USDT"
                    )

        except Exception as exc:

            error(
                f"POSITION ERROR {symbol}: {exc}"
            )


# =========================================================
# SIGNAL QUALITY CHECK
# =========================================================

def is_quality_signal(s):

    if not s:
        return False

    symbol = s.get("symbol")

    score = float(s.get("score", 0))

    confidence = float(
        s.get("confidence", 0)
    )

    signal_type = s.get(
        "signal",
        ""
    )

    quality = s.get(
        "quality",
        ""
    )

    # -----------------------------------------------------
    # BUY ONLY
    # -----------------------------------------------------

    if signal_type != "BUY":
        return False

    # -----------------------------------------------------
    # SCORE
    # -----------------------------------------------------

    if score < MIN_BUY_SCORE:
        return False

    # -----------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------

    if confidence < MIN_CONFIDENCE:
        return False

    # -----------------------------------------------------
    # QUALITY
    # -----------------------------------------------------

    if quality != REQUIRED_QUALITY:
        return False

    # -----------------------------------------------------
    # HTF / LTF
    # -----------------------------------------------------

    if s.get("htf_bull") is False:
        return False

    if s.get("ltf_bull") is False:
        return False

    # -----------------------------------------------------
    # ADX
    # -----------------------------------------------------

    adx = float(
        s.get("adx", 0)
    )

    if adx < 25:
        return False

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    rsi = float(
        s.get("rsi", 0)
    )

    if rsi < 52 or rsi > 68:
        return False

    # -----------------------------------------------------
    # MOMENTUM
    # -----------------------------------------------------

    momentum = float(
        s.get("momentum", 0)
    )

    if momentum < 0.003:
        return False

    # -----------------------------------------------------
    # VOLUME
    # -----------------------------------------------------

    volume = float(
        s.get("volume", 0)
    )

    volume_ma = float(
        s.get("volume_ma", 0)
    )

    if volume_ma > 0:

        volume_ratio = volume / volume_ma

        if volume_ratio < 1.20:
            return False

    # -----------------------------------------------------
    # MACD
    # -----------------------------------------------------

    macd_hist = s.get(
        "macd_hist"
    )

    if macd_hist is not None:

        try:

            if float(macd_hist) <= 0:
                return False

        except Exception:

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

        return

    # -----------------------------------------------------
    # SORT BY QUALITY
    # -----------------------------------------------------

    signals = sorted(
        signals,
        key=lambda x: (
            float(x.get("score", 0)),
            float(x.get("confidence", 0)),
            float(x.get("adx", 0)),
            float(x.get("momentum", 0)),
        ),
        reverse=True,
    )

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
    # QUALITY FILTER
    # -----------------------------------------------------

    quality_signals = []

    for s in signals:

        if is_quality_signal(s):

            quality_signals.append(s)

    if not quality_signals:

        info(
            "[QUALITY] No A+ setup "
            "found this scan"
        )

        return

    # -----------------------------------------------------
    # ONLY BEST SIGNAL
    # -----------------------------------------------------

    best = quality_signals[0]

    symbol = best["symbol"]

    info(
        f"[BEST SETUP] "
        f"{symbol} "
        f"Score={best['score']} "
        f"Confidence={best['confidence']} "
        f"Quality={best['quality']} "
        f"RSI={best.get('rsi', 0):.1f} "
        f"ADX={best.get('adx', 0):.1f} "
        f"MOM={best.get('momentum', 0):.4f}"
    )

    # -----------------------------------------------------
    # COOLDOWN
    # -----------------------------------------------------

    if (
        symbol in cooldown
        and
        time.time() - cooldown[symbol]
        < COOLDOWN_SECONDS
    ):

        info(
            f"[COOLDOWN] {symbol}"
        )

        return

    # -----------------------------------------------------
    # OPEN ONLY ONE TRADE
    # -----------------------------------------------------

    if trader.free_slots() <= 0:

        return

    try:

        opened = trader.try_open_position(
            symbol,
            best
        )

    except Exception as exc:

        error(
            f"[OPEN ERROR] "
            f"{symbol}: {exc}"
        )

        return

    if opened:

        signal(
            f"[A+ BUY] "
            f"{symbol} "
            f"Score={best['score']} "
            f"Confidence={best['confidence']} "
            f"Quality={best['quality']}"
        )

    else:

        info(
            f"[REJECTED] {symbol}"
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

            # -------------------------------------------------
            # MANAGE EXISTING POSITIONS
            # -------------------------------------------------

            manage_positions()

            # -------------------------------------------------
            # STATUS
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
            # SCAN
            # -------------------------------------------------

            scan()

            # -------------------------------------------------
            # REPORT
            # -------------------------------------------------

            if (
                time.time() - last_report
                >= REPORT_SECONDS
            ):

                print_report(trader)

                last_report = time.time()

            # -------------------------------------------------
            # WAIT
            # -------------------------------------------------

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
# RUN
# =========================================================

if __name__ == "__main__":

    main()
