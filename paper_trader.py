from config import (
    START_BALANCE,
    RISK_PER_TRADE,
    MAX_POSITION_PCT,
    MAX_OPEN_POSITIONS,
    DAILY_LOSS_LIMIT,
)

from datetime import datetime, timezone

from market_data import get_price


# ==========================================
# PAPER TRADER
# ==========================================

class PaperTrader:

    def __init__(self):

        # ==========================================
        # ACCOUNT
        # ==========================================

        self.start_balance = float(
            START_BALANCE
        )

        self.balance = self.start_balance

        self.positions = {}

        self.closed_trades = []


        # ==========================================
        # P/L
        # ==========================================

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

        self.risk_percent = (
            RISK_PER_TRADE * 100
        )

        self.max_position_pct = (
            MAX_POSITION_PCT
        )

        self.max_open_positions = (
            MAX_OPEN_POSITIONS
        )

        # Maximum realized loss allowed per day

        self.max_daily_loss = (
            self.start_balance
            * DAILY_LOSS_LIMIT
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
            f"[TRADER] MAX POSITION % = "
            f"{self.max_position_pct * 100:.1f}%"
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

            print(
                "[RISK] Daily loss reset"
            )


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

            try:

                current_price = get_price(
                    symbol
                )

                if current_price is None:

                    current_price = pos["entry"]

                total += (
                    (
                        float(current_price)
                        - float(pos["entry"])
                    )
                    * float(pos["quantity"])
                )

            except Exception:

                continue

        return total


    # ==========================================
    # EQUITY
    # ==========================================

    def equity(self):

        position_value = 0.0

        for symbol, pos in self.positions.items():

            try:

                current_price = get_price(
                    symbol
                )

                if current_price is None:

                    current_price = pos["entry"]

                position_value += (
                    float(current_price)
                    * float(pos["quantity"])
                )

            except Exception:

                continue

        return (
            self.balance
            + position_value
        )

    # ==========================================
    # POSITION SIZE
    # ==========================================

    def calculate_position_size(
        self,
        entry,
        stop,
    ):

        # ------------------------------------------
        # SAFETY
        # ------------------------------------------

        entry = float(entry)
        stop = float(stop)

        if entry <= 0:
            return 0.0

        if stop <= 0:
            return 0.0


        # ==========================================
        # STOP DISTANCE
        # ==========================================

        stop_distance = abs(
            entry - stop
        )

        if stop_distance <= 0:
            return 0.0


        # ==========================================
        # RISK AMOUNT
        # ==========================================

        risk_amount = (
            self.equity()
            * RISK_PER_TRADE
        )

        if risk_amount <= 0:
            return 0.0


        # ==========================================
        # QUANTITY FROM STOP DISTANCE
        # ==========================================

        quantity = (
            risk_amount
            / stop_distance
        )


        # ==========================================
        # MAX POSITION VALUE
        # ==========================================

        max_position_value = (
            self.equity()
            * self.max_position_pct
        )

        max_quantity = (
            max_position_value
            / entry
        )

        if quantity > max_quantity:

            quantity = max_quantity


        # ==========================================
        # NEVER USE MORE CASH THAN AVAILABLE
        # ==========================================

        cash_quantity = (
            self.balance
            / entry
        )

        if quantity > cash_quantity:

            quantity = cash_quantity


        # ==========================================
        # FINAL SAFETY
        # ==========================================

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
        trade_signal,
    ):

        # ==========================================
        # BASIC CHECKS
        # ==========================================

        if not symbol:

            return False

        if self.has_position(symbol):

            return False

        if self.free_slots() <= 0:

            print(
                "[FAIL] No free position slots"
            )

            return False


        # ==========================================
        # DAILY RISK RESET
        # ==========================================

        self._reset_daily_loss()


        # ==========================================
        # DAILY LOSS LIMIT
        # ==========================================

        if self.daily_loss >= self.max_daily_loss:

            print(
                "[FAIL] Daily loss limit reached"
            )

            return False


        # ==========================================
        # SIGNAL DATA
        # ==========================================

        try:

            entry = float(
                trade_signal["entry"]
            )

        except Exception:

            try:

                entry = float(
                    get_price(symbol)
                )

            except Exception:

                print(
                    f"[FAIL] No entry price {symbol}"
                )

                return False


        # ==========================================
        # STOP
        # ==========================================

        try:

            stop = float(
                trade_signal["stop"]
            )

        except Exception:

            stop = 0.0


        # ==========================================
        # ATR FALLBACK
        # ==========================================

        if stop <= 0:

            atr_value = float(
                trade_signal.get(
                    "atr",
                    0,
                )
            )

            if atr_value <= 0:

                print(
                    f"[FAIL] No valid stop {symbol}"
                )

                return False

            stop = (
                entry
                - (
                    atr_value
                    * self.stop_atr
                )
            )


        # ==========================================
        # VALID LONG STOP
        # ==========================================

        if stop >= entry:

            print(
                f"[FAIL] Invalid LONG stop "
                f"{symbol} "
                f"entry={entry:.8f} "
                f"stop={stop:.8f}"
            )

            return False


        # ==========================================
        # STOP DISTANCE
        # ==========================================

        stop_distance = (
            entry - stop
        )

        if stop_distance <= 0:

            print(
                f"[FAIL] Invalid stop distance "
                f"{symbol}"
            )

            return False


        # ==========================================
        # RISK PER TRADE
        # ==========================================

        risk_amount = (
            self.equity()
            * RISK_PER_TRADE
        )

        if risk_amount <= 0:

            print(
                f"[FAIL] Risk amount = 0"
            )

            return False


        # ==========================================
        # QUANTITY
        # ==========================================

        quantity = (
            self.calculate_position_size(
                entry,
                stop,
            )
        )

        if quantity <= 0:

            print(
                f"[FAIL] Quantity = 0"
            )

            return False


        # ==========================================
        # POSITION VALUE
        # ==========================================

        position_value = (
            entry
            * quantity
        )


        # ==========================================
        # FINAL CASH CHECK
        # ==========================================

        if position_value > self.balance:

            quantity = (
                self.balance
                / entry
            )

            quantity = round(
                quantity,
                6,
            )

            position_value = (
                entry
                * quantity
            )


        if quantity <= 0:

            print(
                f"[FAIL] Not enough balance "
                f"{symbol}"
            )

            return False


        # ==========================================
        # TAKE PROFIT
        # ==========================================

        take = trade_signal.get(
            "take"
        )

        if take is not None:

            try:

                take = float(take)

            except Exception:

                take = 0.0

        else:

            take = 0.0


        # ==========================================
        # ATR TP FALLBACK
        # ==========================================

        if take <= entry:

            risk_distance = (
                entry
                - stop
            )

            take = (
                entry
                + (
                    risk_distance
                    * 3.0
                )
            )


        # ==========================================
        # RISK / REWARD
        # ==========================================

        reward = (
            take
            - entry
        )

        rr = (
            reward
            / stop_distance
            if stop_distance > 0
            else 0.0
        )


        # ==========================================
        # STORE POSITION
        # ==========================================

        self.positions[symbol] = {

            "symbol": symbol,

            "side": "LONG",

            "entry": entry,

            "quantity": quantity,

            "original_quantity": quantity,

            "stop": stop,

            "initial_stop": stop,

            "take": take,

            "risk_distance": stop_distance,

            "risk_amount": risk_amount,

            "position_value": position_value,

            "rr": rr,

            "partial_taken": False,

            "break_even": False,

            "trailing": False,

            "score": trade_signal.get(
                "score",
                0,
            ),

            "confidence": trade_signal.get(
                "confidence",
                0,
            ),

            "quality": trade_signal.get(
                "quality",
                "",
            ),

            "opened_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }


        # ==========================================
        # RESERVE CASH
        # ==========================================

        self.balance -= position_value


        # ==========================================
        # LOG
        # ==========================================

        print(
            f"[OPEN] {symbol} "
            f"Entry={entry:.8f} "
            f"Qty={quantity:.6f} "
            f"SL={stop:.8f} "
            f"TP={take:.8f}"
        )

        print(
            f"[OPEN] {symbol} "
            f"Risk={risk_amount:.4f} "
            f"RR={rr:.2f}"
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

        try:

            price = float(price)

        except Exception:

            return None

        if price <= 0:

            return None


        pos = self.positions[symbol]


        # ==========================================
        # UPDATE HIGHEST PRICE
        # ==========================================

        if price > pos["entry"]:

            if (
                "highest"
                not in pos
            ):

                pos["highest"] = price

            elif price > pos["highest"]:

                pos["highest"] = price

        else:

            if (
                "highest"
                not in pos
            ):

                pos["highest"] = pos["entry"]


        # ==========================================
        # ORIGINAL RISK
        # ==========================================

        risk_distance = float(
            pos.get(
                "risk_distance",
                abs(
                    pos["entry"]
                    - pos["initial_stop"]
                ),
            )
        )

        if risk_distance <= 0:

            risk_distance = abs(
                pos["entry"]
                - pos["initial_stop"]
            )

        if risk_distance <= 0:

            risk_distance = pos["entry"] * 0.01


        # ==========================================
        # PROFIT IN R
        # ==========================================

        profit_distance = (
            price
            - pos["entry"]
        )

        current_r = (
            profit_distance
            / risk_distance
        )


        # ==========================================
        # BREAK EVEN
        # ==========================================

        if (
            not pos["break_even"]
            and
            current_r >= self.break_even_r
        ):

            pos["stop"] = pos["entry"]

            pos["break_even"] = True

            print(
                f"[BE] {symbol} "
                f"Price={price:.8f}"
            )


        # ==========================================
        # PARTIAL TAKE PROFIT
        # ==========================================

        if (
            not pos["partial_taken"]
            and
            current_r >= self.partial_r
            and
            pos["quantity"] > 0
        ):

            partial_quantity = (
                pos["quantity"]
                * 0.50
            )

            if partial_quantity > 0:

                partial_value = (
                    partial_quantity
                    * price
                )

                partial_pnl = (
                    (
                        price
                        - pos["entry"]
                    )
                    * partial_quantity
                )

                self.balance += (
                    partial_value
                )

                self.realized_pnl += (
                    partial_pnl
                )

                pos["quantity"] -= (
                    partial_quantity
                )

                pos["partial_taken"] = True

                print(
                    f"[PARTIAL] {symbol} "
                    f"Qty={partial_quantity:.6f} "
                    f"PnL={partial_pnl:+.4f}"
                )


        # ==========================================
        # TRAILING STOP
        # ==========================================

        if pos.get(
            "highest",
            pos["entry"],
        ) > pos["entry"]:

            trailing_stop = (
                pos["highest"]
                - (
                    risk_distance
                    * 1.5
                )
            )

            if trailing_stop > pos["stop"]:

                pos["stop"] = (
                    trailing_stop
                )

                pos["trailing"] = True


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

        for sym, position in (
            self.positions.items()
        ):

            try:

                current_price = get_price(
                    sym
                )

                if current_price is None:

                    current_price = (
                        position["entry"]
                    )

                self.open_pnl += (
                    (
                        float(current_price)
                        - float(
                            position["entry"]
                        )
                    )
                    * float(
                        position["quantity"]
                    )
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

        try:

            price = float(price)

        except Exception:

            return None

        if price <= 0:

            return None


        # ==========================================
        # REMOVE POSITION
        # ==========================================

        pos = self.positions.pop(
            symbol
        )


        # ==========================================
        # FINAL VALUE
        # ==========================================

        value = (
            price
            * pos["quantity"]
        )


        # ==========================================
        # PNL
        # ==========================================

        pnl = (
            price
            - pos["entry"]
        ) * pos["quantity"]


        # ==========================================
        # RETURN CASH
        # ==========================================

        self.balance += value


        # ==========================================
        # REALIZED PNL
        # ==========================================

        self.realized_pnl += pnl


        # ==========================================
        # WIN / LOSS
        # ==========================================

        if pnl >= 0:

            self.wins += 1

        else:

            self.losses += 1

            self.daily_loss += abs(
                pnl
            )


        # ==========================================
        # OPEN PNL RESET
        # ==========================================

        self.open_pnl = 0.0


        # ==========================================
        # RECALCULATE OPEN PNL
        # ==========================================

        for sym, position in (
            self.positions.items()
        ):

            try:

                current_price = get_price(
                    sym
                )

                if current_price is None:

                    current_price = (
                        position["entry"]
                    )

                self.open_pnl += (
                    (
                        float(current_price)
                        - float(
                            position["entry"]
                        )
                    )
                    * float(
                        position["quantity"]
                    )
                )

            except Exception:

                continue


        # ==========================================
        # TRADE RESULT
        # ==========================================

        trade = {

            "symbol": symbol,

            "side": "LONG",

            "reason": reason,

            "entry": pos["entry"],

            "exit": price,

            "quantity": pos["quantity"],

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


        # ==========================================
        # SAVE IN MEMORY
        # ==========================================

        self.closed_trades.append(
            trade
        )


        # ==========================================
        # LOG RESULT
        # ==========================================

        if pnl >= 0:

            print(
                f"[CLOSE WIN] {symbol} "
                f"Reason={reason} "
                f"PnL={pnl:+.4f}"
            )

        else:

            print(
                f"[CLOSE LOSS] {symbol} "
                f"Reason={reason} "
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
            (
                self.wins
                / closed
            )
            * 100,
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

        if losses <= 0:

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

        self._reset_daily_loss()

        # ==========================================
        # UPDATE OPEN PNL
        # ==========================================

        self.open_pnl = self.calculate_open_pnl()

        # ==========================================
        # EQUITY
        # ==========================================

        current_equity = self.equity()

        # ==========================================
        # RETURN
        # ==========================================

        if self.start_balance > 0:

            return_percent = (
                (
                    current_equity
                    - self.start_balance
                )
                / self.start_balance
            ) * 100

        else:

            return_percent = 0.0

        # ==========================================
        # STATS
        # ==========================================

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

            "return": round(
                return_percent,
                2,
            ),

            "positions": len(
                self.positions
            ),

            "free_slots": self.free_slots(),

            "trades": self.total_trades,

            "wins": self.wins,

            "losses": self.losses,

            "win_rate": self.win_rate(),

            "profit_factor": self.profit_factor(),

            "daily_loss": round(
                self.daily_loss,
                2,
            ),

            "max_daily_loss": round(
                self.max_daily_loss,
                2,
            ),

            "risk_percent": round(
                self.risk_percent,
                2,
            ),

            "max_position_pct": round(
                self.max_position_pct,
                4,
            ),

        }
