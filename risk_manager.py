# ==========================================
# Trading Bot V3
# Risk Manager
# ==========================================

from config import (
    RISK_PER_TRADE,
    MAX_POSITION_PCT,
    MAX_OPEN_POSITIONS,
    DAILY_LOSS_LIMIT,
)


class RiskManager:

    def __init__(self):

        self.daily_loss = 0.0

    # ======================================

    def can_open_position(
        self,
        trader,
    ):

        if len(trader.positions) >= MAX_OPEN_POSITIONS:
            return False

        if self.daily_loss >= DAILY_LOSS_LIMIT:
            return False

        return True

    # ======================================

    def position_size(

        self,

        cash,

        confidence,

    ):

        confidence = max(60, confidence)

        confidence = min(100, confidence)

        risk = RISK_PER_TRADE

        multiplier = confidence / 100

        size = cash * MAX_POSITION_PCT * multiplier

        return max(size, cash * risk)

    # ======================================

    def register_trade(

        self,

        pnl,

    ):

        if pnl < 0:

            self.daily_loss += abs(pnl)

    # ======================================

    def reset_day(self):

        self.daily_loss = 0

    # ======================================

    def trade_quality(

        self,

        confidence,

        rank,

    ):

        if confidence >= 95 and rank >= 95:
            return "A+"

        if confidence >= 90:
            return "A"

        if confidence >= 85:
            return "B"

        if confidence >= 80:
            return "C"

        return "IGNORE"