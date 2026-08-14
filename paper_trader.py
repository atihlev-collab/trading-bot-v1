from datetime import datetime, timezone
from config import (
    START_BALANCE, RISK_PER_TRADE, MAX_POSITION_PCT,
    MAX_OPEN_POSITIONS, DAILY_LOSS_LIMIT, ATR_STOP_MULT,
    REWARD_RISK, BREAK_EVEN_AT, TRAILING_STOP,
    TRAILING_AT_R, TRAILING_ATR, FEE_RATE, SLIPPAGE_RATE
)
from market_data import get_price

class PaperTrader:
    def __init__(self):
        self.start_balance = float(START_BALANCE)
        self.balance = float(START_BALANCE)
        self.positions = {}
        self.closed_trades = []
        self.realized_pnl = 0.0
        self.open_pnl = 0.0
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.risk_percent = RISK_PER_TRADE * 100
        self.max_position_pct = MAX_POSITION_PCT
        self.max_open_positions = MAX_OPEN_POSITIONS
        self.max_daily_loss = self.start_balance * DAILY_LOSS_LIMIT
        self.daily_loss = 0.0
        self.daily_date = datetime.now(timezone.utc).date()

    def _reset_day(self):
        today = datetime.now(timezone.utc).date()
        if today != self.daily_date:
            self.daily_date = today
            self.daily_loss = 0.0

    def has_position(self, symbol):
        return symbol in self.positions

    def free_slots(self):
        return max(0, self.max_open_positions - len(self.positions))

    def equity(self):
        return self.balance + self.open_pnl

    def _mark_open_pnl(self):
        total = 0.0
        for sym, pos in self.positions.items():
            try:
                px = get_price(sym)
            except Exception:
                px = pos["last_price"]
            pos["last_price"] = px
            total += (px - pos["entry"]) * pos["quantity"]
        self.open_pnl = total

    def calculate_position_size(self, entry, stop):
        self._reset_day()
        stop_distance = abs(entry - stop)
        if stop_distance <= 0 or entry <= 0:
            return 0.0

        risk_amount = self.equity() * RISK_PER_TRADE
        quantity = risk_amount / stop_distance

        max_value = self.equity() * MAX_POSITION_PCT
        quantity = min(quantity, max_value / entry)

        cash_quantity = self.balance / entry
        quantity = min(quantity, cash_quantity)

        return round(max(quantity, 0.0), 6)

    def try_open_position(self, symbol, signal):
        self._reset_day()

        if self.daily_loss >= self.max_daily_loss:
            print("[FAIL] Daily loss limit reached")
            return False
        if self.has_position(symbol):
            return False
        if self.free_slots() <= 0:
            return False

        entry_raw = float(signal["close"])
        atr_value = float(signal["atr"])
        if entry_raw <= 0 or atr_value <= 0:
            return False

        entry = entry_raw * (1 + SLIPPAGE_RATE)
        stop = entry - atr_value * ATR_STOP_MULT
        risk_per_unit = entry - stop
        take = entry + risk_per_unit * REWARD_RISK

        quantity = self.calculate_position_size(entry, stop)
        if quantity <= 0:
            return False

        value = quantity * entry
        entry_fee = value * FEE_RATE
        total_cost = value + entry_fee

        if total_cost > self.balance:
            quantity = self.balance / (entry * (1 + FEE_RATE))
            value = quantity * entry
            entry_fee = value * FEE_RATE
            total_cost = value + entry_fee

        if quantity <= 0 or total_cost > self.balance:
            return False

        self.balance -= total_cost
        self.positions[symbol] = {
            "entry": entry,
            "quantity": quantity,
            "initial_quantity": quantity,
            "value": value,
            "stop": stop,
            "take": take,
            "initial_risk": risk_per_unit * quantity,
            "highest": entry,
            "last_price": entry,
            "break_even": False,
            "partial_taken": False,
            "opened": datetime.now(timezone.utc),
            "score": signal.get("score", 0),
            "confidence": signal.get("confidence", 0),
            "quality": signal.get("quality", ""),
        }

        print(
            f"[OPEN] {symbol} Entry={entry:.6f} Qty={quantity:.6f} "
            f"SL={stop:.6f} TP={take:.6f} Risk={risk_per_unit*quantity:.4f}"
        )
        return True

    def update_position(self, symbol, price):
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        price = float(price)
        pos["last_price"] = price

        if price > pos["highest"]:
            pos["highest"] = price

        risk_unit = pos["initial_risk"] / pos["initial_quantity"]

        # Break even after +1R.
        if not pos["break_even"] and price >= pos["entry"] + risk_unit * BREAK_EVEN_AT:
            pos["stop"] = max(pos["stop"], pos["entry"] * (1 + FEE_RATE))
            pos["break_even"] = True
            print(f"[BE] {symbol}")

        # Trail only after +1.5R, avoiding premature exits.
        if TRAILING_STOP and price >= pos["entry"] + risk_unit * TRAILING_AT_R:
            trail = pos["highest"] - (pos["initial_risk"] / pos["initial_quantity"]) * TRAILING_ATR
            if trail > pos["stop"]:
                pos["stop"] = trail

        # Partial at +2R, not before the main trend has developed.
        if not pos["partial_taken"] and price >= pos["entry"] + risk_unit * 2.0:
            qty = pos["quantity"] / 2
            value = qty * price
            fee = value * FEE_RATE
            pnl = (price - pos["entry"]) * qty - fee
            self.balance += value - fee
            self.realized_pnl += pnl
            pos["quantity"] -= qty
            pos["partial_taken"] = True
            print(f"[PARTIAL] {symbol} PnL={pnl:+.4f}")

        if price <= pos["stop"]:
            return self.close_position(symbol, price, "STOP")

        if price >= pos["take"]:
            return self.close_position(symbol, price, "TARGET")

        self._mark_open_pnl()
        return None

    def close_position(self, symbol, price, reason):
        if symbol not in self.positions:
            return None

        pos = self.positions.pop(symbol)
        exit_price = float(price) * (1 - SLIPPAGE_RATE)
        value = exit_price * pos["quantity"]
        fee = value * FEE_RATE
        pnl = (exit_price - pos["entry"]) * pos["quantity"] - fee

        self.balance += value - fee
        self.realized_pnl += pnl
        self.total_trades += 1

        if pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1
            self.daily_loss += abs(pnl)

        self._mark_open_pnl()

        trade = {
            "symbol": symbol,
            "reason": reason,
            "entry": pos["entry"],
            "exit": exit_price,
            "quantity": pos["quantity"],
            "pnl": pnl,
            "quality": pos.get("quality", ""),
            "confidence": pos.get("confidence", 0),
            "score": pos.get("score", 0),
        }
        self.closed_trades.append(trade)
        print(f"[CLOSE] {symbol} {reason} PnL={pnl:+.4f}")
        return trade

    def win_rate(self):
        closed = self.wins + self.losses
        return round(self.wins / closed * 100, 1) if closed else 0.0

    def profit_factor(self):
        profits = sum(t["pnl"] for t in self.closed_trades if t["pnl"] > 0)
        losses = abs(sum(t["pnl"] for t in self.closed_trades if t["pnl"] < 0))
        if losses == 0:
            return 999.0 if profits > 0 else 0.0
        return round(profits / losses, 2)

    def stats(self):
        self._mark_open_pnl()
        return {
            "balance": round(self.balance, 2),
            "equity": round(self.equity(), 2),
            "realized": round(self.realized_pnl, 2),
            "open_pnl": round(self.open_pnl, 2),
            "positions": len(self.positions),
            "trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate(),
            "profit_factor": self.profit_factor(),
        }
