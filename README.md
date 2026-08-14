# Trading Bot V4

This version is a clean test build, not a promise of guaranteed profit.

## Changes from the previous test
- Starting paper balance: 100 USDT
- Maximum simultaneous positions: 5
- Risk per trade: 1%
- Position value cap: 20%
- Higher-timeframe confirmation (1h)
- 15m trend + momentum + volume + MACD + ADX filters
- No trading on the still-forming candle
- Fees and slippage included
- Break-even and delayed trailing stop
- Historical backtest included

## Run
```bash
pip install -r requirements.txt
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

A backtest result is not a guarantee of future performance.
