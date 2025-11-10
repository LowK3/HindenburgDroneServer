import sys, time, select
from config import LOG_PREFIX

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"{LOG_PREFIX} {ts} | {msg}")
    sys.stdout.flush()

def check_keyboard(self):
        """Called frequently (including during streaming) so 'q' works."""
        try:
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            if dr:
                key = sys.stdin.read(1)
                if key.lower() == "q":
                    log("Shutdown key 'q' pressed.")
                    self.request_shutdown()
        except Exception:
            # ignore stdin issues
            pass