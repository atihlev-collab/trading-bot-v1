"""
Historical backtest for the V4 strategy.

Usage:
    python backtest.py

It downloads recent 15m and 1h Binance candles and simulates the
same core entry/exit rules without placing real orders.
"""

import time
import requests
import pandas as pd
import numpy as np

from config import (
    SYMBOLS, CANDLE_LIMIT, EMA_FAST, EMA_SLOW, EMA_TREND,
    RSI_PERIOD, RSI_MIN, RSI_MAX, ATR_PERIOD, MIN_ATR_PERCENT,
    MAX_ATR_PERCENT, VOLUME_PERIOD, VOLUME_MULTIPLIER,
    MIN_MOMENTUM, MIN_TREND_STRENGTH, MAX_GREEN_CANDLE,
    ATR_STOP_MULT, REWARD_RISK, FEE_RATE, SLIPPAGE_RATE,
    RISK_PER_TRADE, MAX_POSITION_PCT
)
from indicators import ema, rsi, atr, momentum, volume_ma, trend_strength, macd, adx

BASE_URL = "https://data-api.binance.vision"

def get_history(symbol, interval, limit=1000):
    r = requests.get(
        f"{BASE_URL}/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": min(limit, 1000)},
        timeout=20
    )
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_volume","trades","taker_buy_base",
        "taker_buy_quote","ignore"
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ["open","high","low","close","volume"]:
        df[c] = df[c].astype(float)
    return df.iloc[:-1].reset_index(drop=True)

def prepare(df):
    df = df.copy()
    df["ema20"] = ema(df.close, EMA_FAST)
    df["ema50"] = ema(df.close, EMA_SLOW)
    df["ema200"] = ema(df.close, EMA_TREND)
    df["rsi"] = rsi(df.close, RSI_PERIOD)
    df["atr"] = atr(df, ATR_PERIOD)
    df["mom"] = momentum(df.close, 5)
    df["vol_ma"] = volume_ma(df.volume, VOLUME_PERIOD)
    df["trend"] = trend_strength(df.ema20, df.ema50)
    _, _, df["macd_hist"] = macd(df.close)
    df["adx"] = adx(df, 14)
    return df

def run_symbol(symbol, capital=100.0):
    low = prepare(get_history(symbol, "15m", 1000))
    high = prepare(get_history(symbol, "1h", 1000))

    high_view = high[["open_time","close","ema20","ema50","ema200"]].copy()
    high_view.columns = ["htf_time","htf_close","htf_ema20","htf_ema50","htf_ema200"]
    low = pd.merge_asof(
        low.sort_values("open_time"),
        high_view.sort_values("htf_time"),
        left_on="open_time",
        right_on="htf_time",
        direction="backward"
    )

    balance = capital
    position = None
    trades = []

    for i in range(220, len(low)):
        row = low.iloc[i]
        price = row.close

        if position:
            position["highest"] = max(position["highest"], price)
            risk_unit = position["initial_risk"] / position["initial_qty"]

            if not position["be"] and price >= position["entry"] + risk_unit:
                position["stop"] = position["entry"]
                position["be"] = True

            if price <= position["stop"] or price >= position["take"]:
                exit_price = price * (1 - SLIPPAGE_RATE)
                qty = position["qty"]
                pnl = (exit_price - position["entry"]) * qty
                pnl -= exit_price * qty * FEE_RATE
                balance += exit_price * qty - exit_price * qty * FEE_RATE
                balance += 0
                trades.append(pnl)
                position = None
                continue

        if position:
            continue

        if balance <= 0:
            break

        atr_v = row.atr
        if not np.isfinite(atr_v) or price <= 0:
            continue

        atr_pct = atr_v / price
        vol_ratio = row.volume / row.vol_ma if row.vol_ma > 0 else 0
        candle_body = abs(row.close-row.open) / row.open

        conditions = [
            row.htf_close > row.htf_ema200,
            row.htf_ema20 > row.htf_ema50,
            price > row.ema200,
            row.ema20 > row.ema50,
            RSI_MIN <= row.rsi <= RSI_MAX,
            MIN_ATR_PERCENT <= atr_pct <= MAX_ATR_PERCENT,
            row.mom >= MIN_MOMENTUM,
            row.trend >= MIN_TREND_STRENGTH,
            vol_ratio >= VOLUME_MULTIPLIER,
            candle_body <= MAX_GREEN_CANDLE,
            row.macd_hist > 0,
            row.adx >= 18,
        ]
        if not all(conditions):
            continue

        entry = price * (1 + SLIPPAGE_RATE)
        stop = entry - atr_v * ATR_STOP_MULT
        risk_unit = entry - stop
        take = entry + risk_unit * REWARD_RISK

        risk_amount = balance * RISK_PER_TRADE
        qty = risk_amount / risk_unit
        qty = min(qty, balance * MAX_POSITION_PCT / entry)
        qty = min(qty, balance / (entry * (1 + FEE_RATE)))

        if qty <= 0:
            continue

        cost = qty * entry
        fee = cost * FEE_RATE
        balance -= cost + fee

        position = {
            "entry": entry,
            "qty": qty,
            "initial_qty": qty,
            "initial_risk": risk_unit * qty,
            "stop": stop,
            "take": take,
            "highest": entry,
            "be": False,
        }

    if position:
        exit_price = low.iloc[-1].close * (1 - SLIPPAGE_RATE)
        qty = position["qty"]
        pnl = (exit_price-position["entry"])*qty - exit_price*qty*FEE_RATE
        balance += exit_price*qty - exit_price*qty*FEE_RATE
        trades.append(pnl)

    wins = sum(x > 0 for x in trades)
    losses = sum(x < 0 for x in trades)
    gross_profit = sum(x for x in trades if x > 0)
    gross_loss = abs(sum(x for x in trades if x < 0))
    pf = gross_profit / gross_loss if gross_loss else (999 if gross_profit else 0)

    return {
        "symbol": symbol,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": wins/len(trades)*100 if trades else 0,
        "profit_factor": pf,
        "pnl": balance-capital,
        "end_balance": balance,
    }

def main():
    results = []
    print("V4 HISTORICAL BACKTEST")
    print("="*65)
    for symbol in SYMBOLS:
        try:
            result = run_symbol(symbol)
            results.append(result)
            print(
                f"{symbol:10} trades={result['trades']:3d} "
                f"WR={result['win_rate']:5.1f}% "
                f"PF={result['profit_factor']:5.2f} "
                f"PnL={result['pnl']:+7.2f}"
            )
        except Exception as exc:
            print(f"{symbol:10} ERROR {exc}")
        time.sleep(0.15)

    if not results:
        return

    df = pd.DataFrame(results)
    total_trades = int(df.trades.sum())
    total_wins = int(df.wins.sum())
    total_pnl = float(df.pnl.sum())
    weighted_wr = total_wins / total_trades * 100 if total_trades else 0

    print("="*65)
    print(f"TOTAL SYMBOLS : {len(df)}")
    print(f"TOTAL TRADES  : {total_trades}")
    print(f"WIN RATE      : {weighted_wr:.1f}%")
    print(f"TOTAL PNL     : {total_pnl:+.2f} USDT")
    print(f"AVG PF        : {df.profit_factor.replace([np.inf], np.nan).mean():.2f}")
    print("="*65)

if __name__ == "__main__":
    main()
