from config import START_BALANCE

from datetime import datetime


class PaperTrader:

    def __init__(self):

        self.start_balance = START_BALANCE

        self.balance = self.start_balance

        self.positions = {}

        self.closed_trades = []

        self.realized_pnl = 0.0

        self.open_pnl = 0.0

        self.total_trades = 0

        self.wins = 0

        self.losses = 0

        self.max_open_positions = 2

        self.risk_percent = 2.0

        self.daily_loss = 0.0

        self.max_daily_loss = 5.0

    # ==========================================
    # POSITION CHECK
    # ==========================================

    def has_position(self, symbol):

        return symbol in self.positions

    # ==========================================
    # FREE SLOTS
    # ==========================================

    def free_slots(self):

        return self.max_open_positions - len(self.positions)

    # ==========================================
    # EQUITY
    # ==========================================

    def equity(self):

        return self.balance + self.open_pnl

    # ==========================================
    # POSITION SIZE
    # ==========================================

    def calculate_position_size(

        self,

        entry,

        stop,

    ):

        risk_amount = (
            self.balance *
            self.risk_percent /
            100
        )

        stop_distance = abs(
            entry - stop
        )

        if stop_distance <= 0:
            return 0

        quantity = (
            risk_amount /
            stop_distance
        )

        value = quantity * entry

        if value > self.balance:

            value = self.balance

            quantity = value / entry

        return round(quantity, 6)

    # ==========================================
    # OPEN POSITION
    # ==========================================

    def try_open_position(

        self,

        symbol,

        signal,

    ):

        if self.has_position(symbol):
            return False

        if len(self.positions) >= self.max_open_positions:
            return False

        entry = signal["close"]

        atr = signal["atr"]

        stop = entry - atr * 2

        take = entry + atr * 5

        quantity = self.calculate_position_size(

            entry,

            stop,

        )

        if quantity <= 0:
            return False

        value = quantity * entry

        if value > self.balance + 0.01:
            print(
                f"[SKIP] {symbol} "
                f"value={value:.8f} "
                f"balance={self.balance:.8f}"
            )
            return False

        self.balance -= value

        print(
            f"[OPEN OK] {symbol} "
            f"qty={quantity} "
            f"value={value:.2f}"
        )

        self.positions[symbol] = {

            "entry": entry,

            "quantity": quantity,

            "value": value,

            "stop": stop,

            "take": take,

            "highest": entry,

            "break_even": False,

            "partial_taken": False,

            "opened": datetime.utcnow(),

        }

        self.total_trades += 1

        print(

            f"[OPEN] {symbol} "

            f"Entry={entry:.4f} "

            f"SL={stop:.4f} "

            f"TP={take:.4f}"

        )

        return True

    # ==========================================
    # UPDATE POSITION
    # ==========================================

    def update_position(
        self,
        symbol,
        price,
    ):

        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]

        # Update highest price
        if price > pos["highest"]:
            pos["highest"] = price

        # --------------------------
        # Break Even
        # --------------------------

        if (
            not pos["break_even"]
            and
            price >= pos["entry"] + (pos["take"] - pos["entry"]) * 0.30
        ):

            pos["stop"] = pos["entry"]
            pos["break_even"] = True

            print(f"[BE] {symbol} -> Stop moved to Break Even")

        # --------------------------
        # Trailing Stop
        # --------------------------

        trail = pos["highest"] * 0.985

        if trail > pos["stop"]:
            pos["stop"] = trail

        # --------------------------
        # Partial TP
        # --------------------------

        if (
            not pos["partial_taken"]
            and
            price >= pos["entry"] + (pos["take"] - pos["entry"]) * 0.60
        ):

            qty = pos["quantity"] / 2

            pnl = (
                (price - pos["entry"])
                * qty
            )

            self.balance += qty * price

            self.realized_pnl += pnl

            pos["quantity"] -= qty

            pos["partial_taken"] = True

            print(
                f"[PARTIAL] {symbol} "
                f"PnL={pnl:.2f}"
            )

        # --------------------------
        # Stop Loss
        # --------------------------

        if price <= pos["stop"]:

            return self.close_position(
                symbol,
                price,
                "STOP",
            )

        # --------------------------
        # Take Profit
        # --------------------------

        if price >= pos["take"]:

            return self.close_position(
                symbol,
                price,
                "TARGET",
            )

        # --------------------------
        # Open PnL
        # --------------------------

        self.open_pnl = 0

        for p in self.positions.values():

            self.open_pnl += (
                (price - p["entry"])
                * p["quantity"]
            )

        return None

    # ==========================================
    # CLOSE POSITION
    # ==========================================

    def close_position(
        self,
        symbol,
        price,
        reason,
    ):

        if symbol not in self.positions:
            return None

        pos = self.positions.pop(symbol)

        value = price * pos["quantity"]

        pnl = (
            price - pos["entry"]
        ) * pos["quantity"]

        self.balance += value

        self.realized_pnl += pnl

        if pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1

        self.open_pnl = 0

        return {

            "symbol": symbol,

            "reason": reason,

            "entry": pos["entry"],

            "exit": price,

            "quantity": pos["quantity"],

            "pnl": pnl,

        }

    # ==========================================
    # WIN RATE
    # ==========================================

    def win_rate(self):

        closed = self.wins + self.losses

        if closed == 0:
            return 0.0

        return round(
            self.wins / closed * 100,
            1,
        )

    # ==========================================
    # PROFIT FACTOR
    # ==========================================

    def profit_factor(self):

        profit = 0.0
        loss = 0.0

        # Ако по-късно пазим история на сделките,
        # тук ще се смята реалният Profit Factor.
        # Засега връщаме базова стойност.

        if loss == 0:
            return 0.0

        return round(
            profit / abs(loss),
            2,
        )

    # ==========================================
    # STATS
    # ==========================================

    def stats(self):

        return {

            "balance": self.balance,

            "equity": self.equity(),

            "realized": self.realized_pnl,

            "open_pnl": self.open_pnl,

            "positions": len(self.positions),

            "trades": self.total_trades,

            "wins": self.wins,

            "losses": self.losses,

            "win_rate": self.win_rate(),

            "profit_factor": self.profit_factor(),

        }
