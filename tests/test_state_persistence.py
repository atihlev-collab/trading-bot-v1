import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import database
from paper_trader import PaperTrader


class PaperAccountPersistenceTests(unittest.TestCase):
    def test_balance_and_open_position_survive_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "paper-trader.sqlite")
            with patch.object(database, "DB_FILE", db_path):
                first = PaperTrader()
                first.balance = 81.25
                first.realized_pnl = -1.75
                first.total_trades = 1
                first.wins = 0
                first.losses = 1
                first.daily_loss = 1.75
                opened_at = datetime(2026, 10, 12, 12, 30, tzinfo=timezone.utc)
                first.positions = {
                    "BTCUSDT": {
                        "entry": 100.0,
                        "quantity": 0.1,
                        "initial_quantity": 0.1,
                        "value": 10.0,
                        "stop": 95.0,
                        "take": 112.5,
                        "initial_risk": 0.5,
                        "atr": 2.0,
                        "highest": 101.0,
                        "last_price": 100.5,
                        "break_even": False,
                        "partial_taken": False,
                        "partial_realized_pnl": 0.0,
                        "entry_fee": 0.01,
                        "opened": opened_at,
                        "score": 90,
                        "confidence": 88,
                        "quality": "A",
                    }
                }
                first._persist_state()

                restored = PaperTrader()

                self.assertAlmostEqual(restored.balance, 81.25)
                self.assertAlmostEqual(restored.realized_pnl, -1.75)
                self.assertEqual(restored.total_trades, 1)
                self.assertEqual(restored.losses, 1)
                self.assertIn("BTCUSDT", restored.positions)
                self.assertAlmostEqual(restored.positions["BTCUSDT"]["stop"], 95.0)
                self.assertIsInstance(restored.positions["BTCUSDT"]["opened"], datetime)
                self.assertEqual(
                    restored.positions["BTCUSDT"]["opened"],
                    opened_at,
                )


if __name__ == "__main__":
    unittest.main()
