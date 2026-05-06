import psutil
import smbus2
import bme280
import pigpio
import math
import time
import threading
from mpu6050 import mpu6050
from config import (
    WATER_DETECTION_PIN, I2C_PORT, BME_ADDRESS, IMU_ADDRESS, SENSOR_RECONNECT_COOLDOWN,
    POLLING_RATE, SMOOTHING_FACTOR
)
from Utils.common import log

class TelemetryGatherer:
    """Asynchronously polls hardware sensors to prevent blocking the network loop."""
    def __init__(self, thruster_mgr, gpio_connection: pigpio.pi):
        self.thruster = thruster_mgr
        self.gpio = gpio_connection
        self.bus = None
        self.bme_calibration = None
        self.imu = None
        
        self.water_connected = False
        self.bme_connected = False
        self.imu_connected = False
        self.last_reconnect_time = 0
        self.last_slow_poll_time = 0

        self.pitch_filtered = 0.0
        self.roll_filtered = 0.0
        
        self._lock = threading.Lock()
        self._cached_state = self._default_state()
        self._running = False

    def _default_state(self):
        return {
            "type": "TELEMETRY",
            "cpu_temp": None,
            "cpu_usg": None,
            "ram_usg": None,
            "low_pwr": False,
            "leak_detected": False,
            "front_pwr": None,
            "rear_pwr": None,
            "hull_temp": None,
            "hull_hum": None,
            "hull_press": None,
            "pitch": 0.0,
            "roll": 0.0
        }

    def start(self):
        self._running = True
        self._init_hardware()
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def get_state(self):
        with self._lock:
            return self._cached_state.copy()

    def _init_hardware(self):
        """ Attempts to connect to all offline sensors. """
        if not self.water_connected and self.gpio.connected:
            try:
                self.gpio.set_mode(WATER_DETECTION_PIN, pigpio.INPUT)
                self.gpio.set_pull_up_down(WATER_DETECTION_PIN, pigpio.PUD_UP)
                self.water_connected = True
            except Exception as e:
                log(f"Water Sensor Init Error: {e}")

        if not self.bme_connected:
            try:
                self.bus = smbus2.SMBus(I2C_PORT)
                self.bme_calibration = bme280.load_calibration_params(self.bus, BME_ADDRESS)
                self.bme_connected = True
            except Exception as e:
                log(f"BME280 Init Error: {e}")

        if not self.imu_connected:
            try:
                self.imu = mpu6050(IMU_ADDRESS)
                self.imu_connected = True
            except Exception as e:
                log(f"Gyro Init Error: {e}")

    def _poll_loop(self):
        while self._running:
            if not (self.water_connected and self.bme_connected and self.imu_connected):
                if time.time() - self.last_reconnect_time > SENSOR_RECONNECT_COOLDOWN:
                    self._init_hardware()
                    self.last_reconnect_time = time.time()

            state = self._cached_state.copy()
            self._poll_imu(state)
            self._poll_thrusters(state)

            current_time = time.time()
            if current_time - self.last_slow_poll_time >= 1.0:
                self._poll_system_stats(state)
                self._poll_bme(state)
                self._poll_water_sensor(state)
                self.last_slow_poll_time = current_time

            with self._lock:
                self._cached_state = state
            
            time.sleep(POLLING_RATE)

    def _poll_system_stats(self, state: dict):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                state["cpu_temp"] = round(int(f.read()) / 1000.0, 1)
        except IOError:
            pass

        try:
            with open("/sys/devices/platform/soc/soc:firmware/get_throttled", "r") as f:
                state["low_pwr"] = (f.read().strip() != "0")
        except IOError:
            pass

        state["cpu_usg"] = psutil.cpu_percent(interval=None)
        state["ram_usg"] = psutil.virtual_memory().percent

    def _poll_water_sensor(self, state: dict):
        if self.water_connected:
            try:
                state["leak_detected"] = (self.gpio.read(WATER_DETECTION_PIN) == 0)
            except pigpio.error:
                self.water_connected = False

    def _poll_bme(self, state: dict):
        if self.bme_connected:
            try:
                bme_data = bme280.sample(self.bus, BME_ADDRESS, self.bme_calibration)
                state["hull_temp"] = round(bme_data.temperature, 1)
                state["hull_hum"] = round(bme_data.humidity, 1)
                state["hull_press"] = round(bme_data.pressure, 1)
            except Exception:
                self.bme_connected = False

    def _poll_imu(self, state: dict):
        if self.imu_connected:
            try:
                accel = self.imu.get_accel_data()
                x, y, z = accel['x'], accel['y'], accel['z']

                # Invert axes as needed to match the physical orientation of the sensor on the drone
                raw_pitch = math.degrees(math.atan2(-y, math.sqrt(x*x + z*z)))
                raw_roll = math.degrees(math.atan2(-x, z))

                self.pitch_filtered = (SMOOTHING_FACTOR * raw_pitch) + ((1.0 - SMOOTHING_FACTOR) * self.pitch_filtered)
                self.roll_filtered = (SMOOTHING_FACTOR * raw_roll) + ((1.0 - SMOOTHING_FACTOR) * self.roll_filtered)

                state["pitch"] = round(self.pitch_filtered, 1)
                state["roll"] = round(self.roll_filtered, 1)
            except Exception:
                self.imu_connected = False

    def _poll_thrusters(self, state: dict):
        thruster_data = self.thruster.get_telemetry_data() if self.thruster else {}
        state["front_pwr"] = thruster_data.get("front_pwr_pct", 0)
        state["rear_pwr"] = thruster_data.get("rear_pwr_pct", 0)

    def stop(self):
        self._running = False

