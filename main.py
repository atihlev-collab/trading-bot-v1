import json, logging, math, os, time
from datetime import datetime, timezone
from market_data import get_candles
from scanner import scan_market

START_BALANCE=float(os.getenv("START_BALANCE","100"))
RISK_PER_TRADE=float(os.getenv("RISK_PER_TRADE","0.01"))
MAX_POSITIONS=int(os.getenv("MAX_POSITIONS","3"))
SCAN_SECONDS=int(os.getenv("SCAN_SECONDS","60"))
SL_ATR=float(os.getenv("SL_ATR","1.5"))
TP_ATR=float(os.getenv("TP_ATR","2.4"))
TRAIL_ATR=float(os.getenv("TRAIL_ATR","1.2"))
FEE_RATE=float(os.getenv("FEE_RATE","0.0004"))
SLIPPAGE=float(os.getenv("SLIPPAGE","0.0002"))
STATE_FILE=os.getenv("STATE_FILE","trading_state_v5.json")

logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s")
log=logging.getLogger("TradingBotV5")

def sf(x,d=0.0):
    try:
        x=float(x); return x if math.isfinite(x) else d
    except: return d

def load():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE,encoding="utf-8") as f: s=json.load(f)
            s.setdefault("balance",START_BALANCE); s.setdefault("start_balance",START_BALANCE); s.setdefault("positions",{}); s.setdefault("trades",[]); return s
        except Exception as e: log.warning("state load failed: %s",e)
    return {"balance":START_BALANCE,"start_balance":START_BALANCE,"positions":{},"trades":[]}
state=load()

def save():
    tmp=STATE_FILE+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(state,f,indent=2)
    os.replace(tmp,STATE_FILE)

def pnl_open():
    return sum((sf(p["last_price"])-sf(p["entry"]))*sf(p["qty"]) for p in state["positions"].values())

def equity(): return sf(state["balance"])+pnl_open()

def account():
    print(f"BALANCE: {state['balance']:.2f} | EQUITY: {equity():.2f} | OPEN_PNL: {pnl_open():+.2f} | POSITIONS: {len(state['positions'])}")

def size(entry,stop,qf):
    risk=max(0,equity()*RISK_PER_TRADE); dist=abs(entry-stop)
    if risk<=0 or dist<=0:return 0
    qty=risk/dist*max(.35,min(1,qf))
    return min(qty,max(0,state["balance"]*.95/entry))

def open_pos(s):
    sym=s["symbol"]
    if sym in state["positions"]: log.info("[SKIP] %s already has position",sym); return
    if len(state["positions"])>=MAX_POSITIONS: return
    entry=sf(s["close"])*(1+SLIPPAGE); a=sf(s["atr"])
    if entry<=0 or a<=0:return
    stop=entry-a*SL_ATR; target=entry+a*TP_ATR
    qty=size(entry,stop,sf(s.get("quality_factor"),.7))
    fee=entry*qty*FEE_RATE
    if qty<=0 or entry*qty+fee>state["balance"]:return
    state["balance"]-=fee
    state["positions"][sym]={"symbol":sym,"entry":entry,"qty":qty,"stop":stop,"target":target,"highest":entry,"last_price":entry,"opened_at":datetime.now(timezone.utc).isoformat(),"score":s["score"],"confidence":s["confidence"],"quality":s["quality"],"atr":a}
    save()
    log.info("[OPEN] %s Entry=%.6f Qty=%.6f SL=%.6f TP=%.6f Risk=%.4f Score=%s Conf=%s Q=%s",sym,entry,qty,stop,target,(entry-stop)*qty,s["score"],s["confidence"],s["quality"])

def close_pos(sym,price,reason):
    p=state["positions"].get(sym)
    if not p:return
    exitp=sf(price)*(1-SLIPPAGE); qty=sf(p["qty"]); entry=sf(p["entry"])
    net=(exitp-entry)*qty-exitp*qty*FEE_RATE
    state["balance"]+=net
    state["trades"].append({"symbol":sym,"entry":entry,"exit":exitp,"qty":qty,"pnl":net,"reason":reason,"opened_at":p.get("opened_at"),"closed_at":datetime.now(timezone.utc).isoformat()})
    del state["positions"][sym]; save()
    log.info("[CLOSE] %s Exit=%.6f PNL=%+.4f Reason=%s",sym,exitp,net,reason)

def update_positions():
    for sym in list(state["positions"]):
        p=state["positions"].get(sym)
        try:
            c=get_candles(sym,"1m")
            if c is None or len(c)<3:continue
            row=c.iloc[-1]; close=sf(row["close"]); high=sf(row["high"]); low=sf(row["low"])
            p["last_price"]=close; p["highest"]=max(sf(p["highest"]),high)
            entry=sf(p["entry"]); a=sf(p["atr"]); stop=sf(p["stop"]); target=sf(p["target"]); hi=sf(p["highest"])
            if a and hi>=entry+a: stop=max(stop,entry+a*.1)
            if a and hi>=entry+a*1.5: stop=max(stop,hi-a*TRAIL_ATR)
            p["stop"]=stop
            # If SL and TP occur in the same candle, assume SL first.
            if low<=stop: close_pos(sym,stop,"SL")
            elif high>=target: close_pos(sym,target,"TP")
        except Exception as e: log.warning("[POSITION ERROR] %s: %s",sym,e)
    save()

def stats():
    t=state["trades"]; wins=sum(sf(x.get("pnl"))>0 for x in t); losses=len(t)-wins
    gp=sum(sf(x.get("pnl")) for x in t if sf(x.get("pnl"))>0); gl=abs(sum(sf(x.get("pnl")) for x in t if sf(x.get("pnl"))<0))
    pf=gp/gl if gl else (float("inf") if gp else 0); wr=wins/len(t)*100 if t else 0
    print(f"TRADES: {len(t)} | WINS: {wins} | LOSSES: {losses} | WIN RATE: {wr:.1f}% | PROFIT FACTOR: {'INF' if math.isinf(pf) else f'{pf:.2f}'} | REALIZED P/L: {state['balance']-state['start_balance']:+.2f}")

def main():
    log.info("================================================================="); log.info("Trading Bot V5 Started"); log.info("=================================================================")
    account(); log.info("Start balance: %.2f USDT",START_BALANCE); log.info("Risk/trade: %.1f%%",RISK_PER_TRADE*100); log.info("Max positions: %s",MAX_POSITIONS); log.info("BUY score threshold: 78"); log.info("================================================================="); log.info("=== LOOP START ===")
    while True:
        try:
            update_positions(); account()
            signals=scan_market(); log.info("scan_market returned %s signals",len(signals))
            buys=[x for x in signals if x["signal"]=="BUY"]
            buys.sort(key=lambda x:(x["quality_factor"],x["score"],x["confidence"],x["confirmations"]),reverse=True)
            for s in buys:
                if s["quality"] in ("A+","A","B"): open_pos(s)
            account(); stats()
        except Exception as e: log.exception("[LOOP ERROR] %s",e)
        time.sleep(max(10,SCAN_SECONDS))

if __name__=="__main__": main()
