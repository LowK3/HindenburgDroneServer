import psutil, pigpio, smbus2, bme280, math, time, traceback
from mpu6050 import mpu6050
from config import WATER_DETECTION_PIN, I2C_PORT, BME280_ADDRESS, GYRO_ADDRESS, RECONNECT_COOLDOWN
from Utils.common import log

last_reconnect_time = 0

pi = pigpio.pi()
water_connected = False
bme_connected = False
imu_connected = False

bus = None
bme_calibration = None
imu = None

def try_init_hardware():
    """ Attempts to connect to all offline sensors. """
    global water_connected, bme_connected, imu_connected, bus, bme_calibration, imu

    # Start water detection sensor
    if not water_connected and pi.connected:
        try:
            pi.set_mode(WATER_DETECTION_PIN, pigpio.INPUT)
            pi.set_pull_up_down(WATER_DETECTION_PIN, pigpio.PUD_UP)
            water_connected = True
        except Exception as e:
            log(f"Water Sensor Init Error: {e}")

    # Start BME280 sensor
    if not bme_connected:
        try:
            bus = smbus2.SMBus(1)
            bme_calibration = bme280.load_calibration_params(bus, 0x76)
            bme_connected = True
        except Exception:
            pass

    # Start Gyroscope GY-6500
    if not imu_connected:
        try:
            imu = mpu6050(0x68)
            imu_connected = True
        except Exception:
            pass

try_init_hardware()

def get_system_telemetry(engine_manager):
    """ Gathers internal Drone telemetry and returns a JSON-ready dictionary """
    global water_connected, bme_connected, imu_connected, last_reconnect_time

    if not (water_connected and bme_connected and imu_connected):
        if time.time() - last_reconnect_time > RECONNECT_COOLDOWN:
            try_init_hardware()
            last_reconnect_time = time.time()

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
    if water_connected:
        try:
            leak_detected = (pi.read(WATER_DETECTION_PIN) == 0)
        except Exception:
            water_connected = False

    hull_temp = 0.0
    hull_hum = 0.0
    if bme_connected:
        try:
            bme_data = bme280.sample(bus, BME280_ADDRESS, bme_calibration)
            hull_temp = bme_data.temperature
            hull_hum = bme_data.humidity
        except Exception as e:
            bme_connected = False

    pitch = 0.0
    roll = 0.0
    if imu_connected:
        try:
            accel = imu.get_accel_data()
            x, y, z = accel['x'], accel['y'], accel['z']
            # Convert raw G-forces into degrees of tilt
            pitch = math.degrees(math.atan2(y, math.sqrt(x*x + z*z)))
            roll = math.degrees(math.atan2(-x, z))
        except Exception:
            imu_connected = False

    engine_data = engine_manager.get_telemetry_data() if engine_manager else {}

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
        "hull_hum": round(hull_hum, 1),
        "pitch": round(pitch, 1),
        "roll": round(roll, 1)
    }