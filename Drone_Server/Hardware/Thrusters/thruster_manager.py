import pigpio
from config import REAR_LEFT_PIN, REAR_RIGHT_PIN, FRONT_LEFT_PIN, FRONT_RIGHT_PIN
from .rear_thrusters import RearThrusters
from .front_thrusters import FrontThrusters
from Utils.common import log

class ThrusterManager:
    """ Thruster control accepting commands from control TCP server. """
    def __init__(self, gpio_connection: pigpio.pi):
        self.gpio = gpio_connection
        self.rear = RearThrusters(self.gpio, REAR_LEFT_PIN, REAR_RIGHT_PIN)
        self.front = FrontThrusters(self.gpio, FRONT_LEFT_PIN, FRONT_RIGHT_PIN)

        self._command_map = {
            "W": self.rear.forward,
            "S": self.rear.backward,
            "A": self.rear.turn_left,
            "D": self.rear.turn_right,
            "UP": self.front.tilt_up,
            "DOWN": self.front.tilt_down,
            "STOP": self._stop_all_thrusters,
            "REAR+": self.rear.increase_power,
            "REAR-": self.rear.decrease_power,
            "FRONT+": self.front.increase_power,
            "FRONT-": self.front.decrease_power
        }

    def execute(self, payload: dict):
        action = payload.get("cmd", "").upper()
        
        command_func = self._command_map.get(action)
        if command_func:
            command_func()
            log(f"Executed thruster command: {action}")
        else:
            log(f"Unknown command received: {action}")

    def get_telemetry_data(self):
        return {
            "front_power_pct": self.front.get_power_percentage(),
            "rear_power_pct": self.rear.get_power_percentage()
        }

    def stop(self):
        log("Stopping all thrusters")
        self._stop_all_thrusters()

    def _stop_all_thrusters(self):
        self.rear.stop()
        self.front.stop()