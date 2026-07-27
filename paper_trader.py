from datetime import datetime, timezone
from config import (
    FEE_RATE, SLIPPAGE_RATE, RISK_PER_TRADE, MAX_POSITION_PCT,
    ATR_STOP_MULT, REWARD_RISK
)
from database import get_cash, open_position, close_position

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def paper_buy(symbol, market_price, atr):
    cash = get_cash()
    entry = market_price * (1 + SLIPPAGE_RATE)
    stop_distance = ATR_STOP_MULT * atr
    if stop_distance <= 0:
        return None

    stop = entry - stop_distance
    target = entry + stop_distance * REWARD_RISK

    # Risk-based size, also capped by available capital allocation.
    risk_budget = cash * RISK_PER_TRADE
    qty_by_risk = risk_budget / stop_distance
    qty_by_cap = (cash * MAX_POSITION_PCT) / (entry * (1 + FEE_RATE))
    qty = min(qty_by_risk, qty_by_cap)
    if qty <= 0:
        return None

    entry_fee = entry * qty * FEE_RATE
    ok = open_position(symbol, entry, qty, stop, target, entry_fee, utcnow())
    if not ok:
        return None
    return entry, qty, stop, target

def paper_sell(symbol, market_price, reason):
    exit_price = market_price * (1 - SLIPPAGE_RATE)
    from database import get_position
    p = get_position(symbol)
    if not p:
        return None
    exit_fee = exit_price * p["qty"] * FEE_RATE
    pnl = close_position(symbol, exit_price, exit_fee, reason, utcnow())
    return exit_price, pnl
