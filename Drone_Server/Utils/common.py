import sys, time
from config import LOG_PREFIX

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"{LOG_PREFIX} {ts} | {msg}")
    sys.stdout.flush()