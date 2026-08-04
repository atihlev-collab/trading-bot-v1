import logging
import os

LOG_DIR = "logs"

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s | %(levelname)s | %(message)s",

    handlers=[

        logging.FileHandler(
            f"{LOG_DIR}/tradingbot.log"
        ),

        logging.StreamHandler(),

    ],

)

logger = logging.getLogger("TradingBotV3")


def info(message):
    logger.info(message)


def warning(message):
    logger.warning(message)


def error(message):
    logger.error(message)


def trade(message):
    logger.info(f"[TRADE] {message}")


def signal(message):
    logger.info(f"[SIGNAL] {message}")


def position(message):
    logger.info(f"[POSITION] {message}")