import sys, time, select
from config import LOG_PREFIX

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"{LOG_PREFIX} {ts} | {msg}")
    sys.stdout.flush()

def check_keyboard(shutdown_event):
    """
    Non-blocking check for 'q' key in stdin.
    Sets the given shutdown_event if pressed.
    """
    try:
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            key = sys.stdin.read(1)
            if key.lower() == 'q':
                log("Shutdown key 'q' pressed")
                shutdown_event.set()
    except Exception:
        # ignore any stdin/select failures silently
        pass