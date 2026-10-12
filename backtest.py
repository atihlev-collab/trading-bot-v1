"""
Historical backtest for Trading Bot V5/V6 strategy.

IMPORTANT:
This backtest is designed to follow the current scanner/trader configuration
as closely as possible.

It uses:
    15m = entry timeframe
    1h  = higher timeframe trend

Features:
    - EMA trend
    - RSI
    - ATR volatility filter
    - Momentum
    - Volume
    - Trend strength
    - MACD
    - ADX
    - Break-even
    - ATR trailing stop
    - Fees on entry and exit
    - Slippage
    - Conservative same-candle SL/TP handling
    - Maximum drawdown
"""

import time
import requests
import pandas as pd
import numpy as np

from config import (
    START_BALANCE,
    SYMBOLS,

    LOWER_TIMEFRAME,
    HIGHER_TIMEFRAME,

    EMA_FAST,
    EMA_SLOW,
    EMA_TREND,

    RSI_PERIOD,
    RSI_MIN,
    RSI_MAX,
    RSI_HARD_MAX,

    ATR_PERIOD,
    MIN_ATR_PERCENT,
    MAX_ATR_PERCENT,

    VOLUME_PERIOD,
    VOLUME_MULTIPLIER,
    STRONG_VOLUME_RATIO,

    MIN_MOMENTUM,
    STRONG_MOMENTUM,
    MIN_TREND_STRENGTH,
    STRONG_TREND_STRENGTH,
    MAX_GREEN_CANDLE,
    MAX_ENTRY_CANDLE,

    BUY_SCORE,
    MIN_BUY_CONFIRMATIONS,

    ATR_STOP_MULT,
    REWARD_RISK,

    BREAK_EVEN_AT,
    TRAILING_STOP,
    TRAILING_AT_R,
    TRAILING_ATR,

    FEE_RATE,
    SLIPPAGE_RATE,

    RISK_PER_TRADE,
    MAX_POSITION_PCT,
    BACKTEST_LIMIT,
    BACKTEST_MIN_TRADES,
    REQUIRE_POSITIVE_EXPECTANCY,
    MAX_BACKTEST_DRAWDOWN,
)

from indicators import (
    ema,
    rsi,
    atr,
    momentum,
    volume_ma,
    trend_strength,
    macd,
    adx,
)


BASE_URL = "https://data-api.binance.vision"


# =========================================================
# DATA
# =========================================================

INTERVAL_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def get_history(symbol, interval, limit=None):
    """Fetch a recent historical window in pages; Binance caps klines at 1000/page."""
    limit = max(250, int(limit or BACKTEST_LIMIT))
    interval_ms = INTERVAL_MS.get(interval)
    if interval_ms is None:
        raise ValueError(f"Unsupported interval: {interval}")

    now_ms = int(time.time() * 1000)
    start_ms = now_ms - limit * interval_ms
    all_rows = []

    while len(all_rows) < limit:
        page_limit = min(1000, limit - len(all_rows))
        response = requests.get(
            f"{BASE_URL}/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "limit": page_limit,
                "startTime": start_ms,
                "endTime": now_ms,
            },
            timeout=20,
        )
        response.raise_for_status()
        page = response.json()
        if not page:
            break

        all_rows.extend(page)
        next_start = int(page[-1][0]) + interval_ms
        if next_start <= start_ms or len(page) < page_limit or next_start >= now_ms:
            break
        start_ms = next_start
        time.sleep(0.12)

    if not all_rows:
        raise RuntimeError(f"No historical data for {symbol} {interval}")

    df = pd.DataFrame(
        all_rows,
        columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ],
    )
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)

    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Remove duplicate page boundaries and candles that had not closed at
    # the time this history window was requested.
    now = pd.Timestamp.now(tz="UTC")
    df = (
        df.drop_duplicates(subset=["open_time"])
        .sort_values("open_time")
        .dropna(subset=["open", "high", "low", "close", "volume"])
    )
    df = df[df["close_time"] < now].reset_index(drop=True)

    if len(df) < 250:
        raise RuntimeError(
            f"Insufficient closed candles for {symbol} {interval}: {len(df)}"
        )
    return df


# =========================================================
# INDICATORS
# =========================================================

def prepare(df):
    df = df.copy()

    df["ema20"] = ema(df["close"], EMA_FAST)
    df["ema50"] = ema(df["close"], EMA_SLOW)
    df["ema200"] = ema(df["close"], EMA_TREND)
    df["rsi"] = rsi(df["close"], RSI_PERIOD)
    df["atr"] = atr(df, ATR_PERIOD)
    df["atr_pct"] = df["atr"] / df["close"].replace(0, np.nan)
    df["mom"] = momentum(df["close"], 5)
    df["vol_ma"] = volume_ma(df["volume"], VOLUME_PERIOD)
    df["volume_ratio"] = df["volume"] / df["vol_ma"].replace(0, np.nan)
    df["trend"] = trend_strength(df["ema20"], df["ema50"])
    _, _, df["macd_hist"] = macd(df["close"])
    df["macd_hist_prev"] = df["macd_hist"].shift(1)
    df["adx"] = adx(df, 14)
    df["candle_body"] = (
        (df["close"] - df["open"]) / df["open"].replace(0, np.nan)
    )
    return df


# =========================================================
# HTF MERGE
# =========================================================

def add_higher_timeframe(low, high):
    # Use the higher-timeframe close timestamp, not its open timestamp.
    # A 1h candle's final OHLC/indicators are unavailable until it closes.
    high_view = high[
        ["close_time", "close", "ema20", "ema50", "ema200"]
    ].copy()
    high_view.columns = [
        "htf_time", "htf_close", "htf_ema20", "htf_ema50", "htf_ema200"
    ]

    low = pd.merge_asof(
        low.sort_values("close_time"),
        high_view.sort_values("htf_time"),
        left_on="close_time",
        right_on="htf_time",
        direction="backward",
    )
    return low.reset_index(drop=True)


# =========================================================
# ENTRY CONDITIONS
# =========================================================

def valid_entry(row):
    """Reproduce the scanner's BUY rules on a historical closed candle."""
    required = [
        row.get("htf_close"), row.get("htf_ema20"), row.get("htf_ema50"),
        row.get("htf_ema200"), row.get("ema20"), row.get("ema50"),
        row.get("ema200"), row.get("rsi"), row.get("atr"), row.get("atr_pct"),
        row.get("mom"), row.get("vol_ma"), row.get("volume_ratio"),
        row.get("trend"), row.get("macd_hist"), row.get("adx"),
        row.get("candle_body"),
    ]
    if not all(pd.notna(value) and np.isfinite(float(value)) for value in required):
        return False

    price = float(row["close"])
    rsi_now = float(row["rsi"])
    atr_pct = float(row["atr_pct"])
    mom_now = float(row["mom"])
    trend_now = float(row["trend"])
    adx_now = float(row["adx"])
    hist_now = float(row["macd_hist"])
    hist_prev = float(row.get("macd_hist_prev", 0.0) or 0.0)
    volume_ratio = float(row["volume_ratio"])
    candle_body = float(row["candle_body"])

    if price <= 0 or not (MIN_ATR_PERCENT <= atr_pct <= MAX_ATR_PERCENT):
        return False
    if rsi_now > RSI_HARD_MAX or mom_now < 0:
        return False
    if candle_body > MAX_ENTRY_CANDLE:
        return False

    htf_bull = (
        float(row["htf_close"]) > float(row["htf_ema200"])
        and float(row["htf_ema20"]) > float(row["htf_ema50"])
    )
    ltf_bull = (
        price > float(row["ema200"])
        and float(row["ema20"]) > float(row["ema50"])
    )
    if not htf_bull or not ltf_bull:
        return False

    conditions = {
        "HTF": htf_bull,
        "LTF": ltf_bull,
        "RSI": RSI_MIN <= rsi_now <= RSI_MAX,
        "MOM": mom_now >= MIN_MOMENTUM,
        "TREND": trend_now >= MIN_TREND_STRENGTH,
        "VOLUME": volume_ratio >= VOLUME_MULTIPLIER,
        "MACD": hist_now > 0,
        "ADX": adx_now >= 20,
        "CANDLE": 0 < candle_body <= MAX_GREEN_CANDLE,
    }
    confirmations = sum(bool(value) for value in conditions.values())

    score = 0
    if htf_bull:
        score += 18
    if ltf_bull:
        score += 18
    if RSI_MIN <= rsi_now <= RSI_MAX:
        score += 10
        if 55 <= rsi_now <= 63:
            score += 3
    elif rsi_now < RSI_MIN:
        score += 3
    if mom_now >= STRONG_MOMENTUM:
        score += 12
    elif mom_now >= MIN_MOMENTUM:
        score += 8
    if trend_now >= STRONG_TREND_STRENGTH:
        score += 10
    elif trend_now >= MIN_TREND_STRENGTH:
        score += 6
    if adx_now >= 25:
        score += 10
    elif adx_now >= 20:
        score += 6
    if hist_now > 0:
        score += 8
        if hist_now > abs(hist_prev):
            score += 2
    if volume_ratio >= STRONG_VOLUME_RATIO:
        score += 10
    elif volume_ratio >= VOLUME_MULTIPLIER:
        score += 6
    if 0 < candle_body <= MAX_GREEN_CANDLE:
        score += 5

    score = min(score, 100)
    return (
        score >= int(BUY_SCORE)
        and confirmations >= int(MIN_BUY_CONFIRMATIONS)
        and mom_now >= MIN_MOMENTUM
        and 0 < candle_body <= min(MAX_GREEN_CANDLE, MAX_ENTRY_CANDLE)
    )


# =========================================================
# POSITION HELPERS
# =========================================================

def calculate_position_size(
    balance,
    entry,
    stop,
):
    risk_amount = (
        balance
        * RISK_PER_TRADE
    )

    stop_distance = abs(
        entry - stop
    )

    if stop_distance <= 0:
        return 0.0

    quantity = (
        risk_amount
        / stop_distance
    )

    # Maximum position value.
    max_value = (
        balance
        * MAX_POSITION_PCT
    )

    max_quantity = (
        max_value
        / entry
    )

    quantity = min(
        quantity,
        max_quantity,
    )

    # Never spend more than available cash
    # including entry fee.
    max_affordable_quantity = (
        balance
        / (
            entry
            * (1 + FEE_RATE)
        )
    )

    quantity = min(
        quantity,
        max_affordable_quantity,
    )

    return max(
        float(quantity),
        0.0,
    )


# =========================================================
# EXIT PRICE
# =========================================================

def close_position(balance, position, exit_price):
    """Close the remaining quantity, including conservative exit slippage."""
    quantity = float(position["quantity"])
    exit_price = float(exit_price) * (1 - SLIPPAGE_RATE)
    gross_value = exit_price * quantity
    exit_fee = gross_value * FEE_RATE
    proceeds = gross_value - exit_fee
    remaining_entry_fee = (
        float(position["entry"]) * quantity * FEE_RATE
    )
    pnl = (
        (exit_price - float(position["entry"])) * quantity
        - remaining_entry_fee
        - exit_fee
    )
    balance += proceeds
    return balance, pnl, exit_price


# =========================================================
# BACKTEST ONE SYMBOL
# =========================================================

def run_symbol(
    symbol,
    capital=100.0,
):
    low_raw = get_history(
        symbol,
        LOWER_TIMEFRAME,
        BACKTEST_LIMIT,
    )

    low_ms = INTERVAL_MS.get(LOWER_TIMEFRAME)
    high_ms = INTERVAL_MS.get(HIGHER_TIMEFRAME)
    if not low_ms or not high_ms or high_ms < low_ms:
        raise ValueError("Backtest expects a valid higher timeframe")
    # Match the test window and include 200 extra closed HTF candles for EMA warm-up.
    high_limit = int(np.ceil(BACKTEST_LIMIT * low_ms / high_ms)) + EMA_TREND
    high_raw = get_history(
        symbol,
        HIGHER_TIMEFRAME,
        high_limit,
    )

    low = prepare(low_raw)
    high = prepare(high_raw)

    low = add_higher_timeframe(
        low,
        high,
    )

    if len(low) < 250:
        raise RuntimeError(
            f"Not enough candles for {symbol}"
        )

    balance = float(capital)

    position = None

    trades = []

    equity_curve = []

    peak = balance
    max_drawdown = 0.0

    # Need enough history for EMA200 etc.
    start_index = 220

    # Signals are calculated on a fully closed candle and executed at
    # the next candle's open. This avoids filling at a close that is only
    # known after the signal candle has finished.
    for i in range(start_index + 1, len(low)):
        signal_row = low.iloc[i - 1]
        bar = low.iloc[i]

        bar_open = float(bar["open"])
        bar_high = float(bar["high"])
        bar_low = float(bar["low"])
        bar_close = float(bar["close"])

        # No stacking: this model backtests one position per symbol.
        if position is None and balance > 0 and valid_entry(signal_row):
            signal_atr = float(signal_row["atr"])
            if np.isfinite(signal_atr) and signal_atr > 0 and bar_open > 0:
                entry = bar_open * (1 + SLIPPAGE_RATE)
                stop = entry - signal_atr * ATR_STOP_MULT
                initial_risk = entry - stop
                take = entry + initial_risk * REWARD_RISK
                quantity = calculate_position_size(balance, entry, stop)
                entry_value = quantity * entry
                entry_fee = entry_value * FEE_RATE

                if quantity > 0 and entry_value + entry_fee <= balance:
                    balance -= entry_value + entry_fee
                    position = {
                        "symbol": symbol,
                        "entry": entry,
                        "quantity": quantity,
                        "initial_quantity": quantity,
                        "stop": stop,
                        "take": take,
                        "initial_risk_per_unit": initial_risk,
                        "atr": signal_atr,
                        "highest": entry,
                        "break_even": False,
                        "partial_taken": False,
                        "partial_pnl": 0.0,
                        "entry_fee_remaining": entry_fee,
                        "opened_index": i,
                    }

        # Manage using the stop that was already active before this candle.
        # Any newly activated break-even/trailing stop becomes active on the
        # next candle, avoiding intrabar look-ahead.
        if position is not None:
            stop = float(position["stop"])
            take = float(position["take"])
            exit_reason = None
            exit_price = None

            if bar_open <= stop:
                exit_reason = "STOP_GAP"
                exit_price = bar_open
            elif bar_open >= take:
                exit_reason = "TAKE_GAP"
                exit_price = take
            else:
                stop_hit = bar_low <= stop
                take_hit = bar_high >= take
                # When both prices occur in one OHLC bar, assume the stop
                # was hit first. This is deliberately conservative.
                if stop_hit:
                    exit_reason = "STOP"
                    exit_price = stop
                elif take_hit:
                    exit_reason = "TAKE"
                    exit_price = take

            if exit_reason is not None:
                balance, remaining_pnl, actual_exit = close_position(
                    balance, position, exit_price
                )
                total_trade_pnl = (
                    float(position.get("partial_pnl", 0.0))
                    + remaining_pnl
                )
                trades.append({
                    "symbol": symbol,
                    "entry": position["entry"],
                    "exit": actual_exit,
                    "quantity": position["initial_quantity"],
                    "pnl": total_trade_pnl,
                    "reason": exit_reason,
                    "opened_at": str(low.iloc[position["opened_index"]]["close_time"]),
                    "closed_at": str(bar["close_time"]),
                })
                position = None
                # No second entry on the same candle after an exit.
                equity_curve.append(balance)
                peak = max(peak, balance)
                max_drawdown = max(
                    max_drawdown,
                    ((peak - balance) / peak * 100) if peak > 0 else 0.0,
                )
                continue

            # Conservative partial profit at +2R, half the remaining size.
            # Same-candle stop events were checked first above.
            partial_level = (
                float(position["entry"])
                + float(position["initial_risk_per_unit"]) * 2.0
            )
            if (
                not position["partial_taken"]
                and bar_high >= partial_level
                and float(position["quantity"]) > 0
            ):
                old_qty = float(position["quantity"])
                qty = old_qty / 2.0
                partial_exit = partial_level * (1 - SLIPPAGE_RATE)
                proceeds = qty * partial_exit
                exit_fee = proceeds * FEE_RATE
                entry_fee_part = (
                    float(position["entry_fee_remaining"])
                    * qty / old_qty
                )
                partial_pnl = (
                    (partial_exit - float(position["entry"])) * qty
                    - exit_fee
                    - entry_fee_part
                )
                balance += proceeds - exit_fee
                position["partial_pnl"] += partial_pnl
                position["entry_fee_remaining"] = max(
                    0.0,
                    float(position["entry_fee_remaining"]) - entry_fee_part,
                )
                position["quantity"] = old_qty - qty
                position["partial_taken"] = True

            # The profit target can close the remaining position after a
            # partial exit. This is after stop priority for the same bar.
            if bar_high >= take:
                balance, remaining_pnl, actual_exit = close_position(
                    balance, position, take
                )
                total_trade_pnl = (
                    float(position.get("partial_pnl", 0.0))
                    + remaining_pnl
                )
                trades.append({
                    "symbol": symbol,
                    "entry": position["entry"],
                    "exit": actual_exit,
                    "quantity": position["initial_quantity"],
                    "pnl": total_trade_pnl,
                    "reason": "TAKE",
                    "opened_at": str(low.iloc[position["opened_index"]]["close_time"]),
                    "closed_at": str(bar["close_time"]),
                })
                position = None
                equity_curve.append(balance)
                peak = max(peak, balance)
                max_drawdown = max(
                    max_drawdown,
                    ((peak - balance) / peak * 100) if peak > 0 else 0.0,
                )
                continue

            # Update stop levels only after checking the currently active
            # stop/target for this candle.
            position["highest"] = max(
                float(position["highest"]),
                bar_high,
            )
            entry = float(position["entry"])
            initial_risk = float(position["initial_risk_per_unit"])

            if (
                not position["break_even"]
                and bar_high >= entry + initial_risk * BREAK_EVEN_AT
            ):
                position["stop"] = max(
                    float(position["stop"]),
                    entry * (1 + FEE_RATE),
                )
                position["break_even"] = True

            if (
                TRAILING_STOP
                and bar_high >= entry + initial_risk * TRAILING_AT_R
            ):
                trailing_stop = (
                    float(position["highest"])
                    - float(position["atr"]) * TRAILING_ATR
                )
                if trailing_stop > float(position["stop"]):
                    position["stop"] = trailing_stop

            estimated_exit_value = (
                float(position["quantity"])
                * bar_close
                * (1 - FEE_RATE - SLIPPAGE_RATE)
            )
            equity = balance + estimated_exit_value
        else:
            equity = balance

        equity_curve.append(equity)
        peak = max(peak, equity)
        drawdown = ((peak - equity) / peak * 100) if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    # =====================================================
    # FORCE CLOSE LAST POSITION
    # =====================================================

    if position is not None:

        last_close = float(low.iloc[-1]["close"])
        balance, remaining_pnl, actual_exit = close_position(
            balance, position, last_close
        )
        total_trade_pnl = (
            float(position.get("partial_pnl", 0.0)) + remaining_pnl
        )
        trades.append({
            "symbol": symbol,
            "entry": position["entry"],
            "exit": actual_exit,
            "quantity": position["initial_quantity"],
            "pnl": total_trade_pnl,
            "reason": "END",
            "opened_at": str(low.iloc[position["opened_index"]]["close_time"]),
            "closed_at": str(low.iloc[-1]["close_time"]),
        })

        position = None

    # =====================================================
    # STATISTICS
    # =====================================================

    pnls = [
        float(t["pnl"])
        for t in trades
    ]

    wins = [
        x for x in pnls
        if x > 0
    ]

    losses = [
        x for x in pnls
        if x < 0
    ]

    total_trades = len(pnls)

    win_count = len(wins)
    loss_count = len(losses)

    gross_profit = sum(wins)

    gross_loss = abs(
        sum(losses)
    )

    profit_factor = (
        gross_profit
        / gross_loss
        if gross_loss > 0
        else (
            999.0
            if gross_profit > 0
            else 0.0
        )
    )

    total_pnl = (
        balance
        - capital
    )

    win_rate = (
        win_count
        / total_trades
        * 100
        if total_trades
        else 0
    )

    avg_win = (
        np.mean(wins)
        if wins
        else 0
    )

    avg_loss = (
        np.mean(losses)
        if losses
        else 0
    )

    expectancy = (
        np.mean(pnls)
        if pnls
        else 0
    )

    return {
        "symbol": symbol,
        "trades": total_trades,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "wins": win_count,
        "losses": loss_count,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "pnl": total_pnl,
        "end_balance": balance,
        "max_drawdown": max_drawdown,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
    }


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 95)
    print("TRADING BOT HISTORICAL BACKTEST")
    print("=" * 95)

    print(
        f"Timeframes : "
        f"{LOWER_TIMEFRAME} / {HIGHER_TIMEFRAME}"
    )

    print(
        f"Risk/trade : "
        f"{RISK_PER_TRADE * 100:.2f}%"
    )

    print(
        f"SL         : "
        f"{ATR_STOP_MULT:.2f} ATR"
    )

    print(
        f"TP         : "
        f"{REWARD_RISK:.2f} R"
    )

    print(
        f"Fees       : "
        f"{FEE_RATE * 100:.3f}%"
    )

    print(
        f"Slippage   : "
        f"{SLIPPAGE_RATE * 100:.3f}%"
    )

    print("=" * 95)

    results = []

    for symbol in SYMBOLS:

        try:

            result = run_symbol(
                symbol,
                capital=100.0,
            )

            results.append(result)

            print(
                f"{symbol:10} "
                f"TR={result['trades']:4d} "
                f"WR={result['win_rate']:5.1f}% "
                f"PF={result['profit_factor']:6.2f} "
                f"PnL={result['pnl']:+8.2f} "
                f"DD={result['max_drawdown']:6.2f}% "
                f"EXP={result['expectancy']:+.4f}"
            )

        except Exception as exc:

            print(
                f"{symbol:10} ERROR {exc}"
            )

        time.sleep(0.15)

    if not results:
        print()
        print("NO RESULTS")
        return

    df = pd.DataFrame(results)

    total_trades = int(
        df["trades"].sum()
    )

    total_wins = int(
        df["wins"].sum()
    )

    total_losses = int(
        df["losses"].sum()
    )

    # Each symbol is tested with its own starting capital. These sums are
    # pooled research statistics, not the result of one simultaneous portfolio.
    total_pnl = float(df["pnl"].sum())
    total_gross_profit = float(df["gross_profit"].sum())
    total_gross_loss = float(df["gross_loss"].sum())
    aggregate_pf = (
        total_gross_profit / total_gross_loss
        if total_gross_loss > 0
        else (999.0 if total_gross_profit > 0 else 0.0)
    )

    weighted_win_rate = (
        total_wins
        / total_trades
        * 100
        if total_trades
        else 0
    )

    profitable_symbols = int(
        (df["pnl"] > 0).sum()
    )

    losing_symbols = int(
        (df["pnl"] < 0).sum()
    )

    flat_symbols = int(
        (df["pnl"] == 0).sum()
    )

    average_pf = float(
        df["profit_factor"]
        .replace([np.inf], np.nan)
        .mean()
    )

    median_pf = float(
        df["profit_factor"]
        .replace([np.inf], np.nan)
        .median()
    )

    average_pnl = float(
        df["pnl"].mean()
    )

    median_pnl = float(
        df["pnl"].median()
    )

    average_dd = float(
        df["max_drawdown"].mean()
    )

    worst_dd = float(
        df["max_drawdown"].max()
    )

    total_expectancy = (
        total_pnl / total_trades
        if total_trades
        else 0
    )

    print()
    print("=" * 95)
    print("FINAL RESULTS — INDEPENDENT $100 TEST PER SYMBOL")
    print("=" * 95)

    print(
        f"Symbols             : {len(df)}"
    )

    print(
        f"Profitable symbols  : {profitable_symbols}"
    )

    print(
        f"Losing symbols      : {losing_symbols}"
    )

    print(
        f"Flat symbols        : {flat_symbols}"
    )

    print(
        f"Total trades        : {total_trades}"
    )

    print(
        f"Total wins          : {total_wins}"
    )

    print(
        f"Total losses        : {total_losses}"
    )

    print(
        f"Win rate            : "
        f"{weighted_win_rate:.2f}%"
    )

    print(
        f"Sum of test PnL     : "
        f"{total_pnl:+.2f} USDT (NOT a portfolio return)"
    )

    print(
        f"Average PnL/symbol  : "
        f"{average_pnl:+.2f} USDT"
    )

    print(
        f"Median PnL/symbol   : "
        f"{median_pnl:+.2f} USDT"
    )

    print(
        f"Average PF          : "
        f"{average_pf:.2f}"
    )

    print(
        f"Pooled PF           : "
        f"{aggregate_pf:.2f}"
    )

    print(
        f"Median PF           : "
        f"{median_pf:.2f}"
    )

    print(
        f"Average expectancy  : "
        f"{total_expectancy:+.4f} USDT/trade"
    )

    print(
        f"Average Max DD      : "
        f"{average_dd:.2f}%"
    )

    print(
        f"Worst Max DD        : "
        f"{worst_dd:.2f}%"
    )

    print("=" * 95)

    # =====================================================
    # PROFITABLE SYMBOLS
    # =====================================================

    profitable = (
        df[df["pnl"] > 0]
        .sort_values(
            "pnl",
            ascending=False,
        )
    )

    losing = (
        df[df["pnl"] < 0]
        .sort_values(
            "pnl",
            ascending=True,
        )
    )

    print()
    print("TOP PROFITABLE SYMBOLS")
    print("-" * 95)

    if profitable.empty:

        print("None")

    else:

        for _, row in profitable.head(10).iterrows():

            print(
                f"{row['symbol']:10} "
                f"PnL={row['pnl']:+8.2f} "
                f"PF={row['profit_factor']:6.2f} "
                f"WR={row['win_rate']:5.1f}% "
                f"DD={row['max_drawdown']:6.2f}%"
            )

    print()
    print("WORST SYMBOLS")
    print("-" * 95)

    if losing.empty:

        print("None")

    else:

        for _, row in losing.head(10).iterrows():

            print(
                f"{row['symbol']:10} "
                f"PnL={row['pnl']:+8.2f} "
                f"PF={row['profit_factor']:6.2f} "
                f"WR={row['win_rate']:5.1f}% "
                f"DD={row['max_drawdown']:6.2f}%"
            )

    print()
    print("=" * 95)

    # =====================================================
    # SIMPLE VERDICT
    # =====================================================

    print("SYSTEM VERDICT")
    print("=" * 95)

    if total_trades < BACKTEST_MIN_TRADES:

        print(
            "NOT ENOUGH TRADES FOR A RELIABLE VERDICT."
        )

    elif (
        total_pnl > 0
        and aggregate_pf > 1.0
        and total_expectancy > 0
        and (worst_dd / 100.0) <= MAX_BACKTEST_DRAWDOWN
    ):

        print(
            "POSITIVE IN-SAMPLE RESULT ONLY: this sample passes the configured "
            "profit-factor, expectancy and drawdown checks."
        )

        print(
            "NEXT STEP: untouched out-of-sample and walk-forward tests; "
            "this is not proof of future/live profitability."
        )

    else:

        print(
            "NOT ACCEPTED: profitability, pooled PF, expectancy or "
            "drawdown did not pass the configured checks."
        )

    print("=" * 95)


if __name__ == "__main__":
    main()
