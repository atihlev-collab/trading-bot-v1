from datetime import datetime, timezone

from config import (
    START_BALANCE,
    RISK_PER_TRADE,
    MAX_POSITION_PCT,
    MAX_OPEN_POSITIONS,
    DAILY_LOSS_LIMIT,
    ATR_STOP_MULT,
    REWARD_RISK,
    BREAK_EVEN_AT,
    TRAILING_STOP,
    TRAILING_AT_R,
    TRAILING_ATR,
    FEE_RATE,
    SLIPPAGE_RATE,
)

from market_data import get_price


class PaperTrader:

    # ==========================================
    # INIT
    # ==========================================

    def __init__(self):

        self.start_balance = float(START_BALANCE)

        # Free cash
        self.balance = float(START_BALANCE)

        # Open positions
        self.positions = {}

        # Closed trades
        self.closed_trades = []

        # P/L
        self.realized_pnl = 0.0
        self.open_pnl = 0.0

        # Statistics
        self.total_trades = 0
        self.wins = 0
        self.losses = 0

        # Risk
        self.risk_percent = RISK_PER_TRADE * 100
        self.max_position_pct = MAX_POSITION_PCT
        self.max_open_positions = MAX_OPEN_POSITIONS

        # Daily loss
        self.max_daily_loss = (
            self.start_balance * DAILY_LOSS_LIMIT
        )

        self.daily_loss = 0.0

        self.daily_date = (
            datetime.now(timezone.utc).date()
        )

    # ==========================================
    # DAILY RESET
    # ==========================================

    def _reset_day(self):

        today = datetime.now(timezone.utc).date()

        if today != self.daily_date:

            self.daily_date = today
            self.daily_loss = 0.0

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
            - len(self.positions),
        )

    # ==========================================
    # OPEN POSITION MARKET VALUE
    # ==========================================

    def _position_market_value(self):

        total = 0.0

        for symbol, pos in self.positions.items():

            price = pos.get(
                "last_price",
                pos["entry"],
            )

            quantity = pos["quantity"]

            total += price * quantity

        return total

    # ==========================================
    # EQUITY
    # ==========================================

    def equity(self):

        """
        Total account value:

        Free cash
        +
        current market value of open positions

        This is the important correction.

        The money used to open a position is
        not treated as a loss. It is simply
        moved from cash into the position.
        """

        return (
            self.balance
            + self._position_market_value()
        )

    # ==========================================
    # MARK OPEN P/L
    # ==========================================

    def _mark_open_pnl(self):

        total = 0.0

        for symbol, pos in self.positions.items():

            try:

                px = get_price(symbol)

            except Exception:

                px = pos["last_price"]

            px = float(px)

            pos["last_price"] = px

            entry = pos["entry"]
            quantity = pos["quantity"]

            # Unrealized gross P/L
            gross_pnl = (
                px - entry
            ) * quantity

            # Estimated exit fee
            estimated_exit_fee = (
                px
                * quantity
                * FEE_RATE
            )

            # Entry fee was already paid when
            # position was opened.
            allocated_entry_fee = (
                pos.get("entry_fee", 0.0)
                * (
                    quantity
                    / max(
                        pos["initial_quantity"],
                        1e-12,
                    )
                )
            )

            total += (
                gross_pnl
                - estimated_exit_fee
                - allocated_entry_fee
            )

        self.open_pnl = total

    # ==========================================
    # POSITION SIZE
    # ==========================================

    def calculate_position_size(
        self,
        entry,
        stop,
    ):

        self._reset_day()

        entry = float(entry)
        stop = float(stop)

        stop_distance = abs(
            entry - stop
        )

        if (
            stop_distance <= 0
            or entry <= 0
        ):
            return 0.0

        # ======================================
        # RISK AMOUNT
        # ======================================

        risk_amount = (
            self.equity()
            * RISK_PER_TRADE
        )

        # ======================================
        # QUANTITY FROM STOP DISTANCE
        # ======================================

        quantity = (
            risk_amount
            / stop_distance
        )

        # ======================================
        # MAX POSITION VALUE
        # ======================================

        max_position_value = (
            self.equity()
            * MAX_POSITION_PCT
        )

        max_quantity = (
            max_position_value
            / entry
        )

        if quantity > max_quantity:

            quantity = max_quantity

        # ======================================
        # NEVER USE MORE CASH THAN AVAILABLE
        # ======================================

        cash_quantity = (
            self.balance
            / (
                entry
                * (1 + FEE_RATE)
            )
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

        self._reset_day()

        # ======================================
        # DAILY LOSS LIMIT
        # ======================================

        if (
            self.daily_loss
            >= self.max_daily_loss
        ):

            print(
                "[FAIL] Daily loss limit reached"
            )

            return False

        # ======================================
        # EXISTING POSITION
        # ======================================

        if self.has_position(symbol):

            return False

        # ======================================
        # MAX POSITIONS
        # ======================================

        if self.free_slots() <= 0:

            return False

        # ======================================
        # SIGNAL DATA
        # ======================================

        entry_raw = float(
            signal["close"]
        )

        atr_value = float(
            signal["atr"]
        )

        if (
            entry_raw <= 0
            or atr_value <= 0
        ):

            return False

        # ======================================
        # ENTRY WITH SLIPPAGE
        # ======================================

        entry = (
            entry_raw
            * (1 + SLIPPAGE_RATE)
        )

        # ======================================
        # STOP
        # ======================================

        stop = (
            entry
            - atr_value
            * ATR_STOP_MULT
        )

        risk_per_unit = (
            entry - stop
        )

        if risk_per_unit <= 0:

            return False

        # ======================================
        # TAKE PROFIT
        # ======================================

        take = (
            entry
            + risk_per_unit
            * REWARD_RISK
        )

        # ======================================
        # POSITION SIZE
        # ======================================

        quantity = self.calculate_position_size(
            entry,
            stop,
        )

        if quantity <= 0:

            return False

        # ======================================
        # POSITION VALUE
        # ======================================

        value = (
            quantity
            * entry
        )

        # ======================================
        # ENTRY FEE
        # ======================================

        entry_fee = (
            value
            * FEE_RATE
        )

        total_cost = (
            value
            + entry_fee
        )

        # ======================================
        # FINAL CASH CHECK
        # ======================================

        if total_cost > self.balance:

            quantity = (
                self.balance
                / (
                    entry
                    * (1 + FEE_RATE)
                )
            )

            quantity = round(
                quantity,
                6,
            )

            value = (
                quantity
                * entry
            )

            entry_fee = (
                value
                * FEE_RATE
            )

            total_cost = (
                value
                + entry_fee
            )

        if (
            quantity <= 0
            or total_cost > self.balance
        ):

            return False

        # ======================================
        # REMOVE CASH
        # ======================================

        self.balance -= total_cost

        # ======================================
        # SAVE POSITION
        # ======================================

        self.positions[symbol] = {

            "entry": entry,

            "quantity": quantity,

            "initial_quantity": quantity,

            "value": value,

            "stop": stop,

            "take": take,

            "initial_risk": (
                risk_per_unit
                * quantity
            ),

            "highest": entry,

            "last_price": entry,

            "break_even": False,

            "partial_taken": False,

            "entry_fee": entry_fee,

            "opened": (
                datetime.now(timezone.utc)
            ),

            "score": signal.get(
                "score",
                0,
            ),

            "confidence": signal.get(
                "confidence",
                0,
            ),

            "quality": signal.get(
                "quality",
                "",
            ),
        }

        # ======================================
        # LOG
        # ======================================

        print(
            f"[OPEN] {symbol} "
            f"Entry={entry:.6f} "
            f"Qty={quantity:.6f} "
            f"SL={stop:.6f} "
            f"TP={take:.6f} "
            f"Risk={risk_per_unit * quantity:.4f}"
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

        price = float(price)

        pos["last_price"] = price

        # ======================================
        # HIGHEST PRICE
        # ======================================

        if price > pos["highest"]:

            pos["highest"] = price

        # ======================================
        # RISK PER UNIT
        # ======================================

        risk_unit = (
            pos["initial_risk"]
            / max(
                pos["initial_quantity"],
                1e-12,
            )
        )

        # ======================================
        # BREAK EVEN
        # ======================================

        if (
            not pos["break_even"]
            and price
            >= (
                pos["entry"]
                + risk_unit
                * BREAK_EVEN_AT
            )
        ):

            pos["stop"] = max(
                pos["stop"],
                pos["entry"]
                * (1 + FEE_RATE),
            )

            pos["break_even"] = True

            print(
                f"[BE] {symbol}"
            )

        # ======================================
        # TRAILING STOP
        # ======================================

        if (
            TRAILING_STOP
            and price
            >= (
                pos["entry"]
                + risk_unit
                * TRAILING_AT_R
            )
        ):

            trail = (
                pos["highest"]
                - risk_unit
                * TRAILING_ATR
            )

            if trail > pos["stop"]:

                pos["stop"] = trail

        # ======================================
        # PARTIAL TAKE PROFIT
        # ======================================

        if (
            not pos["partial_taken"]
            and price
            >= (
                pos["entry"]
                + risk_unit * 2.0
            )
        ):

            qty = (
                pos["quantity"]
                / 2
            )

            value = (
                qty * price
            )

            exit_fee = (
                value * FEE_RATE
            )

            # Allocate the original entry fee
            # to the quantity being closed.
            entry_fee_part = (
                pos["entry_fee"]
                * (
                    qty
                    / max(
                        pos["initial_quantity"],
                        1e-12,
                    )
                )
            )

            pnl = (
                (price - pos["entry"])
                * qty
                - exit_fee
                - entry_fee_part
            )

            self.balance += (
                value
                - exit_fee
            )

            self.realized_pnl += pnl

            pos["entry_fee"] = max(
                0.0,
                pos["entry_fee"]
                - entry_fee_part,
            )

            pos["quantity"] -= qty

            pos["partial_taken"] = True

            print(
                f"[PARTIAL] {symbol} "
                f"PnL={pnl:+.4f}"
            )

        # ======================================
        # STOP
        # ======================================

        if price <= pos["stop"]:

            return self.close_position(
                symbol,
                price,
                "STOP",
            )

        # ======================================
        # TARGET
        # ======================================

        if price >= pos["take"]:

            return self.close_position(
                symbol,
                price,
                "TARGET",
            )

        # ======================================
        # UPDATE OPEN P/L
        # ======================================

        self._mark_open_pnl()

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

        price = float(price)

        # ======================================
        # EXIT SLIPPAGE
        # ======================================

        exit_price = (
            price
            * (1 - SLIPPAGE_RATE)
        )

        quantity = pos["quantity"]

        # ======================================
        # EXIT VALUE
        # ======================================

        value = (
            exit_price
            * quantity
        )

        # ======================================
        # EXIT FEE
        # ======================================

        exit_fee = (
            value
            * FEE_RATE
        )

        # ======================================
        # ENTRY FEE ALLOCATION
        # ======================================

        entry_fee = pos.get(
            "entry_fee",
            0.0,
        )

        # ======================================
        # REALIZED P/L
        # ======================================

        gross_pnl = (
            exit_price
            - pos["entry"]
        ) * quantity

        pnl = (
            gross_pnl
            - exit_fee
            - entry_fee
        )

        # ======================================
        # RETURN CASH
        # ======================================

        self.balance += (
            value
            - exit_fee
        )

        self.realized_pnl += pnl

        # ======================================
        # STATISTICS
        # ======================================

        self.total_trades += 1

        if pnl >= 0:

            self.wins += 1

        else:

            self.losses += 1

            self.daily_loss += abs(pnl)

        # ======================================
        # OPEN P/L RESET
        # ======================================

        self._mark_open_pnl()

        # ======================================
        # TRADE RESULT
        # ======================================

        trade = {

            "symbol": symbol,

            "reason": reason,

            "entry": pos["entry"],

            "exit": exit_price,

            "quantity": quantity,

            "pnl": pnl,

            "quality": pos.get(
                "quality",
                "",
            ),

            "confidence": pos.get(
                "confidence",
                0,
            ),

            "score": pos.get(
                "score",
                0,
            ),
        }

        self.closed_trades.append(
            trade
        )

        print(
            f"[CLOSE] {symbol} "
            f"{reason} "
            f"PnL={pnl:+.4f}"
        )

        return trade

    # ==========================================
    # WIN RATE
    # ==========================================

    def win_rate(self):

        closed = (
            self.wins
            + self.losses
        )

        if closed <= 0:

            return 0.0

        return round(
            self.wins
            / closed
            * 100,
            1,
        )

    # ==========================================
    # PROFIT FACTOR
    # ==========================================

    def profit_factor(self):

        profits = sum(
            t["pnl"]
            for t in self.closed_trades
            if t["pnl"] > 0
        )

        losses = abs(
            sum(
                t["pnl"]
                for t in self.closed_trades
                if t["pnl"] < 0
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

        self._mark_open_pnl()

        current_equity = self.equity()

        return {

            "balance": round(
                self.balance,
                2,
            ),

            "equity": round(
                current_equity,
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
