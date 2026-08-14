import sqlite3
from datetime import datetime, timezone
from config import DB_FILE

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            side TEXT,
            entry REAL,
            exit REAL,
            quantity REAL,
            pnl REAL,
            reason TEXT,
            quality TEXT,
            confidence REAL,
            score REAL,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_trade(result):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO trades(
            symbol, side, entry, exit, quantity, pnl,
            reason, quality, confidence, score, created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (
        result["symbol"], "LONG", result["entry"], result["exit"],
        result["quantity"], result["pnl"], result["reason"],
        result.get("quality", ""), result.get("confidence", 0),
        result.get("score", 0), datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()

def load_stats():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*),
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END),
               COALESCE(SUM(pnl),0)
        FROM trades
    """)
    trades, wins, pnl = cur.fetchone()
    conn.close()
    trades = trades or 0
    wins = wins or 0
    return {
        "trades": trades,
        "wins": wins,
        "win_rate": round(wins / trades * 100, 1) if trades else 0,
        "pnl": round(pnl or 0, 4),
    }
