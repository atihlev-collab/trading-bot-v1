
import math

from config import (
    SYMBOLS, LOWER_TIMEFRAME, HIGHER_TIMEFRAME,
    EMA_FAST, EMA_SLOW, EMA_TREND,
    RSI_PERIOD, RSI_MIN, RSI_MAX,
    ATR_PERIOD, MIN_ATR_PERCENT, MAX_ATR_PERCENT,
    VOLUME_PERIOD, MIN_MOMENTUM, MAX_GREEN_CANDLE, BUY_SCORE,
)
from indicators import ema, rsi, atr, momentum, volume_ma, trend_strength, macd, adx
from market_data import get_candles


def num(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def ratio(a, b):
    a, b = num(a), num(b)
    return a / b if a is not None and b and b > 0 else 0.0


def analyze_symbol(symbol):
    try:
        low = get_candles(symbol, LOWER_TIMEFRAME)
        high = get_candles(symbol, HIGHER_TIMEFRAME)
        if low is None or high is None or len(low) < 220 or len(high) < 220:
            return None

        lc, hc = low["close"], high["close"]
        lf, ls, lt = ema(lc, EMA_FAST), ema(lc, EMA_SLOW), ema(lc, EMA_TREND)
        hf, hs, ht = ema(hc, EMA_FAST), ema(hc, EMA_SLOW), ema(hc, EMA_TREND)
        rv, av = rsi(lc, RSI_PERIOD), atr(low, ATR_PERIOD)
        mv, vma = momentum(lc, 5), volume_ma(low["volume"], VOLUME_PERIOD)
        _, _, mh = macd(lc)
        ax = adx(low, 14)
        i = -1

        price, a, r = num(lc.iloc[i]), num(av.iloc[i]), num(rv.iloc[i])
        mom, axn, mhist = num(mv.iloc[i]), num(ax.iloc[i]), num(mh.iloc[i])
        vol = num(low["volume"].iloc[i]) or 0.0
        vavg = num(vma.iloc[i]) or 0.0
        op = num(low["open"].iloc[i])
        hc0, hf0, hs0, ht0 = num(hc.iloc[i]), num(hf.iloc[i]), num(hs.iloc[i]), num(ht.iloc[i])
        lf0, ls0, lt0 = num(lf.iloc[i]), num(ls.iloc[i]), num(lt.iloc[i])

        if any(x is None for x in [price,a,r,mom,axn,mhist,op,hc0,hf0,hs0,ht0,lf0,ls0,lt0]) or price <= 0 or a <= 0:
            return None

        atr_pct = a / price
        if not MIN_ATR_PERCENT <= atr_pct <= MAX_ATR_PERCENT:
            return None

        htf = hc0 > ht0 and hf0 > hs0
        ltf = price > lt0 and lf0 > ls0
        vr = ratio(vol, vavg)
        body = abs(price - op) / op

        score, reasons = 0, []
        if htf: score += 20; reasons.append("HTF")
        elif hc0 > ht0: score += 8; reasons.append("HTF-WEAK")
        if ltf: score += 20; reasons.append("LTF")
        elif price > lt0: score += 8; reasons.append("LTF-WEAK")

        if 52 <= r <= 64: score += 15; reasons.append("RSI+")
        elif 48 <= r <= 68: score += 10; reasons.append("RSI")
        elif 44 <= r < 48: score += 4; reasons.append("RSI-WEAK")

        if mom >= 0.006: score += 15; reasons.append("MOM+")
        elif mom >= max(0.003, MIN_MOMENTUM): score += 10; reasons.append("MOM")
        elif mom >= MIN_MOMENTUM * .75: score += 4; reasons.append("MOM-WEAK")

        if axn >= 30: score += 15; reasons.append("ADX+")
        elif axn >= 25: score += 10; reasons.append("ADX")
        elif axn >= 18: score += 5; reasons.append("ADX-WEAK")

        if mhist > 0: score += 10; reasons.append("MACD")
        elif mhist >= 0: score += 5; reasons.append("MACD-FLAT")

        if vr >= 1.5: score += 10; reasons.append("VOL+")
        elif vr >= 1.2: score += 7; reasons.append("VOL")
        elif vr >= .95: score += 3; reasons.append("VOL-NORMAL")

        if body <= MAX_GREEN_CANDLE * .7: score += 5; reasons.append("CANDLE")
        elif body <= MAX_GREEN_CANDLE: score += 3; reasons.append("CANDLE-WEAK")

        if r > 68: score -= 10; reasons.append("RSI-HIGH")
        if body > MAX_GREEN_CANDLE: score -= 10; reasons.append("CANDLE-LARGE")
        if mhist < 0: score -= 7
        if mom < MIN_MOMENTUM * .75: score -= 7
        if axn < 15: score -= 5; reasons.append("ADX-LOW")
        score = max(0, min(100, int(round(score))))

        points = sum([htf, ltf, 50 <= r <= 66, mom >= .003, axn >= 20, mhist > 0, vr >= 1.10])
        confidence = round(points / 7 * 100)
        strong = htf and ltf
        confirmations = sum([strong, mom >= max(.0025, MIN_MOMENTUM*.9), axn >= 18, mhist > 0, 48 <= r <= 67, vr >= .95, body <= MAX_GREEN_CANDLE])
        min_buy = max(78, int(BUY_SCORE))

        if score >= min_buy and confidence >= 71 and confirmations >= 6 and strong and axn >= 18 and mhist > 0 and 48 <= r <= 67:
            signal = "BUY"
        elif score >= 70 and confidence >= 57 and confirmations >= 4:
            signal = "WATCH"
        else:
            return None

        quality = "A+" if score >= 92 and confidence >= 85 else "A" if score >= 86 and confidence >= 71 else "B" if score >= 78 else "C"
        qfactor = {"A+":1.0,"A":.9,"B":.7,"C":.4}[quality]

        return {
            "symbol": symbol, "signal": signal, "score": score, "confidence": confidence,
            "quality": quality, "quality_factor": qfactor, "close": price, "atr": a,
            "atr_pct": atr_pct, "trend_strength": num(trend_strength(lf,ls).iloc[i]) or 0.0,
            "momentum": mom, "volume": vol, "volume_ma": vavg, "volume_ratio": vr,
            "rsi": r, "adx": axn, "macd_hist": mhist, "htf_bull": htf, "ltf_bull": ltf,
            "candle_body": body, "confirmations": confirmations, "reasons": reasons,
        }
    except Exception as exc:
        print(f"[SCAN ERROR] {symbol}: {exc}")
        return None


def scan_market():
    signals=[]; buys=watch=0
    for symbol in SYMBOLS:
        r=analyze_symbol(symbol)
        if not r: continue
        signals.append(r)
        buys += r["signal"] == "BUY"
        watch += r["signal"] == "WATCH"
    signals.sort(key=lambda x:(x["signal"]=="BUY",x["score"],x["confidence"],x["confirmations"],x["adx"],x["momentum"]), reverse=True)
    print(f"[SCAN] Checked={len(SYMBOLS)} Candidates={len(signals)} BUY={buys} WATCH={watch}")
    if signals:
        x=signals[0]
        print(f"[TOP] {x['symbol']} {x['signal']} Score={x['score']} RSI={x['rsi']:.1f} ADX={x['adx']:.1f} MOM={x['momentum']:.4f} VOL={x['volume_ratio']:.2f} HTF={x['htf_bull']} LTF={x['ltf_bull']} CONF={x['confidence']} Q={x['quality']} CONFIRM={x['confirmations']}/7")
        print("[REASONS] " + ", ".join(x["reasons"]))
    return signals
