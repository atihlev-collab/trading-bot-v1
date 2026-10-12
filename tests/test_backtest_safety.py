import unittest

import pandas as pd

from backtest import (
    add_higher_timeframe,
    calculate_position_size,
    close_position,
    valid_entry,
)


class BacktestSafetyTests(unittest.TestCase):
    def test_higher_timeframe_uses_only_a_closed_hour(self):
        low = pd.DataFrame({
            "close_time": pd.to_datetime([
                "2026-01-01T10:14:59.999Z",
                "2026-01-01T10:29:59.999Z",
                "2026-01-01T10:44:59.999Z",
                "2026-01-01T10:59:59.999Z",
            ], utc=True),
            "close": [101.0, 102.0, 103.0, 104.0],
        })
        high = pd.DataFrame({
            "close_time": pd.to_datetime([
                "2026-01-01T09:59:59.999Z",
                "2026-01-01T10:59:59.999Z",
            ], utc=True),
            "close": [100.0, 110.0],
            "ema20": [99.0, 108.0],
            "ema50": [98.0, 105.0],
            "ema200": [95.0, 100.0],
        })

        merged = add_higher_timeframe(low, high)
        self.assertEqual(list(merged["htf_close"]), [100.0, 100.0, 100.0, 110.0])

    def test_entry_requires_configured_minimum_momentum(self):
        row = pd.Series({
            "htf_close": 110.0,
            "htf_ema20": 108.0,
            "htf_ema50": 105.0,
            "htf_ema200": 100.0,
            "close": 110.0,
            "ema20": 108.0,
            "ema50": 105.0,
            "ema200": 100.0,
            "rsi": 60.0,
            "atr": 1.0,
            "atr_pct": 1.0 / 110.0,
            "mom": 0.006,
            "vol_ma": 100.0,
            "volume_ratio": 1.8,
            "volume": 180.0,
            "trend": 0.5,
            "macd_hist": 2.0,
            "macd_hist_prev": 1.0,
            "adx": 30.0,
            "candle_body": 0.005,
        })
        self.assertTrue(valid_entry(row))
        row["mom"] = 0.001
        self.assertFalse(valid_entry(row))

    def test_position_size_respects_value_cap(self):
        qty = calculate_position_size(100.0, 100.0, 98.0)
        self.assertAlmostEqual(qty, 0.2, places=7)
        self.assertLessEqual(qty * 100.0, 20.0)

    def test_close_position_accounts_for_exit_fee_and_slippage(self):
        position = {"entry": 100.0, "quantity": 1.0}
        balance, pnl, exit_price = close_position(0.0, position, 110.0)
        self.assertAlmostEqual(exit_price, 109.945, places=6)
        self.assertAlmostEqual(pnl, 9.735055, places=5)
        self.assertAlmostEqual(balance, 109.835055, places=5)


if __name__ == "__main__":
    unittest.main()
