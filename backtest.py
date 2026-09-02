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
    SYMBOLS,

    LOWER_TIMEFRAME,
    HIGHER_TIMEFRAME,

    CANDLE_LIMIT,

    EMA_FAST,
    EMA_SLOW,
    EMA_TREND,

    RSI_PERIOD,
    RSI_MIN,
    RSI_MAX,

    ATR_PERIOD,
    MIN_ATR_PERCENT,
    MAX_ATR_PERCENT,

    VOLUME_PERIOD,
    VOLUME_MULTIPLIER,

    MIN_MOMENTUM,
    MIN_TREND_STRENGTH,
    MAX_GREEN_CANDLE,

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

def get_history(symbol, interval, limit=1000):
    url = f"{BASE_URL}/api/v3/klines"

    response = requests.get(
        url,
        params={
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000),
        },
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    if not data:
        raise RuntimeError(
            f"No historical data for {symbol} {interval}"
        )

    df = pd.DataFrame(
        data,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )

    df["open_time"] = pd.to_datetime(
        df["open_time"],
        unit="ms",
        utc=True,
    )

    df["close_time"] = pd.to_datetime(
        df["close_time"],
        unit="ms",
        utc=True,
    )

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )

    # Never use currently-forming candle.
    if len(df) > 2:
        df = df.iloc[:-1].copy()

    return df.reset_index(drop=True)


# =========================================================
# INDICATORS
# =========================================================

def prepare(df):
    df = df.copy()

    df["ema20"] = ema(
        df["close"],
        EMA_FAST,
    )

    df["ema50"] = ema(
        df["close"],
        EMA_SLOW,
    )

    df["ema200"] = ema(
        df["close"],
        EMA_TREND,
    )

    df["rsi"] = rsi(
        df["close"],
        RSI_PERIOD,
    )

    df["atr"] = atr(
        df,
        ATR_PERIOD,
    )

    df["mom"] = momentum(
        df["close"],
        5,
    )

    df["vol_ma"] = volume_ma(
        df["volume"],
        VOLUME_PERIOD,
    )

    df["trend"] = trend_strength(
        df["ema20"],
        df["ema50"],
    )

    _, _, df["macd_hist"] = macd(
        df["close"]
    )

    df["adx"] = adx(
        df,
        14,
    )

    return df


# =========================================================
# HTF MERGE
# =========================================================

def add_higher_timeframe(low, high):
    high_view = high[
        [
            "open_time",
            "close",
            "ema20",
            "ema50",
            "ema200",
        ]
    ].copy()

    high_view.columns = [
        "htf_time",
        "htf_close",
        "htf_ema20",
        "htf_ema50",
        "htf_ema200",
    ]

    low = pd.merge_asof(
        low.sort_values("open_time"),
        high_view.sort_values("htf_time"),
        left_on="open_time",
        right_on="htf_time",
        direction="backward",
    )

    return low.reset_index(drop=True)


# =========================================================
# ENTRY CONDITIONS
# =========================================================

def valid_entry(row):
    required = [
        row["htf_close"],
        row["htf_ema20"],
        row["htf_ema50"],
        row["htf_ema200"],
        row["ema20"],
        row["ema50"],
        row["ema200"],
        row["rsi"],
        row["atr"],
        row["mom"],
        row["vol_ma"],
        row["trend"],
        row["macd_hist"],
        row["adx"],
    ]

    if not all(np.isfinite(x) for x in required):
        return False

    price = float(row["close"])

    if price <= 0:
        return False

    atr_pct = float(row["atr"]) / price

    if not (
        MIN_ATR_PERCENT
        <= atr_pct
        <= MAX_ATR_PERCENT
    ):
        return False

    volume_ma_value = float(row["vol_ma"])

    if volume_ma_value <= 0:
        return False

    volume_ratio = (
        float(row["volume"])
        / volume_ma_value
    )

    candle_body = (
        abs(float(row["close"]) - float(row["open"]))
        / float(row["open"])
        if row["open"] > 0
        else 999
    )

    conditions = [

        # Higher timeframe trend
        row["htf_close"] > row["htf_ema200"],
        row["htf_ema20"] > row["htf_ema50"],

        # Lower timeframe trend
        price > row["ema200"],
        row["ema20"] > row["ema50"],

        # Momentum
        MIN_MOMENTUM <= row["mom"],

        # RSI
        RSI_MIN <= row["rsi"] <= RSI_MAX,

        # Volatility
        MIN_ATR_PERCENT <= atr_pct <= MAX_ATR_PERCENT,

        # Trend strength
        row["trend"] >= MIN_TREND_STRENGTH,

        # Volume
        volume_ratio >= VOLUME_MULTIPLIER,

        # Candle protection
        candle_body <= MAX_GREEN_CANDLE,

        # MACD
        row["macd_hist"] > 0,

        # ADX
        row["adx"] >= 18,
    ]

    return all(conditions)


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

def close_position(
    balance,
    position,
    exit_price,
):
    quantity = position["quantity"]

    exit_price = (
        exit_price
        * (1 - SLIPPAGE_RATE)
    )

    gross_value = (
        exit_price
        * quantity
    )

    exit_fee = (
        gross_value
        * FEE_RATE
    )

    proceeds = (
        gross_value
        - exit_fee
    )

    pnl = (
        exit_price
        - position["entry"]
    ) * quantity

    pnl -= position["entry"] * quantity * FEE_RATE
    pnl -= exit_fee

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
        1000,
    )

    high_raw = get_history(
        symbol,
        HIGHER_TIMEFRAME,
        1000,
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

    max_balance = balance
    max_drawdown = 0.0

    # Need enough history for EMA200 etc.
    start_index = 220

    for i in range(
        start_index,
        len(low),
    ):
        row = low.iloc[i]

        current_close = float(
            row["close"]
        )

        current_high = float(
            row["high"]
        )

        current_low = float(
            row["low"]
        )

        # =================================================
        # MANAGE OPEN POSITION
        # =================================================

        if position is not None:

            entry = position["entry"]
            initial_risk = position[
                "initial_risk_per_unit"
            ]

            # -------------------------------------------------
            # 1. BREAK EVEN
            # -------------------------------------------------

            if (
                not position["break_even"]
                and current_high
                >= entry
                + initial_risk * BREAK_EVEN_AT
            ):
                position["stop"] = entry
                position["break_even"] = True

            # -------------------------------------------------
            # 2. UPDATE HIGHEST
            # -------------------------------------------------

            position["highest"] = max(
                position["highest"],
                current_high,
            )

            # -------------------------------------------------
            # 3. TRAILING STOP
            # -------------------------------------------------

            if TRAILING_STOP:

                trail_activation = (
                    entry
                    + initial_risk
                    * TRAILING_AT_R
                )

                if (
                    current_high
                    >= trail_activation
                ):

                    atr_value = float(
                        row["atr"]
                    )

                    if np.isfinite(
                        atr_value
                    ):

                        trailing_stop = (
                            position["highest"]
                            - atr_value
                            * TRAILING_ATR
                        )

                        if (
                            trailing_stop
                            > position["stop"]
                        ):
                            position["stop"] = (
                                trailing_stop
                            )

            stop = position["stop"]
            take = position["take"]

            # -------------------------------------------------
            # 4. EXIT LOGIC
            # -------------------------------------------------

            stop_hit = (
                current_low
                <= stop
            )

            take_hit = (
                current_high
                >= take
            )

            exit_reason = None
            exit_price = None

            # Conservative assumption:
            # if both SL and TP happen in same candle,
            # SL happens first.
            if stop_hit:
                exit_reason = "STOP"
                exit_price = stop

            elif take_hit:
                exit_reason = "TAKE"
                exit_price = take

            if exit_reason:

                old_balance = balance

                balance, pnl, actual_exit = (
                    close_position(
                        balance,
                        position,
                        exit_price,
                    )
                )

                trades.append({
                    "symbol": symbol,
                    "entry": entry,
                    "exit": actual_exit,
                    "quantity": position[
                        "quantity"
                    ],
                    "pnl": pnl,
                    "reason": exit_reason,
                })

                position = None

                # Equity after close.
                equity = balance

                max_balance = max(
                    max_balance,
                    equity,
                )

                drawdown = (
                    (
                        max_balance
                        - equity
                    )
                    / max_balance
                    * 100
                    if max_balance > 0
                    else 0
                )

                max_drawdown = max(
                    max_drawdown,
                    drawdown,
                )

                equity_curve.append(
                    equity
                )

                continue

        # =================================================
        # NO POSITION -> LOOK FOR ENTRY
        # =================================================

        if position is not None:
            continue

        if balance <= 0:
            break

        if not valid_entry(row):
            equity_curve.append(
                balance
            )
            continue

        # -------------------------------------------------
        # ENTRY
        # -------------------------------------------------

        close_price = float(
            row["close"]
        )

        atr_value = float(
            row["atr"]
        )

        if (
            not np.isfinite(atr_value)
            or atr_value <= 0
        ):
            continue

        entry = (
            close_price
            * (1 + SLIPPAGE_RATE)
        )

        stop = (
            entry
            - atr_value
            * ATR_STOP_MULT
        )

        initial_risk = (
            entry
            - stop
        )

        if initial_risk <= 0:
            continue

        take = (
            entry
            + initial_risk
            * REWARD_RISK
        )

        quantity = calculate_position_size(
            balance,
            entry,
            stop,
        )

        if quantity <= 0:
            continue

        entry_value = (
            quantity
            * entry
        )

        entry_fee = (
            entry_value
            * FEE_RATE
        )

        total_entry_cost = (
            entry_value
            + entry_fee
        )

        if total_entry_cost > balance:
            continue

        balance -= total_entry_cost

        position = {
            "entry": entry,
            "quantity": quantity,

            "stop": stop,
            "take": take,

            "initial_stop": stop,

            "initial_risk_per_unit": (
                initial_risk
            ),

            "highest": entry,

            "break_even": False,

            "opened_index": i,
        }

        # Equity includes current position
        # at close price.
        mark_value = (
            quantity
            * current_close
        )

        unrealized = (
            current_close
            - entry
        ) * quantity

        equity = (
            balance
            + mark_value
            + unrealized * 0
        )

        max_balance = max(
            max_balance,
            equity,
        )

        drawdown = (
            (
                max_balance
                - equity
            )
            / max_balance
            * 100
            if max_balance > 0
            else 0
        )

        max_drawdown = max(
            max_drawdown,
            drawdown,
        )

        equity_curve.append(
            equity
        )

    # =====================================================
    # FORCE CLOSE LAST POSITION
    # =====================================================

    if position is not None:

        last_close = float(
            low.iloc[-1]["close"]
        )

        balance, pnl, actual_exit = (
            close_position(
                balance,
                position,
                last_close,
            )
        )

        trades.append({
            "symbol": symbol,
            "entry": position["entry"],
            "exit": actual_exit,
            "quantity": position["quantity"],
            "pnl": pnl,
            "reason": "END",
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

    total_pnl = float(
        df["pnl"].sum()
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
    print("FINAL RESULTS")
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
        f"Total PnL           : "
        f"{total_pnl:+.2f} USDT"
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

    if total_trades < 30:

        print(
            "NOT ENOUGH TRADES FOR A RELIABLE VERDICT."
        )

    elif (
        total_pnl > 0
        and average_pf > 1.0
        and total_expectancy > 0
    ):

        print(
            "POSITIVE RESULT: strategy is profitable "
            "on this historical sample."
        )

        print(
            "NEXT STEP: robustness testing and "
            "parameter validation."
        )

    else:

        print(
            "NOT PROFITABLE ENOUGH: strategy needs "
            "further improvement."
        )

    print("=" * 95)


if __name__ == "__main__":
    main()
