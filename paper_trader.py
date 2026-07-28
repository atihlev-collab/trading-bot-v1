from datetime import datetime, timezone

from config import (
    FEE_RATE,
    SLIPPAGE_RATE,
    RISK_PER_TRADE,
    MAX_POSITION_PCT,
    ATR_STOP_MULT,
    REWARD_RISK,
    BREAK_EVEN_AT,
    TRAILING_STOP,
    TRAILING_ATR,
)

from database import (
    get_cash,
    open_position,
    close_position,
    get_position,
)

print(">>> LOADED paper_trader.py <<<") 


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class PaperTrader:

    def __init__(self):

        self.positions = {}

        self.load_positions()

    def load_positions(self):
        self.refresh_positions()    

    def has_position(self, symbol):

        return symbol in self.positions

    def try_open_position(self, symbol, signal):

        print(">>> ENTER try_open_position <<<")

        if self.has_position(symbol):
            return False

        cash = get_cash()

        print(f"[DEBUG] {symbol} Cash={cash:.2f}")

        entry = signal["close"] * (1 + SLIPPAGE_RATE)

        atr = signal["atr"]

        stop_distance = atr * ATR_STOP_MULT

        if stop_distance <= 0:
            return False

        stop = entry - stop_distance

        target = entry + stop_distance * REWARD_RISK

        risk_budget = cash * RISK_PER_TRADE

        qty_risk = risk_budget / stop_distance

        qty_cash = (
            cash *
            MAX_POSITION_PCT /
            (entry * (1 + FEE_RATE))
        )

        qty = min(qty_risk, qty_cash)

        if qty <= 0:
            return False

        fee = qty * entry * FEE_RATE

        ok = open_position(
            symbol,
            entry,
            qty,
            stop,
            target,
            fee,
            utcnow(),
        )

        if not ok:
            print(f"[OPEN FAILED] {symbol}")
            return False

        self.positions[symbol] = {
            "entry": entry,
            "qty": qty,
            "stop": stop,
            "target": target,
            "atr": atr,
            "break_even": False,
        }

        print(
            f"[OPEN] {symbol} "
            f"Entry={entry:.2f} "
            f"SL={stop:.2f} "
            f"TP={target:.2f}"
        )

        return True

    def update_position(self, symbol, market_price):

        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]

        stop = pos["stop"]
        target = pos["target"]
        entry = pos["entry"]
        atr = pos["atr"]

        # ==========================
        # Break Even
        # ==========================

        if (
            not pos["break_even"]
            and market_price >= entry + atr * BREAK_EVEN_AT
        ):

            pos["stop"] = entry
            pos["break_even"] = True

            print(f"[BE] {symbol} -> Stop moved to Break Even")

        # ==========================
        # Trailing Stop
        # ==========================

        if TRAILING_STOP:

            new_stop = market_price - atr * TRAILING_ATR

            if new_stop > pos["stop"]:
                pos["stop"] = new_stop

        # ==========================
        # Stop Loss
        # ==========================

        if market_price <= pos["stop"]:

            exit_price = market_price * (1 - SLIPPAGE_RATE)

            db_pos = get_position(symbol)

            if not db_pos:
                return None

            exit_fee = exit_price * db_pos["qty"] * FEE_RATE

            pnl = close_position(
                symbol,
                exit_price,
                exit_fee,
                "STOP",
                utcnow(),
            )

            del self.positions[symbol]

            return {
                "reason": "STOP",
                "pnl": pnl,
            }

        # ==========================
        # Take Profit
        # ==========================

        if market_price >= target:

            exit_price = market_price * (1 - SLIPPAGE_RATE)

            db_pos = get_position(symbol)

            if not db_pos:
                return None

            exit_fee = exit_price * db_pos["qty"] * FEE_RATE

            pnl = close_position(
                symbol,
                exit_price,
                exit_fee,
                "TARGET",
                utcnow(),
            )

            del self.positions[symbol]

            return {
                "reason": "TARGET",
                "pnl": pnl,
            }

        return None

    def refresh_positions(self):
        """
        Synchronize in-memory positions with the database.
        """

        from database import get_positions

        db_positions = get_positions()

        self.positions = {}

        for p in db_positions:

            self.positions[p["symbol"]] = {
                "entry": p["entry"],
                "qty": p["qty"],
                "stop": p["stop"],
                "target": p["target"],
                "atr": max(
                    (p["target"] - p["entry"]) /
                    REWARD_RISK /
                    ATR_STOP_MULT,
                    0.0000001,
                ),
                "break_even": False,
            }
