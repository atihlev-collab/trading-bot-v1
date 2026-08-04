# ==========================================
# Trading Bot V3
# CONFIG
# ==========================================

START_BALANCE = 50.0

# ==========================================
# Symbols
# ==========================================

SYMBOLS = [

    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",

    "DOGEUSDT",
    "ADAUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "DOTUSDT",

    "TRXUSDT",
    "TONUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "ATOMUSDT",

    "UNIUSDT",
    "AAVEUSDT",
    "NEARUSDT",
    "APTUSDT",
    "ARBUSDT",

    "OPUSDT",
    "INJUSDT",
    "SUIUSDT",
    "SEIUSDT",
    "HBARUSDT",

    "FILUSDT",
    "ETCUSDT",
    "ALGOUSDT",
    "VETUSDT",
    "ICPUSDT",

]

# ==========================================
# Timeframes
# ==========================================

LOWER_TIMEFRAME = "15m"

HIGHER_TIMEFRAME = "1h"

CANDLE_LIMIT = 300

SCAN_SECONDS = 30

# ==========================================
# EMA
# ==========================================

EMA_FAST = 20

EMA_SLOW = 50

EMA_TREND = 200

# ==========================================
# RSI
# ==========================================

RSI_PERIOD = 14

RSI_MIN = 48

RSI_MAX = 65

# ==========================================
# ATR
# ==========================================

ATR_PERIOD = 14

MIN_ATR_PERCENT = 0.004

MAX_ATR_PERCENT = 0.040

# ==========================================
# Volume
# ==========================================

VOLUME_PERIOD = 20

VOLUME_MULTIPLIER = 1.15

# ==========================================
# Momentum
# ==========================================

MIN_MOMENTUM = 0.004

MIN_TREND_STRENGTH = 0.30

MAX_GREEN_CANDLE = 0.015

# ==========================================
# Signal Ranking
# ==========================================

BUY_SCORE = 90

WATCH_SCORE = 80

IGNORE_SCORE = 79

# ==========================================
# Risk
# ==========================================

RISK_PER_TRADE = 0.01

MAX_POSITION_PCT = 0.20

MAX_OPEN_POSITIONS = 2

DAILY_LOSS_LIMIT = 0.03

COOLDOWN_HOURS = 2

# ==========================================
# Stops
# ==========================================

ATR_STOP_MULT = 2.0

REWARD_RISK = 3.0

BREAK_EVEN_AT = 1.0

TRAILING_STOP = True

TRAILING_ATR = 1.5

# ==========================================
# Fees
# ==========================================

FEE_RATE = 0.001

SLIPPAGE_RATE = 0.0005

# ==========================================
# Reports
# ==========================================

REPORT_INTERVAL_MINUTES = 30

LOG_SIGNALS = True

LOG_SKIPPED = False

LOG_POSITIONS = True

# ==========================================
# Database
# ==========================================

DB_FILE = "/data/trading_bot_v3.db"

# ==========================================
# Binance
# ==========================================

BASE_URL = "https://data-api.binance.vision"

REQUEST_TIMEOUT = 15

REQUEST_RETRIES = 3

RETRY_DELAY = 2
