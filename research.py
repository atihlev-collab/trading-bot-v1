"""
Predefined exit-logic comparison with a chronological train/holdout split.

This is deliberately not an optimizer: it compares a small, documented set
of plausible exit-management variants while keeping scanner entries unchanged.
Every symbol is tested with separate starting capital, so pooled P/L is not a
single portfolio return.
"""

import time

import numpy as np
import pandas as pd

import backtest as bt


TRAIN_FRACTION = 0.70

# These variants are declared before viewing their holdout results.
VARIANTS = [
    {
        "name": "baseline",
        "ATR_STOP_MULT": 1.8,
        "REWARD_RISK": 2.5,
        "BREAK_EVEN_AT": 1.0,
        "TRAILING_STOP": True,
        "TRAILING_AT_R": 1.5,
        "TRAILING_ATR": 1.5,
    },
    {
        "name": "no_trailing",
        "ATR_STOP_MULT": 1.8,
        "REWARD_RISK": 2.5,
        "BREAK_EVEN_AT": 1.0,
        "TRAILING_STOP": False,
        "TRAILING_AT_R": 1.5,
        "TRAILING_ATR": 1.5,
    },
    {
        "name": "no_break_even_no_trailing",
        "ATR_STOP_MULT": 1.8,
        "REWARD_RISK": 2.5,
        "BREAK_EVEN_AT": 999.0,
        "TRAILING_STOP": False,
        "TRAILING_AT_R": 1.5,
        "TRAILING_ATR": 1.5,
    },
    {
        "name": "target_1_5R",
        "ATR_STOP_MULT": 1.8,
        "REWARD_RISK": 1.5,
        "BREAK_EVEN_AT": 1.0,
        "TRAILING_STOP": False,
        "TRAILING_AT_R": 1.5,
        "TRAILING_ATR": 1.5,
    },
    {
        "name": "target_2R",
        "ATR_STOP_MULT": 1.8,
        "REWARD_RISK": 2.0,
        "BREAK_EVEN_AT": 1.0,
        "TRAILING_STOP": False,
        "TRAILING_AT_R": 1.5,
        "TRAILING_ATR": 1.5,
    },
    {
        "name": "wider_stop_2_2ATR",
        "ATR_STOP_MULT": 2.2,
        "REWARD_RISK": 2.5,
        "BREAK_EVEN_AT": 1.0,
        "TRAILING_STOP": False,
        "TRAILING_AT_R": 1.5,
        "TRAILING_ATR": 1.5,
    },
    {
        "name": "tighter_stop_1_5ATR",
        "ATR_STOP_MULT": 1.5,
        "REWARD_RISK": 2.5,
        "BREAK_EVEN_AT": 1.0,
        "TRAILING_STOP": False,
        "TRAILING_AT_R": 1.5,
        "TRAILING_ATR": 1.5,
    },
]


def summarize(name, period, results):
    if not results:
        print(f"[VARIANT] period={period} name={name} NO_RESULTS", flush=True)
        return

    trades = sum(int(row["trades"]) for row in results)
    wins = sum(int(row["wins"]) for row in results)
    losses = sum(int(row["losses"]) for row in results)
    pnl = sum(float(row["pnl"]) for row in results)
    gross_profit = sum(float(row.get("gross_profit", 0.0)) for row in results)
    gross_loss = sum(float(row.get("gross_loss", 0.0)) for row in results)
    pooled_pf = gross_profit / gross_loss if gross_loss > 0 else (
        999.0 if gross_profit > 0 else 0.0
    )
    expectancy = pnl / trades if trades else 0.0
    win_rate = wins / trades * 100 if trades else 0.0
    avg_dd = float(np.mean([row["max_drawdown"] for row in results]))
    worst_dd = float(max(row["max_drawdown"] for row in results))
    profitable_symbols = sum(float(row["pnl"]) > 0 for row in results)

    print(
        f"[VARIANT] period={period:7} name={name:27} "
        f"symbols={len(results):2d} trades={trades:5d} "
        f"WR={win_rate:6.2f}% PF={pooled_pf:5.2f} "
        f"PnL_sum={pnl:+9.2f} Exp={expectancy:+.4f} "
        f"avgDD={avg_dd:5.2f}% worstDD={worst_dd:5.2f}% "
        f"profitable_symbols={profitable_symbols}/{len(results)}",
        flush=True,
    )


def main():
    original_get_history = bt.get_history
    original_valid_entry = bt.valid_entry
    exit_keys = (
        "ATR_STOP_MULT",
        "REWARD_RISK",
        "BREAK_EVEN_AT",
        "TRAILING_STOP",
        "TRAILING_AT_R",
        "TRAILING_ATR",
    )
    original_exit_values = {key: getattr(bt, key) for key in exit_keys}
    history = {}
    cutoffs = {}

    low_ms = bt.INTERVAL_MS.get(bt.LOWER_TIMEFRAME)
    high_ms = bt.INTERVAL_MS.get(bt.HIGHER_TIMEFRAME)
    if not low_ms or not high_ms or high_ms < low_ms:
        raise ValueError("Research requires a valid lower/higher timeframe pair")

    high_limit = int(np.ceil(bt.BACKTEST_LIMIT * low_ms / high_ms)) + bt.EMA_TREND

    print("=" * 110, flush=True)
    print("EXIT-MANAGEMENT RESEARCH — FIXED ENTRY RULES, CHRONOLOGICAL 70/30 SPLIT", flush=True)
    print(
        f"symbols={len(bt.SYMBOLS)} lower={bt.LOWER_TIMEFRAME} "
        f"higher={bt.HIGHER_TIMEFRAME} low_candles={bt.BACKTEST_LIMIT} "
        f"fees={bt.FEE_RATE:.4f} slippage={bt.SLIPPAGE_RATE:.4f}",
        flush=True,
    )
    print("Each symbol uses its own starting balance; summed P/L is not a portfolio return.", flush=True)
    print("=" * 110, flush=True)

    # Fetch each symbol's raw history once. Every variant then reuses exactly
    # the same candles, avoiding differences caused by a new download.
    for index, symbol in enumerate(bt.SYMBOLS, 1):
        try:
            low = original_get_history(symbol, bt.LOWER_TIMEFRAME, bt.BACKTEST_LIMIT)
            high = original_get_history(symbol, bt.HIGHER_TIMEFRAME, high_limit)
            if len(low) < 250 or len(high) < 250:
                raise RuntimeError(f"insufficient candles: low={len(low)} high={len(high)}")
            cutoff_idx = max(220, min(len(low) - 2, int(len(low) * TRAIN_FRACTION)))
            cutoffs[symbol] = low.iloc[cutoff_idx]["close_time"]
            history[symbol] = {
                bt.LOWER_TIMEFRAME: low,
                bt.HIGHER_TIMEFRAME: high,
                "cutoff_idx": cutoff_idx,
            }
            print(
                f"[DATA] {index}/{len(bt.SYMBOLS)} {symbol} "
                f"low={len(low)} high={len(high)} "
                f"holdout_from={cutoffs[symbol]}",
                flush=True,
            )
        except Exception as exc:
            print(f"[DATA ERROR] {symbol}: {exc}", flush=True)
        time.sleep(0.15)

    if not history:
        raise RuntimeError("No symbol histories were loaded")

    mode = {"period": "train", "symbol": None}

    def cached_get_history(symbol, interval, limit=None):
        if symbol not in history or interval not in history[symbol]:
            raise RuntimeError(f"No cached history for {symbol} {interval}")
        df = history[symbol][interval]

        if mode["period"] == "train":
            cutoff_idx = int(history[symbol]["cutoff_idx"])
            cutoff_time = cutoffs[symbol]
            if interval == bt.LOWER_TIMEFRAME:
                return df.iloc[:cutoff_idx + 1].copy().reset_index(drop=True)
            return (
                df[df["close_time"] <= cutoff_time]
                .copy()
                .reset_index(drop=True)
            )

        return df.copy().reset_index(drop=True)

    def holdout_valid_entry(row):
        symbol = mode["symbol"]
        if symbol is None or row["close_time"] < cutoffs[symbol]:
            return False
        return original_valid_entry(row)

    bt.get_history = cached_get_history
    try:
        for variant in VARIANTS:
            for key in exit_keys:
                setattr(bt, key, variant[key])

            for period in ("train", "holdout"):
                mode["period"] = period
                bt.valid_entry = original_valid_entry if period == "train" else holdout_valid_entry
                results = []

                for symbol in history:
                    mode["symbol"] = symbol
                    try:
                        results.append(
                            bt.run_symbol(symbol, capital=bt.START_BALANCE)
                        )
                    except Exception as exc:
                        print(
                            f"[SIM ERROR] period={period} variant={variant['name']} "
                            f"symbol={symbol}: {exc}",
                            flush=True,
                        )

                summarize(variant["name"], period, results)

    finally:
        bt.get_history = original_get_history
        bt.valid_entry = original_valid_entry
        for key, value in original_exit_values.items():
            setattr(bt, key, value)

    print("=" * 110, flush=True)
    print("RESEARCH DONE — HOLDOUT RESULTS ARE THE PRIMARY COMPARISON; NO LIVE SETTINGS WERE CHANGED.", flush=True)
    print("=" * 110, flush=True)


if __name__ == "__main__":
    main()
