import pandas as pd
import numpy as np

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def sma(series, period):
    return series.rolling(period).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    return 100 - (100 / (1 + rs))

def atr(df, period=14):
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False, min_periods=period).mean()

def momentum(series, period=5):
    return series.pct_change(period)

def volume_ma(volume, period=20):
    return volume.rolling(period).mean()

def atr_percent(close, atr_values):
    return atr_values / close.replace(0, np.nan)

def trend_strength(ema_fast, ema_slow):
    return ((ema_fast - ema_slow) / ema_slow.replace(0, np.nan)) * 100

def vwap(df):
    price = (df["high"] + df["low"] + df["close"]) / 3
    return (price * df["volume"]).cumsum() / df["volume"].cumsum().replace(0, np.nan)

def macd(series):
    e12 = ema(series, 12)
    e26 = ema(series, 26)
    line = e12 - e26
    signal = ema(line, 9)
    return line, signal, line - signal

def bollinger(series, period=20):
    middle = sma(series, period)
    std = series.rolling(period).std()
    return middle + 2*std, middle, middle - 2*std

def adx(df, period=14):
    high, low, close = df["high"], df["low"], df["close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    prev_close = close.shift(1)
    tr = pd.concat([
        high-low, (high-prev_close).abs(), (low-prev_close).abs()
    ], axis=1).max(axis=1)
    atr_v = tr.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False, min_periods=period).mean() / atr_v.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False, min_periods=period).mean() / atr_v.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1/period, adjust=False, min_periods=period).mean()

def candle_body_percent(open_price, close_price):
    return (close_price - open_price) / open_price if open_price else 0.0

def bullish(open_price, close_price):
    return close_price > open_price

def bearish(open_price, close_price):
    return close_price < open_price
