import pandas as pd


# ==========================================
# Moving Averages
# ==========================================

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def sma(series, period):
    return series.rolling(period).mean()


# ==========================================
# RSI
# ==========================================

def rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    rs = avg_gain / avg_loss.replace(0, 1e-12)

    return 100 - (100 / (1 + rs))


# ==========================================
# ATR
# ==========================================

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
        min_periods=period,
    ).mean()


# ==========================================
# Momentum
# ==========================================

def momentum(series, period=5):
    return series.pct_change(period)


# ==========================================
# Volume MA
# ==========================================

def volume_ma(volume, period=20):
    return volume.rolling(period).mean()


# ==========================================
# ATR %
# ==========================================

def atr_percent(close, atr_values):
    return atr_values / close


# ==========================================
# Trend Strength
# ==========================================

def trend_strength(ema_fast, ema_slow):
    return ((ema_fast - ema_slow) / ema_slow) * 100


# ==========================================
# VWAP
# ==========================================

def vwap(df):

    price = (
        df["high"] +
        df["low"] +
        df["close"]
    ) / 3

    return (
        (price * df["volume"]).cumsum()
        /
        df["volume"].cumsum()
    )


# ==========================================
# MACD
# ==========================================

def macd(series):

    ema12 = ema(series, 12)
    ema26 = ema(series, 26)

    line = ema12 - ema26

    signal = ema(line, 9)

    hist = line - signal

    return line, signal, hist


# ==========================================
# Bollinger Bands
# ==========================================

def bollinger(series, period=20):

    middle = sma(series, period)

    std = series.rolling(period).std()

    upper = middle + std * 2

    lower = middle - std * 2

    return upper, middle, lower


# ==========================================
# Highest High
# ==========================================

def highest(series, period):
    return series.rolling(period).max()


# ==========================================
# Lowest Low
# ==========================================

def lowest(series, period):
    return series.rolling(period).min()


# ==========================================
# Candle Body %
# ==========================================

def candle_body_percent(open_price, close_price):

    return (
        (close_price - open_price)
        /
        open_price
    )


# ==========================================
# Bullish Candle
# ==========================================

def bullish(open_price, close_price):

    return close_price > open_price


# ==========================================
# Bearish Candle
# ==========================================

def bearish(open_price, close_price):

    return close_price < open_price