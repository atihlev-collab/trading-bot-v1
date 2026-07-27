import sqlite3
from config import DB_FILE, START_BALANCE

def connect():
    return sqlite3.connect(DB_FILE)

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS state (
            id INTEGER PRIMARY KEY CHECK(id=1),
            cash REAL NOT NULL,
            realized_pnl REAL NOT NULL DEFAULT 0
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS positions (
            symbol TEXT PRIMARY KEY,
            entry REAL NOT NULL,
            qty REAL NOT NULL,
            stop REAL NOT NULL,
            target REAL NOT NULL,
            entry_fee REAL NOT NULL,
            opened_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            entry REAL NOT NULL,
            exit REAL NOT NULL,
            qty REAL NOT NULL,
            entry_fee REAL NOT NULL,
            exit_fee REAL NOT NULL,
            pnl REAL NOT NULL,
            reason TEXT NOT NULL,
            opened_at TEXT NOT NULL,
            closed_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, candle_time TEXT, score INTEGER, rsi REAL,
            created_at TEXT,
            UNIQUE(symbol, candle_time)
        )""")
        row = con.execute("SELECT id FROM state WHERE id=1").fetchone()
        if not row:
            con.execute("INSERT INTO state(id,cash,realized_pnl) VALUES(1,?,0)", (START_BALANCE,))

def get_cash():
    with connect() as con:
        return float(con.execute("SELECT cash FROM state WHERE id=1").fetchone()[0])

def get_positions():
    with connect() as con:
        rows = con.execute("SELECT symbol,entry,qty,stop,target,entry_fee,opened_at FROM positions").fetchall()
    return [
        dict(zip(["symbol","entry","qty","stop","target","entry_fee","opened_at"], r))
        for r in rows
    ]

def get_position(symbol):
    with connect() as con:
        r = con.execute(
            "SELECT symbol,entry,qty,stop,target,entry_fee,opened_at FROM positions WHERE symbol=?",
            (symbol,)
        ).fetchone()
    return None if not r else dict(zip(
        ["symbol","entry","qty","stop","target","entry_fee","opened_at"], r
    ))

def signal_seen(symbol, candle_time):
    with connect() as con:
        return con.execute(
            "SELECT 1 FROM signals WHERE symbol=? AND candle_time=?",
            (symbol, candle_time)
        ).fetchone() is not None

def save_signal(symbol, candle_time, score, rsi, created_at):
    with connect() as con:
        con.execute(
            "INSERT OR IGNORE INTO signals(symbol,candle_time,score,rsi,created_at) VALUES(?,?,?,?,?)",
            (symbol,candle_time,score,rsi,created_at)
        )

def open_position(symbol, entry, qty, stop, target, entry_fee, opened_at):
    cost = entry * qty + entry_fee
    with connect() as con:
        cash = con.execute("SELECT cash FROM state WHERE id=1").fetchone()[0]
        if cost > cash + 1e-9:
            return False
        con.execute("UPDATE state SET cash=cash-? WHERE id=1", (cost,))
        con.execute("""INSERT INTO positions
            (symbol,entry,qty,stop,target,entry_fee,opened_at)
            VALUES(?,?,?,?,?,?,?)""",
            (symbol,entry,qty,stop,target,entry_fee,opened_at))
    return True

def close_position(symbol, exit_price, exit_fee, reason, closed_at):
    with connect() as con:
        p = con.execute(
            "SELECT entry,qty,stop,target,entry_fee,opened_at FROM positions WHERE symbol=?",
            (symbol,)
        ).fetchone()
        if not p:
            return None
        entry, qty, stop, target, entry_fee, opened_at = p
        proceeds = exit_price * qty - exit_fee
        pnl = (exit_price-entry)*qty - entry_fee - exit_fee
        con.execute("UPDATE state SET cash=cash+?, realized_pnl=realized_pnl+? WHERE id=1",
                    (proceeds, pnl))
        con.execute("""INSERT INTO trades
            (symbol,entry,exit,qty,entry_fee,exit_fee,pnl,reason,opened_at,closed_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (symbol,entry,exit_price,qty,entry_fee,exit_fee,pnl,reason,opened_at,closed_at))
        con.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
    return pnl

def today_pnl(date_prefix):
    with connect() as con:
        r = con.execute(
            "SELECT COALESCE(SUM(pnl),0) FROM trades WHERE closed_at LIKE ?",
            (date_prefix + "%",)
        ).fetchone()
    return float(r[0])

def stats():
    with connect() as con:
        cash, rpnl = con.execute("SELECT cash,realized_pnl FROM state WHERE id=1").fetchone()
        count, wins, pnl = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(pnl>0),0), COALESCE(SUM(pnl),0) FROM trades"
        ).fetchone()
        gross_win = con.execute(
            "SELECT COALESCE(SUM(CASE WHEN pnl>0 THEN pnl ELSE 0 END),0) FROM trades"
        ).fetchone()[0]
        gross_loss = abs(con.execute(
            "SELECT COALESCE(SUM(CASE WHEN pnl<0 THEN pnl ELSE 0 END),0) FROM trades"
        ).fetchone()[0])
    pf = gross_win/gross_loss if gross_loss else (float("inf") if gross_win else 0)
    return cash, rpnl, count, wins, pnl, pf
