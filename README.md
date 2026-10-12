# Trading Bot — research branch

This version is a clean test build, not a promise of guaranteed profit.

## Changes from the previous test
- Starting paper balance: 100 USDT
- Maximum simultaneous positions: 3
- Configured risk per trade: 0.75%
- Position value cap: 20%
- Higher-timeframe confirmation (1h)
- 15m trend + momentum + volume + MACD + ADX filters
- No trading on the still-forming candle
- Fees and slippage included
- Break-even and delayed trailing stop
- Paginated historical backtest with next-candle-open entries, fees/slippage, conservative same-candle stop priority, and drawdown marking
- Backtest runs are independent per symbol; aggregate P/L is not a real portfolio return

## Run
```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python backtest.py
python main.py
```

## What to judge
Do not judge the system from 5-20 trades. Track:
- Profit Factor
- Net P/L after fees
- Win rate
- Maximum drawdown
- Number of trades
- Stability across symbols and periods

The built-in backtest is a research tool, not proof of an edge. Do not enable live trading from an in-sample result alone. Validate on untouched out-of-sample data and walk-forward periods first.
