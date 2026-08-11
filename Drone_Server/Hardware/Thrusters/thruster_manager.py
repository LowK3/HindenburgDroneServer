import pigpio
from config import (
    REAR_LEFT_PIN, REAR_RIGHT_PIN, FRONT_LEFT_PIN, FRONT_RIGHT_PIN,
    NEUTRAL, MAX_FORWARD, MAX_REVERSE
)
from thrusters import Thruster
from Utils.common import log

class ThrusterManager:
    """ Translates continuous axis inputs into specific PWM duty cycles using a differential mixer. """
    def __init__(self, gpio_connection: pigpio.pi):
        self.gpio = gpio_connection
        self.rear_left = Thruster(self.gpio, REAR_LEFT_PIN)
        self.rear_right = Thruster(self.gpio, REAR_RIGHT_PIN)
        self.front_left = Thruster(self.gpio, FRONT_LEFT_PIN)
        self.front_right = Thruster(self.gpio, FRONT_RIGHT_PIN)

    def execute(self, payload: dict):
        cmd = payload.get("cmd", "").upper()
        
        if cmd == "STOP":
            self.stop()
            print(f"[Thruster] Executed thruster command: {cmd}")
            return
            
        if cmd == "AXIS":
            axes = payload.get("axes", {})
            self._mix_motors(
                fwd=axes.get("fwd", 0.0),
                yaw=axes.get("yaw", 0.0),
                depth=axes.get("depth", 0.0)
            )
            print(f"[Thruster] Executed thruster command: {cmd}")
        else:
            log(f"[Thruster] Unknown command received: {cmd}")

    def _mix_motors(self, fwd: float, yaw: float, depth: float):
        # 1. Differential mix for rear horizontal thrusters
        rl_mix = fwd + yaw
        rr_mix = fwd - yaw
        
        # Normalize if combinations exceed physical limits (e.g., 100% fwd + 100% yaw)
        max_mix = max(abs(rl_mix), abs(rr_mix), 1.0)
        rl_mix /= max_mix
        rr_mix /= max_mix
        
        self.rear_left.set_duty(self._map_pwm(rl_mix))
        self.rear_right.set_duty(self._map_pwm(rr_mix))
        
        # 2. Direct map for front vertical thrusters (heave)
        self.front_left.set_duty(self._map_pwm(depth))
        self.front_right.set_duty(self._map_pwm(depth))

    def _map_pwm(self, axis_val: float) -> int:
        """ Maps an axis float [-1.0, 1.0] to a PWM duty cycle range. """
        if axis_val == 0.0:
            return NEUTRAL
        elif axis_val > 0.0:
            return int(NEUTRAL + (axis_val * (MAX_FORWARD - NEUTRAL)))
        else:
            return int(NEUTRAL + (axis_val * (NEUTRAL - MAX_REVERSE)))

    def stop(self):
        log("Stopping all thrusters")
        self.rear_left.stop()
        self.rear_right.stop()
        self.front_left.stop()
        self.front_right.stop()