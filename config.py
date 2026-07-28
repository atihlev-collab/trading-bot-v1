# ==============================
# Trading Bot V2 - PAPER TRADING
# ==============================

# Account
START_BALANCE = 50.0

# Symbols
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
]

# Timeframe
INTERVAL = "15m"
CANDLE_LIMIT = 300
SCAN_SECONDS = 30

# ==============================
# Strategy
# ==============================

EMA_FAST = 20
EMA_SLOW = 50
EMA_TREND = 200

RSI_PERIOD = 14
RSI_MIN = 45
RSI_MAX = 62

ATR_PERIOD = 14

VOLUME_PERIOD = 20
VOLUME_MULTIPLIER = 1.20

MIN_SCORE = 5

# Price filters
MAX_GREEN_CANDLE = 0.025      # 2.5%
MIN_ATR_PERCENT = 0.003        # 0.3%
MAX_ATR_PERCENT = 0.050        # 5%

# ==============================
# Risk
# ==============================

RISK_PER_TRADE = 0.01

MAX_POSITION_PCT = 0.25

MAX_OPEN_POSITIONS = 2

ATR_STOP_MULT = 1.8

REWARD_RISK = 2.5

BREAK_EVEN_AT = 1.0

TRAILING_STOP = True

TRAILING_ATR = 1.2

COOLDOWN_CANDLES = 2

DAILY_LOSS_LIMIT_PCT = 0.03

# ==============================
# Execution
# ==============================

FEE_RATE = 0.001
SLIPPAGE_RATE = 0.0005

# ==============================
# Database
# ==============================

DB_FILE = "/data/trading_bot_v2.db"

# ==============================
# Market Data
# ==============================

BASE_URL = "https://data-api.binance.vision"

REQUEST_TIMEOUT = 15

REQUEST_RETRIES = 3

RETRY_DELAY = 2

# ==============================
# Reports
# ==============================

REPORT_INTERVAL_MINUTES = 30

LOG_SIGNALS = True

LOG_SKIPPED_SIGNALS = False

LOG_POSITION_UPDATES = True
