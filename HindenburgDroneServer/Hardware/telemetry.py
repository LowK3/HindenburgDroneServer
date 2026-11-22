import psutil
import smbus2
import bme280
import pigpio
import math
import time
import threading
import statistics
from typing import Callable
from collections import deque
from mpu6050 import mpu6050
from config import (
    WATER_DETECTION_PIN, I2C_PORT, BME_ADDRESS, IMU_ADDRESS, SENSOR_RECONNECT_COOLDOWN,
    SMOOTHING_FACTOR, IMU_POLL_INTERVAL, THRUSTER_POLL_INTERVAL, LEAK_POLL_INTERVAL, 
    ENV_POLL_INTERVAL, CPU_TEMP_PATH, CPU_TEMP_SCALE, THROTTLED_FLAGS_PATH, TELEMETRY_LOOP_SLEEP
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
        self._last_imu_poll = 0.0
        self._last_thruster_poll = 0.0
        self._last_leak_poll = 0.0
        self._last_environment_poll = 0.0

        self.pitch_filtered = 0.0
        self.roll_filtered = 0.0
        self.pitch_buffer = deque(maxlen=5)
        self.roll_buffer = deque(maxlen=5)
        
        self._lock = threading.Lock()
        self._running = False
        self._update_callback = None

        self._imu_state = {
            "pitch": None,
            "roll": None
        }

        self._leak_state = {
            "leak_detected": None
        }

        self._environment_state = {
            "cpu_temp": None,
            "cpu_usg": None,
            "ram_usg": None,
            "low_pwr": None,
            "hull_temp": None,
            "hull_hum": None,
            "hull_press": None
        }

        self._thruster_state = {
            "front_pwr": None,
            "rear_pwr": None
        }

    def start(self):
        if self._running:
            return

        self._running = True
        self._init_hardware()
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def get_imu(self):
        with self._lock:
            return self._imu_state.copy()

    def get_leak(self):
        with self._lock:
            return self._leak_state.copy()

    def get_environment(self):
        with self._lock:
            return self._environment_state.copy()

    def get_thrusters(self):
        with self._lock:
            return self._thruster_state.copy()

    def set_update_callback(self, callback: Callable[[str], None]):
        """Registers a callback for telemetry category updates."""
        self._update_callback = callback

    def _notify_update(self, category: str):
        """Notifies the registered callback that a category was updated."""
        if self._update_callback is not None:
            try:
                self._update_callback(category)
            except Exception as e:
                log(f"Telemetry update callback error ({category}): {e}")

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
                if self.bus is not None:
                    self.bus.close()
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
        """Polls each telemetry category at its configured interval."""
        while self._running:
            current_time = time.monotonic()

            # Reconnect disconnected sensors
            if not (self.water_connected and self.bme_connected and self.imu_connected):
                if current_time - self.last_reconnect_time >= SENSOR_RECONNECT_COOLDOWN:
                    self._init_hardware()
                    self.last_reconnect_time = current_time

            # IMU: 200 Hz
            if current_time - self._last_imu_poll >= IMU_POLL_INTERVAL:
                with self._lock:
                    state = self._imu_state.copy()

                self._poll_imu(state)

                with self._lock:
                    self._imu_state = state

                self._notify_update("IMU")
                self._last_imu_poll = current_time

            # Thrusters: 20 Hz
            if current_time - self._last_thruster_poll >= THRUSTER_POLL_INTERVAL:
                with self._lock:
                    state = self._thruster_state.copy()

                self._poll_thrusters(state)

                with self._lock:
                    self._thruster_state = state

                self._notify_update("THRUSTERS")
                self._last_thruster_poll = current_time

            # Leak sensor: 10 Hz
            if current_time - self._last_leak_poll >= LEAK_POLL_INTERVAL:
                with self._lock:
                    state = self._leak_state.copy()

                self._poll_water_sensor(state)

                with self._lock:
                    self._leak_state = state

                self._notify_update("LEAK")
                self._last_leak_poll = current_time

            # Environmental and system data: 1 Hz
            if current_time - self._last_environment_poll >= ENV_POLL_INTERVAL:
                with self._lock:
                    state = self._environment_state.copy()

                self._poll_system_stats(state)
                self._poll_bme(state)

                with self._lock:
                    self._environment_state = state

                self._notify_update("ENVIRONMENT")
                self._last_environment_poll = current_time

            time.sleep(TELEMETRY_LOOP_SLEEP)

    def _poll_system_stats(self, state: dict):
        try:
            with open(CPU_TEMP_PATH, "r") as f:
                state["cpu_temp"] = round(int(f.read()) / CPU_TEMP_SCALE, 1)
        except (IOError, ValueError):
            state["cpu_temp"] = None

        try:
            with open(THROTTLED_FLAGS_PATH, "r") as f:
                throttled_flags = int(f.read().strip(), 0)

                # Bit 0: undervoltage currently active
                state["low_pwr"] = bool(throttled_flags & (1 << 0))
        except (IOError, ValueError):
            state["low_pwr"] = None

        try:
            state["cpu_usg"] = psutil.cpu_percent(interval=None)
        except Exception:
            state["cpu_usg"] = None

        try:
            state["ram_usg"] = psutil.virtual_memory().percent
        except Exception:
            state["ram_usg"] = None

    def _poll_water_sensor(self, state: dict):
        if self.water_connected:
            try:
                state["leak_detected"] = (self.gpio.read(WATER_DETECTION_PIN) == 0)
            except pigpio.error:
                self.water_connected = False
                state["leak_detected"] = None

    def _poll_bme(self, state: dict):
        if self.bme_connected:
            try:
                bme_data = bme280.sample(self.bus, BME_ADDRESS, self.bme_calibration)
                state["hull_temp"] = round(bme_data.temperature, 1)
                state["hull_hum"] = round(bme_data.humidity, 1)
                state["hull_press"] = round(bme_data.pressure, 1)
            except Exception:
                self.bme_connected = False
                state["hull_temp"] = None
                state["hull_hum"] = None
                state["hull_press"] = None

    def _poll_imu(self, state: dict):
        """ Calculates pitch and roll from raw accelerometer vectors using a low-pass filter. """
        if self.imu_connected:
            try:
                accel = self.imu.get_accel_data()
                x, y, z = accel['x'], accel['y'], accel['z']

                # Invert axes as needed to match the physical orientation of the sensor on the drone
                raw_pitch = math.degrees(math.atan2(-y, math.sqrt(x*x + z*z)))
                raw_roll = math.degrees(math.atan2(x, z))

                self.pitch_buffer.append(raw_pitch)
                self.roll_buffer.append(raw_roll)

                median_pitch = statistics.median(self.pitch_buffer)
                median_roll = statistics.median(self.roll_buffer)

                # Exponential moving average (low-pass filter) to mitigate noise
                self.pitch_filtered = (SMOOTHING_FACTOR * median_pitch) + ((1.0 - SMOOTHING_FACTOR) * self.pitch_filtered)
                self.roll_filtered = (SMOOTHING_FACTOR * median_roll) + ((1.0 - SMOOTHING_FACTOR) * self.roll_filtered)

                state["pitch"] = round(self.pitch_filtered, 1)
                state["roll"] = round(self.roll_filtered, 1)
            except Exception:
                self.imu_connected = False
                state["pitch"] = None
                state["roll"] = None

    def _poll_thrusters(self, state: dict):
        try:
            thruster_data = self.thruster.get_telemetry_data()

            state["front_pwr"] = thruster_data.get("front_pwr_pct")
            state["rear_pwr"] = thruster_data.get("rear_pwr_pct")
        except Exception:
            state["front_pwr"] = None
            state["rear_pwr"] = None

    def stop(self):
        self._running = False

