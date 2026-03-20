import psutil

def get_system_telemetry():
    """ Gathers internal Pi health stats and returns a JSON-ready dictionary """
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp_c = int(f.read()) / 1000.0
    except Exception:
        temp_c = 0.0

    try:
        with open('/sys/devices/platform/soc/soc:firmware/get_throttled', 'r') as f:
            low_voltage = (f.read().strip() != '0') 
    except Exception:
        low_voltage = False

    return {
        "type": "TELEMETRY",
        "cpu_temp": round(temp_c, 1),
        "cpu_usage": psutil.cpu_percent(interval=None),
        "ram_usage": psutil.virtual_memory().percent,
        "low_power": low_voltage
    }