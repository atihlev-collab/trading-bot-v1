import unittest
from unittest.mock import patch

import pandas as pd

import scanner


def _prepared_frame(*, bullish=True, current_close=100.2, current_candle=0.002):
    size = 220
    if bullish:
        closes = [100.0] * size
        closes[-1] = current_close
        ema20, ema50, ema200 = [99.0] * size, [98.0] * size, [95.0] * size
    else:
        closes = [94.0] * size
        ema20, ema50, ema200 = [97.0] * size, [98.0] * size, [100.0] * size

    opens = [value / 1.005 for value in closes]
    opens[-1] = current_close / (1 + current_candle)
    return pd.DataFrame({
        "close": closes,
        "open": opens,
        "volume": [180.0] * size,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "atr": [1.0] * size,
        "atr_pct": [0.01] * size,
        "rsi": [60.0] * size,
        "momentum": [0.006] * size,
        "volume_ma": [100.0] * size,
        "volume_ratio": [1.8] * size,
        "trend_strength": [0.5] * size,
        "macd_hist": [2.0] * size,
        "adx": [30.0] * size,
        "candle_body": [0.005] * (size - 1) + [current_candle],
    })

class ScannerCandidateTests(unittest.TestCase):
    def _analyze(self, low, high):
        with patch.object(
            scanner,
            "get_multi_tf",
            return_value={"15m": pd.DataFrame(), "1h": pd.DataFrame()},
        ), patch.object(scanner, "_prepare", side_effect=[low, high]):
            return scanner.analyze_symbol("BTCUSDT")

    def test_uses_latest_closed_candle_not_second_to_last(self):
        low = _prepared_frame(current_close=100.2, current_candle=0.002)
        high = _prepared_frame(current_close=101.0, current_candle=0.002)

        result = self._analyze(low, high)

        self.assertIsNotNone(result)
        self.assertEqual(result["close"], 100.2)
        self.assertEqual(result["signal"], "BUY")

    def test_near_setup_is_kept_as_watch_when_trend_filter_blocks_buy(self):
        low = _prepared_frame(bullish=False, current_close=94.0, current_candle=0.005)
        high = _prepared_frame(bullish=False, current_close=94.0, current_candle=0.005)

        result = self._analyze(low, high)

        self.assertIsNotNone(result)
        self.assertEqual(result["signal"], "WATCH")
        self.assertFalse(result["htf_bull"])
        self.assertFalse(result["ltf_bull"])

    def test_small_red_pullback_is_not_rejected_only_for_candle_color(self):
        low = _prepared_frame(current_close=99.8, current_candle=-0.002)
        high = _prepared_frame(current_close=100.2, current_candle=0.002)

        result = self._analyze(low, high)

        self.assertIsNotNone(result)
        self.assertEqual(result["signal"], "BUY")
        self.assertLess(result["candle_body"], 0)


if __name__ == "__main__":
    unittest.main()
