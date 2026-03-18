import sys, time, select, logging, os
from logging.handlers import RotatingFileHandler
from config import LOG_PREFIX

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "system.log")

logger = logging.getLogger("ServerLogger")
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(
    LOG_FILE, 
    maxBytes = 5 * 1024 * 1024, 
    backupCount = 2
)

formatter = logging.Formatter("[SERVER] [%(asctime)s] | %(message)s", datefmt="%H:%M:%S")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"{LOG_PREFIX} {ts} | {msg}")
    logger.info(msg)

def check_keyboard(shutdown_event):
    """ Non-blocking check for 'q' key in stdin. Sets the given shutdown_event if pressed. """
    try:
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            key = sys.stdin.read(1)
            if key.lower() == "q":
                log("Shutdown key 'q' pressed")
                shutdown_event.set()
    except Exception:
        # ignore any stdin/select failures silently
        pass

def global_crash_handler(exc_type, exc_value, exc_tb):
    """ Catches any fatal crash in the app and saves it to the log file. """
    # Ignore normal manual shutdowns (like pressing Ctrl+C)
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
        
    crash_report = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log(f"[CRITICAL SERVER CRASH]:\n{crash_report}")

sys.excepthook = global_crash_handler