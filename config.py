# Trading Bot V1 - PAPER TRADING ONLY

START_BALANCE = 50.0  # virtual USDT
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
INTERVAL = "15m"
CANDLE_LIMIT = 250

# Strategy
EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14
ATR_PERIOD = 14
RSI_BUY_MIN = 48
RSI_BUY_MAX = 68
VOLUME_MULTIPLIER = 1.05

# Risk
RISK_PER_TRADE = 0.01       # 1% of current equity at stop
MAX_POSITION_PCT = 0.30     # max 30% of cash in one position
MAX_OPEN_POSITIONS = 2
ATR_STOP_MULT = 1.5
REWARD_RISK = 2.0
DAILY_LOSS_LIMIT_PCT = 0.03

# Paper execution assumptions
FEE_RATE = 0.001             # 0.10% per side
SLIPPAGE_RATE = 0.0005       # 0.05% simulated slippage per side

SCAN_SECONDS = 60
DB_FILE = "/data/trading_bot.db"

# Public market-data-only endpoint; no API key and no trading permissions.
BASE_URL = "https://data-api.binance.vision"
