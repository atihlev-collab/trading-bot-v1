import pandas as pd

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def sma(series, period):
    return series.rolling(period).mean()


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

    rs = avg_gain / avg_loss.replace(0, 1e-12)

    return 100 - (100 / (1 + rs))


def atr(df, period=14):
    prev_close = df["close"].shift(1)

    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()


def momentum(series, period=5):
    return series.pct_change(period)


def volume_ma(volume, period=20):
    return volume.rolling(period).mean()


def atr_percent(close, atr_values):
    return atr_values / close


def trend_strength(ema_fast, ema_slow):
    return ((ema_fast - ema_slow) / ema_slow) * 100
