import sys
import time
import logging
import os
import traceback
from logging.handlers import RotatingFileHandler
from config import LOG_PREFIX, LOG_DIR, LOG_MAX_BYTES, LOG_BACKUP_COUNT

logger = logging.getLogger("ServerLogger")

def setup_logging():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    log_file = os.path.join(LOG_DIR, "system.log")
    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    formatter = logging.Formatter("[SERVER] [%(asctime)s] | %(message)s", datefmt="%H:%M:%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    sys.excepthook = global_crash_handler

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"{LOG_PREFIX} {ts} | {msg}")
    logger.info(msg)

def global_crash_handler(exc_type, exc_value, exc_tb):
    """ Catches any fatal crash in the app and saves it to the log file. """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    crash_report = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log(f"[CRITICAL SERVER CRASH]:\n{crash_report}")