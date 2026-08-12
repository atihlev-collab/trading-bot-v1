from config import START_BALANCE
from datetime import datetime, timezone

from market_data import get_price


class PaperTrader:

    def __init__(self):

        # ==========================================
        # ACCOUNT
        # ==========================================

        self.start_balance = float(START_BALANCE)
        self.balance = self.start_balance

        self.positions = {}
        self.closed_trades = []

        self.realized_pnl = 0.0
        self.open_pnl = 0.0

        # ==========================================
        # STATISTICS
        # ==========================================

        self.total_trades = 0
        self.wins = 0
        self.losses = 0

        # ==========================================
        # RISK MANAGEMENT
        # ==========================================

        # Risk per trade
        from config import (
        RISK_PER_TRADE,
        MAX_POSITION_PCT,
        MAX_OPEN_POSITIONS,
        DAILY_LOSS_LIMIT,
        )

        self.risk_percent = RISK_PER_TRADE * 100
        self.max_position_pct = MAX_POSITION_PCT
        self.max_open_positions = MAX_OPEN_POSITIONS

        # Maximum realized loss allowed per day
        self.max_daily_loss = (
            self.start_balance * DAILY_LOSS_LIMIT
        )
        self.daily_loss = 0.0
        self.daily_date = datetime.now(
            timezone.utc
        ).date()

        # ==========================================
        # POSITION MANAGEMENT
        # ==========================================

        # Initial stop = 2 ATR
        self.stop_atr = 2.0

        # Final target = 5 ATR
        self.take_atr = 5.0

        # Move SL to BE after +1R
        self.break_even_r = 1.0

        # Take 50% after +2R
        self.partial_r = 2.0

        # ==========================================
        # STARTUP
        # ==========================================

        print(
            f"[TRADER] START BALANCE = "
            f"{self.start_balance:.2f} USDT"
        )

        print(
            f"[TRADER] RISK / TRADE = "
            f"{self.risk_percent:.1f}%"
        )

        print(
            f"[TRADER] MAX POSITIONS = "
            f"{self.max_open_positions}"
        )

    # ==========================================
    # DAILY RESET
    # ==========================================

    def _reset_daily_loss(self):

        today = datetime.now(
            timezone.utc
        ).date()

        if today != self.daily_date:

            self.daily_date = today
            self.daily_loss = 0.0

            print("[RISK] Daily loss reset")

    # ==========================================
    # POSITION CHECK
    # ==========================================

    def has_position(self, symbol):

        return symbol in self.positions

    # ==========================================
    # FREE SLOTS
    # ==========================================

    def free_slots(self):

        return max(
            0,
            self.max_open_positions
            - len(self.positions)
        )

    # ==========================================
    # CURRENT POSITION VALUE
    # ==========================================

    def position_value(
        self,
        symbol,
        price=None,
    ):

        if symbol not in self.positions:
            return 0.0

        pos = self.positions[symbol]

        if price is None:
            price = get_price(symbol)

        if price is None:
            price = pos["entry"]

        return (
            float(price)
            * float(pos["quantity"])
        )

    # ==========================================
    # OPEN PNL
    # ==========================================

    def calculate_open_pnl(self):

        total = 0.0

        for symbol, pos in self.positions.items():

            current_price = get_price(symbol)

            if current_price is None:
                current_price = pos["entry"]

            total += (
                (
                    float(current_price)
                    - float(pos["entry"])
                )
                * float(pos["quantity"])
            )

        return total

    # ==========================================
    # EQUITY
    # ==========================================

    def equity(self):

        position_value = 0.0

        for symbol, pos in self.positions.items():

            current_price = get_price(symbol)

            if current_price is None:
                current_price = pos["entry"]

            position_value += (
                float(current_price)
                * float(pos["quantity"])
            )

        return self.balance + position_value

    # ==========================================
    # POSITION SIZE
    # ==========================================

    def calculate_position_size(
        self,
        entry,
        stop,
    ):

        entry = float(entry)
        stop = float(stop)

        stop_distance = abs(
            entry - stop
        )

        if entry <= 0:
            return 0.0

        if stop_distance <= 0:
            return 0.0

        # ======================================
        # RISK AMOUNT
        # ======================================

        risk_amount = (
            self.equity()
            * self.risk_percent
            / 100.0
        )

        # ======================================
        # QUANTITY FROM STOP DISTANCE
        # ======================================

        quantity = (
            risk_amount
            / stop_distance
        )

        # ======================================
        # NEVER USE MORE CASH THAN AVAILABLE
        # ======================================

# ======================================
# MAX POSITION VALUE
# ======================================

max_position_value = (
    self.equity()
    * self.max_position_pct
)

max_quantity = (
    max_position_value / entry
)

if quantity > max_quantity:
    quantity = max_quantity

# ======================================
# NEVER USE MORE CASH THAN AVAILABLE
# ======================================

cash_quantity = (
    self.balance / entry
)

if quantity > cash_quantity:
    quantity = cash_quantity

if quantity <= 0:
    return 0.0

return round(
    quantity,
    6,
)

        

        # ==========================================
        # OPEN POSITION
        # ==========================================

            def try_open_position(
                self,
                symbol,
                signal,
        ):

        self._reset_daily_loss()

        # ======================================
        # ALREADY OPEN
        # ======================================

        if self.has_position(symbol):

            print(
                f"[FAIL] Already open: "
                f"{symbol}"
            )

            return False

        # ======================================
        # MAX POSITIONS
        # ======================================

        if len(self.positions) >= (
            self.max_open_positions
        ):

            print(
                "[FAIL] Max positions reached"
            )

            return False

        # ======================================
        # DAILY LOSS LIMIT
        # ======================================

        if (
            self.daily_loss
            >= self.max_daily_loss
        ):

            print(
                "[RISK] Daily loss limit "
                f"reached: "
                f"{self.daily_loss:.2f}/"
                f"{self.max_daily_loss:.2f}"
            )

            return False

        # ======================================
        # SIGNAL DATA
        # ======================================

        try:

            entry = float(
                signal["close"]
            )

            atr = float(
                signal["atr"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            print(
                f"[FAIL] Invalid signal: "
                f"{symbol}"
            )

            return False

        if entry <= 0:
            print(
                f"[FAIL] Invalid entry: "
                f"{entry}"
            )

            return False

        if atr <= 0:
            print(
                f"[FAIL] Invalid ATR: "
                f"{atr}"
            )

            return False

        # ======================================
        # STOP / TARGET
        # ======================================

        stop = (
            entry
            - atr * self.stop_atr
        )

        take = (
            entry
            + atr * self.take_atr
        )

        # ======================================
        # POSITION SIZE
        # ======================================

        quantity = (
            self.calculate_position_size(
                entry,
                stop,
            )
        )

        if quantity <= 0:

            print(
                "[FAIL] Quantity = 0"
            )

            return False

        value = (
            quantity * entry
        )

        # ======================================
        # CASH CHECK
        # ======================================

        if value > (
            self.balance + 0.00000001
        ):

            print(
                f"[FAIL] Not enough balance "
                f"value={value:.6f} "
                f"balance={self.balance:.6f}"
            )

            return False

        # ======================================
        # RESERVE CASH
        # ======================================

        self.balance -= value

        # ======================================
        # STORE POSITION
        # ======================================

        self.positions[symbol] = {

            "entry": entry,

            "quantity": quantity,

            "initial_quantity": quantity,

            "value": value,

            "stop": stop,

            "initial_stop": stop,

            "take": take,

            "atr": atr,

            "highest": entry,

            "break_even": False,

            "partial_taken": False,

            "opened": datetime.now(
                timezone.utc
            ),

        }

        self.total_trades += 1

        # ======================================
        # LOG
        # ======================================

        print(
            f"[OPEN] {symbol} "
            f"Entry={entry:.4f} "
            f"Qty={quantity:.6f} "
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

        # ==========================================
        # BREAK EVEN
        # ==========================================

        profit_distance = (
            pos["take"] - pos["entry"]
        )

        if (
            not pos["break_even"]
            and
            price >= pos["entry"] + profit_distance * 0.30
        ):

            pos["stop"] = pos["entry"]

            pos["break_even"] = True

            print(
                f"[BE] {symbol} "
                f"stop={pos['stop']:.4f}"
            )

        # ==========================================
        # TRAILING STOP
        # ==========================================

        trail = (
            pos["highest"] *
            0.985
        )

        if trail > pos["stop"]:

            pos["stop"] = trail

        # ==========================================
        # PARTIAL TAKE PROFIT
        # ==========================================

        if (
            not pos["partial_taken"]
            and
            price >= (
                pos["entry"]
                +
                profit_distance * 0.60
            )
        ):

            qty = pos["quantity"] / 2

            if qty > 0:

                pnl = (
                    price - pos["entry"]
                ) * qty

                self.balance += (
                    qty * price
                )

                self.realized_pnl += pnl

                pos["quantity"] -= qty

                pos["partial_taken"] = True

                print(
                    f"[PARTIAL] {symbol} "
                    f"PnL={pnl:+.2f}"
                )

        # ==========================================
        # STOP LOSS
        # ==========================================

        if price <= pos["stop"]:

            return self.close_position(
                symbol,
                price,
                "STOP",
            )

        # ==========================================
        # TAKE PROFIT
        # ==========================================

        if price >= pos["take"]:

            return self.close_position(
                symbol,
                price,
                "TARGET",
            )

        # ==========================================
        # OPEN P/L
        # ==========================================

        self.open_pnl = 0.0

        for sym, p in self.positions.items():

            try:

                current_price = get_price(sym)

                if current_price is None:
                    continue

                self.open_pnl += (
                    (
                        current_price
                        -
                        p["entry"]
                    )
                    *
                    p["quantity"]
                )

            except Exception:

                continue

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

        quantity = pos["quantity"]

        value = price * quantity

        pnl = (
            price - pos["entry"]
        ) * quantity

        self.balance += value

        self.realized_pnl += pnl

        # ==========================================
        # WIN / LOSS
        # ==========================================

        if pnl > 0:
            self.wins += 1

        elif pnl < 0:
            self.losses += 1

        # ==========================================
        # DAILY LOSS
        # ==========================================

        if pnl < 0:
            self.daily_loss += abs(pnl)

        # ==========================================
        # OPEN P/L
        # ==========================================

        self.open_pnl = 0.0

        for sym, p in self.positions.items():

            try:

                current_price = get_price(sym)

                if current_price is None:
                    continue

                self.open_pnl += (
                    (
                        current_price
                        -
                        p["entry"]
                    )
                    *
                    p["quantity"]
                )

            except Exception:

                continue

        # ==========================================
        # TRADE RECORD
        # ==========================================

        trade = {

            "symbol": symbol,

            "reason": reason,

            "entry": pos["entry"],

            "exit": price,

            "quantity": quantity,

            "pnl": pnl,

        }

        self.closed_trades.append(trade)

        print(
            f"[CLOSE] {symbol} "
            f"reason={reason} "
            f"PnL={pnl:+.2f} "
            f"balance={self.balance:.2f}"
        )

        return trade


    # ==========================================
    # WIN RATE
    # ==========================================

    def win_rate(self):

        closed = (
            self.wins +
            self.losses
        )

        if closed == 0:
            return 0.0

        return round(
            (
                self.wins /
                closed
            ) * 100,
            1,
        )


    # ==========================================
    # PROFIT FACTOR
    # ==========================================

    def profit_factor(self):

        profits = sum(
            trade["pnl"]
            for trade in self.closed_trades
            if trade["pnl"] > 0
        )

        losses = abs(
            sum(
                trade["pnl"]
                for trade in self.closed_trades
                if trade["pnl"] < 0
            )
        )

        if losses == 0:

            if profits > 0:
                return 999.0

            return 0.0

        return round(
            profits / losses,
            2,
        )

    # ==========================================
    # STATS
    # ==========================================

    def stats(self):

        return {

            "balance": round(
                self.balance,
                2,
            ),

            "equity": round(
                self.equity(),
                2,
            ),

            "realized": round(
                self.realized_pnl,
                2,
            ),

            "open_pnl": round(
                self.open_pnl,
                2,
            ),

            "positions": len(
                self.positions
            ),

            "trades": self.total_trades,

            "wins": self.wins,

            "losses": self.losses,

            "win_rate": self.win_rate(),

            "profit_factor": self.profit_factor(),

        }
