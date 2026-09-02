# ==========================================
# Trading Bot V5 - INDICATORS
# ==========================================

import pandas as pd
import numpy as np


def ema(series, period):
    return series.ewm(
        span=period,
        adjust=False,
        min_periods=period
    ).mean()


def sma(series, period):
    return series.rolling(
        period,
        min_periods=period
    ).mean()


def rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    return 100 - (100 / (1 + rs))


def atr(df, period=14):
    prev_close = df["close"].shift(1)

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()


def atr_percent(close, atr_values):
    return atr_values / close.replace(0, np.nan)


def momentum(series, period=5):
    return series.pct_change(period)


def volume_ma(volume, period=20):
    return volume.rolling(
        period,
        min_periods=period
    ).mean()


def volume_ratio(volume, period=20):
    ma = volume_ma(volume, period)
    return volume / ma.replace(0, np.nan)


def trend_strength(ema_fast, ema_slow):
    return (
        (ema_fast - ema_slow)
        / ema_slow.replace(0, np.nan)
    ) * 100


def vwap(df):
    price = (
        df["high"]
        + df["low"]
        + df["close"]
    ) / 3

    volume_sum = df["volume"].cumsum()

    return (
        (price * df["volume"]).cumsum()
        / volume_sum.replace(0, np.nan)
    )


def macd(series, fast=12, slow=26, signal_period=9):
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)

    line = fast_ema - slow_ema
    signal = ema(line, signal_period)

    histogram = line - signal

    return line, signal, histogram


def bollinger(series, period=20, std_mult=2.0):
    middle = sma(series, period)
    std = series.rolling(
        period,
        min_periods=period
    ).std()

    upper = middle + std_mult * std
    lower = middle - std_mult * std

    return upper, middle, lower


def adx(df, period=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where(
            (up_move > down_move) & (up_move > 0),
            up_move,
            0.0,
        ),
        index=df.index,
    )

    minus_dm = pd.Series(
        np.where(
            (down_move > up_move) & (down_move > 0),
            down_move,
            0.0,
        ),
        index=df.index,
    )

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr_v = tr.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    plus_di = (
        100
        * plus_dm.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period
        ).mean()
        / atr_v.replace(0, np.nan)
    )

    minus_di = (
        100
        * minus_dm.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period
        ).mean()
        / atr_v.replace(0, np.nan)
    )

    di_sum = (
        plus_di + minus_di
    ).replace(0, np.nan)

    dx = (
        100
        * (plus_di - minus_di).abs()
        / di_sum
    )

    return dx.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()


def candle_body_percent(open_price, close_price):
    if open_price == 0:
        return 0.0

    return (
        (close_price - open_price)
        / open_price
    )


def candle_range_percent(high, low, close):
    if close == 0:
        return 0.0

    return (high - low) / close


def upper_wick(open_price, high, close_price):
    return (
        high - max(open_price, close_price)
    )


def lower_wick(open_price, low, close_price):
    return (
        min(open_price, close_price) - low
    )


def bullish(open_price, close_price):
    return close_price > open_price


def bearish(open_price, close_price):
    return close_price < open_price


def higher_high(df, lookback=3):
    if len(df) < lookback + 1:
        return False

    recent = df["high"].iloc[-lookback:]
    previous = df["high"].iloc[-lookback - 1:-1]

    return recent.iloc[-1] > previous.max()


def higher_low(df, lookback=3):
    if len(df) < lookback + 1:
        return False

    recent = df["low"].iloc[-lookback:]
    previous = df["low"].iloc[-lookback - 1:-1]

    return recent.iloc[-1] > previous.min()


def bullish_structure(df, lookback=3):
    return (
        higher_high(df, lookback)
        and higher_low(df, lookback)
    )
