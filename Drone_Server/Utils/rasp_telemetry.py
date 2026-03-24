import psutil, pigpio, smbus2, bme280
from config import WATER_DETECTION_PIN

pi = pigpio.pi()

if pi.connected:
    pi.set_mode(WATER_DETECTION_PIN, pigpio.INPUT)
    pi.set_pull_up_down(WATER_DETECTION_PIN, pigpio.PUD_UP)

I2C_PORT = 1
BME280_ADDRESS = 0x76
try:
    bus = smbus2.SMBus(I2C_PORT)
    bme_calibration = bme280.load_calibration_params(bus, BME280_ADDRESS)
    bme_connected = True
except Exception as e:
    print(f"BME280 ERROR: {e}")
    bme_connected = False

def get_system_telemetry(engine_manager):
    """ Gathers internal Drone telemetry and returns a JSON-ready dictionary """
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

    leak_detected = False
    if pi.connected:
        leak_detected = (pi.read(WATER_DETECTION_PIN) == 0)

    engine_data = engine_manager.get_telemetry_data() if engine_manager else {}

    hull_temp = 0.0
    hull_hum = 0.0
    if bme_connected:
        try:
            bme_data = bme280.sample(bus, BME280_ADDRESS, bme_calibration)
            hull_temp = bme_data.temperature
            hull_hum = bme_data.humidity
        except Exception as e:
            print(f"BME280 READ ERROR: {e}")
            pass

    return {
        "type": "TELEMETRY",
        "cpu_temp": round(temp_c, 1),
        "cpu_usage": psutil.cpu_percent(interval=None),
        "ram_usage": psutil.virtual_memory().percent,
        "low_power": low_voltage,
        "leak_detected": leak_detected,
        "front_power": engine_data.get("front_power_pct", 0),
        "rear_power": engine_data.get("rear_power_pct", 0),
        "hull_temp": round(hull_temp, 1),
        "hull_hum": round(hull_hum, 1)
    }