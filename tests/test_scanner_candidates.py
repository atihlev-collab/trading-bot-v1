import unittest
from unittest.mock import patch

import pandas as pd

import scanner


def _prepared_frame(*, bullish=True, current_close=100.2, current_candle=0.002):
    if bullish:
        close = [100.0, current_close]
        ema20, ema50, ema200 = [99.0, 99.2], [98.0, 98.2], [95.0, 95.0]
    else:
        close = [94.0, 94.0]
        ema20, ema50, ema200 = [97.0, 97.0], [98.0, 98.0], [100.0, 100.0]

    return pd.DataFrame({
        "close": close,
        "open": [99.8, current_close / (1 + current_candle)],
        "volume": [180.0, 180.0],
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "atr": [1.0, 1.0],
        "atr_pct": [0.01, 0.01],
        "rsi": [60.0, 60.0],
        "momentum": [0.006, 0.006],
        "volume_ma": [100.0, 100.0],
        "volume_ratio": [1.8, 1.8],
        "trend_strength": [0.5, 0.5],
        "macd_hist": [1.0, 2.0],
        "adx": [30.0, 30.0],
        "candle_body": [0.005, current_candle],
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
