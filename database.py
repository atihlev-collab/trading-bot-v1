import sqlite3
from datetime import datetime, timezone

from config import DB_FILE


def _connect():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def init_db():
    with _connect() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS trades(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL DEFAULT 'LONG',
                entry REAL NOT NULL,
                exit REAL NOT NULL,
                quantity REAL NOT NULL,
                pnl REAL NOT NULL,
                reason TEXT NOT NULL,
                quality TEXT DEFAULT '',
                confidence REAL DEFAULT 0,
                score REAL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            '''
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_created_at "
            "ON trades(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_symbol "
            "ON trades(symbol)"
        )


def save_trade(result):
    required = (
        "symbol",
        "entry",
        "exit",
        "quantity",
        "pnl",
        "reason",
    )

    for key in required:
        if key not in result:
            raise KeyError(f"Missing trade field: {key}")

    with _connect() as conn:
        conn.execute(
            '''
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
            ''',
            (
                result["symbol"],
                result.get("side", "LONG"),
                float(result["entry"]),
                float(result["exit"]),
                float(result["quantity"]),
                float(result["pnl"]),
                result["reason"],
                result.get("quality", ""),
                float(result.get("confidence", 0) or 0),
                float(result.get("score", 0) or 0),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def load_stats():
    with _connect() as conn:
        row = conn.execute(
            '''
            SELECT
                COUNT(*) AS trades,
                COALESCE(
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END),
                    0
                ) AS wins,
                COALESCE(
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END),
                    0
                ) AS losses,
                COALESCE(SUM(pnl), 0) AS pnl,
                COALESCE(
                    SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END),
                    0
                ) AS gross_profit,
                COALESCE(
                    SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END),
                    0
                ) AS gross_loss
            FROM trades
            '''
        ).fetchone()

    trades, wins, losses, pnl, gross_profit, gross_loss = row

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (999.0 if gross_profit > 0 else 0.0)
    )

    return {
        "trades": int(trades or 0),
        "wins": int(wins or 0),
        "losses": int(losses or 0),
        "win_rate": round(
            (wins / trades * 100) if trades else 0,
            1,
        ),
        "pnl": round(float(pnl or 0), 4),
        "gross_profit": round(float(gross_profit or 0), 4),
        "gross_loss": round(float(gross_loss or 0), 4),
        "profit_factor": round(float(profit_factor), 2),
    }


if __name__ == "__main__":
    init_db()
    print(load_stats())
