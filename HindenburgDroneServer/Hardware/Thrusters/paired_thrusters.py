from .thrusters import Thruster, NEUTRAL
from config import DEFAULT_POWER, POWER_INCREMENT, POWER_MIN, POWER_MAX

class PairedThrusters:
    """ Base class for managing a pair of thrusters. """
    def __init__(self, pi, left_pin: int, right_pin: int):
        self.left = Thruster(pi, left_pin)
        self.right = Thruster(pi, right_pin)
        self.power = DEFAULT_POWER

    def stop(self):
        self.left.stop()
        self.right.stop()

    def increase_power(self):
        self.power = min(self.power + POWER_INCREMENT, POWER_MAX)

    def decrease_power(self):
        self.power = max(self.power - POWER_INCREMENT, POWER_MIN)

    def get_power_percentage(self):
        return int(((self.power - POWER_MIN) / (POWER_MAX - POWER_MIN)) * 100)