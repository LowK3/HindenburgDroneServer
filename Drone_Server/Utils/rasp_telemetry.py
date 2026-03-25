import psutil, pigpio, smbus2, bme280, math
from mpu6050 import mpu6050
from config import WATER_DETECTION_PIN, I2C_PORT, BME280_ADDRESS, GYRO_ADDRESS
from Utils.common import log

pi = pigpio.pi()

# Initialize water detection pin
if pi.connected:
    pi.set_mode(WATER_DETECTION_PIN, pigpio.INPUT)
    pi.set_pull_up_down(WATER_DETECTION_PIN, pigpio.PUD_UP)

# Start BME280 sensor
try:
    bus = smbus2.SMBus(I2C_PORT)
    bme_calibration = bme280.load_calibration_params(bus, BME280_ADDRESS)
    bme_connected = True
    log("BME280 Sensor Connected successfully!")
except Exception as e:
    log(f"BME280 Init Error: {e}")
    bme_connected = False

# Start Gyroscope GY-6500
try:
    imu = mpu6050(GYRO_ADDRESS) 
    imu_connected = True
    log("Gyro GY-6500 Sensor Connected successfully!")
except Exception as e:
    log(f"Gyro GY-6500 Init Error: {e}")
    imu_connected = False

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
            print(f"BME280 Read Error: {e}")
            pass

    pitch = 0.0
    roll = 0.0
    if imu_connected:
        try:
            accel = imu.get_accel_data()
            x, y, z = accel['x'], accel['y'], accel['z']
            
            # Convert raw G-forces into degrees of tilt
            pitch = math.degrees(math.atan2(y, math.sqrt(x*x + z*z)))
            roll = math.degrees(math.atan2(-x, z))
        except Exception as e:
            print(f"Gyro GY-6500 Read Error: {e}")
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
        "hull_hum": round(hull_hum, 1),
        "pitch": round(pitch, 1),
        "roll": round(roll, 1)
    }