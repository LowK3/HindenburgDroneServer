import pigpio
from config import REAR_LEFT_PIN, REAR_RIGHT_PIN, FRONT_LEFT_PIN, FRONT_RIGHT_PIN
from .rear_engines import RearEngines
from .front_engines import FrontEngines
from Utils.common import log

class EngineManager:
    """ Engine control accepting commands from control TCP server. """
    def __init__(self):
        self.pi = pigpio.pi()
        self.rear = RearEngines(self.pi, REAR_LEFT_PIN, REAR_RIGHT_PIN)
        self.front = FrontEngines(self.pi, FRONT_LEFT_PIN, FRONT_RIGHT_PIN)

        self._command_map = {
            "W": self.rear.forward,
            "S": self.rear.backward,
            "A": self.rear.turn_left,
            "D": self.rear.turn_right,
            "UP": self.front.tilt_up,
            "DOWN": self.front.tilt_down,
            "STOP": self._stop_all_engines,
            "REAR+": self.rear.increase_power,
            "REAR-": self.rear.decrease_power,
            "FRONT+": self.front.increase_power,
            "FRONT-": self.front.decrease_power
        }

    def _stop_all_engines(self):
        self.rear.stop()
        self.front.stop()

    def execute(self, payload: dict):
        action = payload.get("cmd", "").upper()
        
        command_func = self._command_map.get(action)
        if command_func:
            command_func()
            log(f"Executed engine command: {action}")
        else:
            log(f"Unknown command received: {action}")

    def stop(self):
        log("Stopping all engines")
        self._stop_all_engines()
        self.pi.stop()

    def get_telemetry_data(self):
        return {
            "front_power_pct": self.front.get_power_percentage(),
            "rear_power_pct": self.rear.get_power_percentage()
        }