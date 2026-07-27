# Trading Bot V1 — Paper Trading

This version is deliberately unable to place real orders.

## What it does
- Virtual starting balance: 50 USDT
- Reads public Binance market data
- 15-minute candles
- BTC, ETH, SOL, BNB, XRP against USDT
- EMA 20/50 + RSI + volume + price momentum
- ATR stop
- 2:1 reward/risk target
- Simulated 0.10% fee per side and 0.05% slippage
- SQLite trade history
- No API keys
- No Telegram
- No leverage/futures

## Install
Python 3.10+ recommended.

Windows:
    py -m pip install -r requirements.txt
    py main.py

Linux/macOS:
    python3 -m pip install -r requirements.txt
    python3 main.py

Keep the bot running. The database `trading_bot.db` is created automatically.

## Reset the 30-day test
Stop the bot and delete `trading_bot.db`, then start it again.

## Important
Paper results do not guarantee live profitability. Real execution can differ due to
fees, spreads, slippage, liquidity, outages and market regime changes.
