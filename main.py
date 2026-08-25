import json
import logging
import math
import os
import time

from datetime import datetime, timezone

from config import BUY_SCORE

from market_data import get_candles
from scanner import scan_market


START_BALANCE = float(
    os.getenv("START_BALANCE", "100")
)

RISK_PER_TRADE = float(
    os.getenv("RISK_PER_TRADE", "0.01")
)

MAX_POSITIONS = int(
    os.getenv("MAX_POSITIONS", "3")
)

SCAN_SECONDS = int(
    os.getenv("SCAN_SECONDS", "60")
)

SL_ATR = float(
    os.getenv("SL_ATR", "1.5")
)

TP_ATR = float(
    os.getenv("TP_ATR", "2.4")
)

TRAIL_ATR = float(
    os.getenv("TRAIL_ATR", "1.2")
)

FEE_RATE = float(
    os.getenv("FEE_RATE", "0.0004")
)

SLIPPAGE = float(
    os.getenv("SLIPPAGE", "0.0002")
)

STATE_FILE = os.getenv(
    "STATE_FILE",
    "trading_state_v5.json"
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

log = logging.getLogger(
    "TradingBotV5"
)


def sf(value, default=0.0):
    try:
        value = float(value)

        if math.isfinite(value):
            return value

        return default

    except Exception:
        return default


def load():

    if os.path.exists(STATE_FILE):

        try:

            with open(
                STATE_FILE,
                encoding="utf-8"
            ) as f:

                state = json.load(f)

            state.setdefault(
                "balance",
                START_BALANCE
            )

            state.setdefault(
                "start_balance",
                START_BALANCE
            )

            state.setdefault(
                "positions",
                {}
            )

            state.setdefault(
                "trades",
                []
            )

            return state

        except Exception as exc:

            log.warning(
                "state load failed: %s",
                exc
            )

    return {
        "balance": START_BALANCE,
        "start_balance": START_BALANCE,
        "positions": {},
        "trades": [],
    }


state = load()


def save():

    tmp_file = STATE_FILE + ".tmp"

    with open(
        tmp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            state,
            f,
            indent=2
        )

    os.replace(
        tmp_file,
        STATE_FILE
    )


def pnl_open():

    total = 0.0

    for position in state["positions"].values():

        total += (
            (
                sf(position["last_price"])
                - sf(position["entry"])
            )
            * sf(position["qty"])
        )

    return total


def equity():

    return (
        sf(state["balance"])
        + pnl_open()
    )


def account():

    print(
        f"BALANCE: {state['balance']:.2f} "
        f"| EQUITY: {equity():.2f} "
        f"| OPEN_PNL: {pnl_open():+.2f} "
        f"| POSITIONS: {len(state['positions'])}"
    )


def position_size(
    entry,
    stop,
    quality_factor
):

    risk = max(
        0.0,
        equity() * RISK_PER_TRADE
    )

    distance = abs(
        entry - stop
    )

    if risk <= 0 or distance <= 0:
        return 0.0

    factor = max(
        0.35,
        min(1.0, quality_factor)
    )

    qty = (
        risk
        / distance
        * factor
    )

    max_qty = (
        state["balance"]
        * 0.95
        / entry
    )

    return min(
        qty,
        max(0.0, max_qty)
    )


def open_position(signal):

    symbol = signal["symbol"]

    if symbol in state["positions"]:

        log.info(
            "[SKIP] %s already has position",
            symbol
        )

        return

    if len(state["positions"]) >= MAX_POSITIONS:

        log.info(
            "[SKIP] Max positions reached"
        )

        return

    entry = (
        sf(signal["close"])
        * (1 + SLIPPAGE)
    )

    atr_value = sf(
        signal["atr"]
    )

    if entry <= 0 or atr_value <= 0:
        return

    stop = (
        entry
        - atr_value * SL_ATR
    )

    target = (
        entry
        + atr_value * TP_ATR
    )

    quality_factor = sf(
        signal.get(
            "quality_factor",
            0.70
        ),
        0.70
    )

    qty = position_size(
        entry,
        stop,
        quality_factor
    )

    fee = (
        entry
        * qty
        * FEE_RATE
    )

    required = (
        entry * qty
        + fee
    )

    if (
        qty <= 0
        or required > state["balance"]
    ):
        return

    state["balance"] -= fee

    state["positions"][symbol] = {

        "symbol": symbol,

        "entry": entry,

        "qty": qty,

        "stop": stop,

        "target": target,

        "highest": entry,

        "last_price": entry,

        "opened_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "score":
            signal["score"],

        "confidence":
            signal["confidence"],

        "quality":
            signal["quality"],

        "confirmations":
            signal.get(
                "confirmations",
                0
            ),

        "quality_factor":
            quality_factor,

        "atr":
            atr_value,
    }

    save()

    log.info(
        "[OPEN] %s "
        "Entry=%.6f "
        "Qty=%.6f "
        "SL=%.6f "
        "TP=%.6f "
        "Risk=%.4f "
        "Score=%s "
        "Conf=%s "
        "Q=%s",
        symbol,
        entry,
        qty,
        stop,
        target,
        (entry - stop) * qty,
        signal["score"],
        signal["confidence"],
        signal["quality"],
    )


def close_position(
    symbol,
    price,
    reason
):

    position = state["positions"].get(
        symbol
    )

    if not position:
        return

    exit_price = (
        sf(price)
        * (1 - SLIPPAGE)
    )

    qty = sf(
        position["qty"]
    )

    entry = sf(
        position["entry"]
    )

    net = (
        (exit_price - entry) * qty
        - exit_price
        * qty
        * FEE_RATE
    )

    state["balance"] += net

    state["trades"].append({

        "symbol": symbol,

        "entry": entry,

        "exit": exit_price,

        "qty": qty,

        "pnl": net,

        "reason": reason,

        "opened_at":
            position.get(
                "opened_at"
            ),

        "closed_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    })

    del state["positions"][symbol]

    save()

    log.info(
        "[CLOSE] %s "
        "Exit=%.6f "
        "PNL=%+.4f "
        "Reason=%s",
        symbol,
        exit_price,
        net,
        reason,
    )


def update_positions():

    for symbol in list(
        state["positions"]
    ):

        position = state["positions"].get(
            symbol
        )

        try:

            candles = get_candles(
                symbol,
                "1m"
            )

            if (
                candles is None
                or len(candles) < 3
            ):
                continue

            row = candles.iloc[-1]

            close = sf(
                row["close"]
            )

            high = sf(
                row["high"]
            )

            low = sf(
                row["low"]
            )

            position["last_price"] = close

            position["highest"] = max(
                sf(position["highest"]),
                high
            )

            entry = sf(
                position["entry"]
            )

            atr_value = sf(
                position["atr"]
            )

            stop = sf(
                position["stop"]
            )

            target = sf(
                position["target"]
            )

            highest = sf(
                position["highest"]
            )

            # Break-even protection
            if (
                atr_value
                and highest >= entry + atr_value
            ):

                stop = max(
                    stop,
                    entry
                    + atr_value * 0.10
                )

            # Trailing stop
            if (
                atr_value
                and highest >= entry + atr_value * 1.5
            ):

                stop = max(
                    stop,
                    highest
                    - atr_value * TRAIL_ATR
                )

            position["stop"] = stop

            # If SL and TP are hit
            # in the same candle,
            # SL is assumed first.

            if low <= stop:

                close_position(
                    symbol,
                    stop,
                    "SL"
                )

            elif high >= target:

                close_position(
                    symbol,
                    target,
                    "TP"
                )

        except Exception as exc:

            log.warning(
                "[POSITION ERROR] %s: %s",
                symbol,
                exc
            )

    save()


def stats():

    trades = state["trades"]

    wins = sum(
        sf(t.get("pnl")) > 0
        for t in trades
    )

    losses = (
        len(trades)
        - wins
    )

    gross_profit = sum(
        sf(t.get("pnl"))
        for t in trades
        if sf(t.get("pnl")) > 0
    )

    gross_loss = abs(
        sum(
            sf(t.get("pnl"))
            for t in trades
            if sf(t.get("pnl")) < 0
        )
    )

    if gross_loss:

        profit_factor = (
            gross_profit
            / gross_loss
        )

    elif gross_profit:

        profit_factor = float("inf")

    else:

        profit_factor = 0

    win_rate = (
        wins
        / len(trades)
        * 100
        if trades
        else 0
    )

    pf_text = (
        "INF"
        if math.isinf(profit_factor)
        else f"{profit_factor:.2f}"
    )

    realized = (
        state["balance"]
        - state["start_balance"]
    )

    print(
        f"TRADES: {len(trades)} "
        f"| WINS: {wins} "
        f"| LOSSES: {losses} "
        f"| WIN RATE: {win_rate:.1f}% "
        f"| PROFIT FACTOR: {pf_text} "
        f"| REALIZED P/L: {realized:+.2f}"
    )


def main():

    log.info(
        "================================================================="
    )

    log.info(
        "Trading Bot V5 Started"
    )

    log.info(
        "================================================================="
    )

    account()

    log.info(
        "Start balance: %.2f USDT",
        START_BALANCE
    )

    log.info(
        "Risk/trade: %.1f%%",
        RISK_PER_TRADE * 100
    )

    log.info(
        "Max positions: %s",
        MAX_POSITIONS
    )

    log.info(
        "BUY score threshold: %s",
        max(70, int(BUY_SCORE))
    )

    log.info(
        "================================================================="
    )

    log.info(
        "=== LOOP START ==="
    )

    while True:

        try:

            update_positions()

            account()

            signals = scan_market()

            log.info(
                "scan_market returned %s signals",
                len(signals)
            )

            buys = [
                x
                for x in signals
                if x.get("signal") == "BUY"
            ]

            # Най-добрите BUY сигнали първи.
            # Използваме get(), за да няма
            # KeyError при стар сигнал/стара версия.

            buys.sort(
                key=lambda x: (
                    x.get("quality_factor", 0.0),
                    x.get("score", 0),
                    x.get("confidence", 0),
                    x.get("confirmations", 0),
                ),
                reverse=True,
            )

            for signal in buys:

                if signal.get("quality") in (
                    "A+",
                    "A",
                    "B",
                ):

                    open_position(
                        signal
                    )

            account()

            stats()

        except Exception as exc:

            log.exception(
                "[LOOP ERROR] %s",
                exc
            )

        time.sleep(
            max(
                10,
                SCAN_SECONDS
            )
        )


if __name__ == "__main__":
    main()
