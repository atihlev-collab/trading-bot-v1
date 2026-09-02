# ==========================================
# Trading Bot V5 - CONFIG
# ==========================================

START_BALANCE = 100.0

SYMBOLS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "DOGEUSDT","ADAUSDT","LINKUSDT","AVAXUSDT","DOTUSDT",
    "TRXUSDT","TONUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "UNIUSDT","AAVEUSDT","NEARUSDT","APTUSDT","ARBUSDT",
    "OPUSDT","INJUSDT","SUIUSDT","SEIUSDT","HBARUSDT",
    "FILUSDT","ETCUSDT","ALGOUSDT","VETUSDT","ICPUSDT",
]

LOWER_TIMEFRAME = "15m"
HIGHER_TIMEFRAME = "1h"

CANDLE_LIMIT = 300
SCAN_SECONDS = 30

# ==========================================
# TREND
# ==========================================

EMA_FAST = 20
EMA_SLOW = 50
EMA_TREND = 200

# ==========================================
# RSI
# ==========================================

RSI_PERIOD = 14
RSI_MIN = 52
RSI_MAX = 67

# Не купуваме при прекалено разтеглен RSI.
RSI_HARD_MAX = 72

# ==========================================
# ATR / VOLATILITY
# ==========================================

ATR_PERIOD = 14

MIN_ATR_PERCENT = 0.0035
MAX_ATR_PERCENT = 0.025

# ==========================================
# VOLUME
# ==========================================

VOLUME_PERIOD = 20

# Минимален обем за BUY.
VOLUME_MULTIPLIER = 1.15

# Силен обем.
STRONG_VOLUME_RATIO = 1.50

# ==========================================
# MOMENTUM
# ==========================================

MIN_MOMENTUM = 0.0025
STRONG_MOMENTUM = 0.0050

# ==========================================
# TREND STRENGTH
# ==========================================

MIN_TREND_STRENGTH = 0.20
STRONG_TREND_STRENGTH = 0.40

# ==========================================
# CANDLE
# ==========================================

MAX_GREEN_CANDLE = 0.012

# Не купуваме след прекалено голяма свещ.
MAX_ENTRY_CANDLE = 0.010

# ==========================================
# SCORE
# ==========================================

BUY_SCORE = 85
WATCH_SCORE = 72
IGNORE_SCORE = 65

# BUY трябва да има минимум потвърждения.
MIN_BUY_CONFIRMATIONS = 6

# ==========================================
# RISK MANAGEMENT
# ==========================================

RISK_PER_TRADE = 0.0075

MAX_POSITION_PCT = 0.20
MAX_OPEN_POSITIONS = 3

DAILY_LOSS_LIMIT = 0.03

COOLDOWN_HOURS = 2

# ==========================================
# STOP / TAKE PROFIT
# ==========================================

ATR_STOP_MULT = 1.8

# 3R не е задължително оптимално.
# Ще го тестваме с backtest.
REWARD_RISK = 2.5

BREAK_EVEN_AT = 1.0

TRAILING_STOP = True
TRAILING_AT_R = 1.5
TRAILING_ATR = 1.5

# ==========================================
# COSTS
# ==========================================

FEE_RATE = 0.001
SLIPPAGE_RATE = 0.0005

# ==========================================
# REPORTING
# ==========================================

REPORT_INTERVAL_MINUTES = 30

LOG_SIGNALS = True
LOG_SKIPPED = False
LOG_POSITIONS = True

# ==========================================
# DATABASE
# ==========================================

DB_FILE = "trading_bot_v5.db"

# ==========================================
# BINANCE
# ==========================================

BASE_URL = "https://data-api.binance.vision"

REQUEST_TIMEOUT = 15
REQUEST_RETRIES = 3
RETRY_DELAY = 2

# ==========================================
# CACHE
# ==========================================

DATA_CACHE_SECONDS = 20

# ==========================================
# BACKTEST
# ==========================================

BACKTEST_LIMIT = 1000

BACKTEST_MIN_TRADES = 30

# Само ако стратегията показва положителна expectancy
# и приемлив drawdown.
REQUIRE_POSITIVE_EXPECTANCY = True

# Максимален допустим drawdown за приемане
# на дадена конфигурация.
MAX_BACKTEST_DRAWDOWN = 0.20
