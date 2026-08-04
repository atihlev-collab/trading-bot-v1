import sqlite3
from datetime import datetime

from config import DB_FILE

DB_NAME = DB_FILE

# ==========================================
# INIT
# ==========================================

def init_db():

    conn = sqlite3.connect(DB_NAME)

    cur = conn.cursor()

    cur.execute(
        """
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
        """
    )

    conn.commit()

    conn.close()


# ==========================================
# SAVE TRADE
# ==========================================

def save_trade(result):

    conn = sqlite3.connect(DB_NAME)

    cur = conn.cursor()

    cur.execute(

        """
        INSERT INTO trades(

            symbol,
            side,
            entry,
            exit,
            quantity,
            pnl,
            reason,
            quality,
            confidence,
            score,
            created_at

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?)

        """,

        (

            result["symbol"],

            "LONG",

            result["entry"],

            result["exit"],

            result["quantity"],

            result["pnl"],

            result["reason"],

            result.get("quality", ""),

            result.get("confidence", 0),

            result.get("score", 0),

            datetime.utcnow().isoformat(),

        )

    )

    conn.commit()

    conn.close()


# ==========================================
# LOAD STATS
# ==========================================

def load_stats():

    conn = sqlite3.connect(DB_NAME)

    cur = conn.cursor()

    cur.execute(

        """
        SELECT

        COUNT(*),

        SUM(
            CASE
            WHEN pnl>0
            THEN 1
            ELSE 0
            END
        ),

        SUM(pnl)

        FROM trades

        """

    )

    row = cur.fetchone()

    conn.close()

    trades = row[0] or 0

    wins = row[1] or 0

    pnl = row[2] or 0

    if trades == 0:
        winrate = 0

    else:
        winrate = round(
            wins /
            trades *
            100,
            1,
        )

    return {

        "trades": trades,

        "wins": wins,

        "win_rate": winrate,

        "pnl": pnl,

    }