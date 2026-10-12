from datetime import date, datetime, timezone

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
from database import init_db, load_account_state, save_account_state


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

        # Restore the account snapshot. If a saved snapshot is corrupt or from
        # an unknown version, fail loudly rather than silently resetting cash.
        init_db()
        state = load_account_state()
        if state is not None:
            required = {
                "balance", "positions", "closed_trades", "realized_pnl",
                "open_pnl", "total_trades", "wins", "losses",
                "daily_loss", "daily_date",
            }
            missing = required.difference(state)
            if missing:
                raise RuntimeError(
                    "Stored account state is incomplete; refusing to reset: "
                    + ", ".join(sorted(missing))
                )

            if not isinstance(state["positions"], dict) or not isinstance(state["closed_trades"], list):
                raise RuntimeError("Stored account state has invalid collections; refusing to reset")

            self.start_balance = float(state.get("start_balance", START_BALANCE))
            self.balance = float(state["balance"])
            self.positions = state["positions"]
            for symbol, pos in self.positions.items():
                if not isinstance(pos, dict):
                    raise RuntimeError(f"Stored position {symbol} is invalid")
                opened = pos.get("opened")
                if isinstance(opened, str):
                    try:
                        pos["opened"] = datetime.fromisoformat(opened)
                    except ValueError as exc:
                        raise RuntimeError(f"Stored position {symbol} has an invalid open time") from exc

            self.closed_trades = state["closed_trades"]
            self.realized_pnl = float(state["realized_pnl"])
            self.open_pnl = float(state["open_pnl"])
            self.total_trades = int(state["total_trades"])
            self.wins = int(state["wins"])
            self.losses = int(state["losses"])
            self.daily_loss = float(state["daily_loss"])
            try:
                self.daily_date = date.fromisoformat(str(state["daily_date"]))
            except ValueError as exc:
                raise RuntimeError("Stored account state has an invalid daily date") from exc

        self.max_daily_loss = self.start_balance * DAILY_LOSS_LIMIT
        self._reset_day()
        self._persist_state()

    def _persist_state(self):
        """Persist balance, positions and statistics after each state change."""
        serialized_positions = {}
        for symbol, pos in self.positions.items():
            serialized = {}
            for key, value in pos.items():
                if isinstance(value, datetime):
                    serialized[key] = value.isoformat()
                elif isinstance(value, (str, int, float, bool)) or value is None:
                    serialized[key] = value
                elif hasattr(value, "item"):
                    serialized[key] = value.item()
                else:
                    raise TypeError(
                        f"Cannot persist position field {symbol}.{key}: "
                        f"{type(value).__name__}"
                    )
            serialized_positions[symbol] = serialized

        save_account_state({
            "version": 1,
            "start_balance": self.start_balance,
            "balance": self.balance,
            "positions": serialized_positions,
            "closed_trades": self.closed_trades,
            "realized_pnl": self.realized_pnl,
            "open_pnl": self.open_pnl,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "daily_loss": self.daily_loss,
            "daily_date": self.daily_date.isoformat(),
        })

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
            # entry_fee is reduced when a partial exit occurs, so it
            # already represents the fee allocated to the remaining size.
            allocated_entry_fee = pos.get("entry_fee", 0.0)

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

        # Daily loss limit is loss-only.
        # Profitable trades must never trigger this guard.
        if (
            self.daily_loss > 0
            and self.daily_loss >= self.max_daily_loss
        ):

            print(
                "[FAIL] Daily loss limit reached "
                f"({self.daily_loss:.2f}/"
                f"{self.max_daily_loss:.2f} USDT)"
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

        # The candle close is a historical signal reference, not a live
        # fill price. Fetch a fresh quote; skip rather than enter at a stale
        # close if the quote endpoint is unavailable.
        try:
            entry_raw = float(get_price(symbol))
        except Exception as exc:
            print(f"[SKIP OPEN] {symbol}: current price unavailable: {exc}")
            return False

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

            "atr": atr_value,

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

            "partial_realized_pnl": 0.0,

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

        # Persist the open before reporting success. If storage fails, revert
        # the in-memory position and cash rather than pretending it is durable.
        try:
            self._persist_state()
        except Exception as exc:
            self.positions.pop(symbol, None)
            self.balance += total_cost
            print(f"[FAIL OPEN] {symbol}: account state could not be saved: {exc}")
            return False

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

            # Use the ATR captured at entry. The paper trader polls quotes
            # rather than candle ATR, so this keeps the trail deterministic.
            trail = (
                pos["highest"]
                - float(pos.get("atr", risk_unit / max(ATR_STOP_MULT, 1e-12)))
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

            partial_exit_price = price * (1 - SLIPPAGE_RATE)

            value = (
                qty * partial_exit_price
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
                (partial_exit_price - pos["entry"])
                * qty
                - exit_fee
                - entry_fee_part
            )

            self.balance += (
                value
                - exit_fee
            )

            self.realized_pnl += pnl
            pos["partial_realized_pnl"] = (
                pos.get("partial_realized_pnl", 0.0) + pnl
            )

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
        self._persist_state()

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

        # Count the full position as one trade, including any realized
        # partial exit; otherwise win rate and profit factor omit that P/L.
        trade_pnl = pnl + float(pos.get("partial_realized_pnl", 0.0))

        self.total_trades += 1

        if trade_pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1
            self.daily_loss += abs(trade_pnl)

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

            "pnl": trade_pnl,
            "remaining_pnl": pnl,

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
        self._persist_state()

        print(
            f"[CLOSE] {symbol} "
            f"{reason} "
            f"PnL={trade_pnl:+.4f}"
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
        self._persist_state()

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
