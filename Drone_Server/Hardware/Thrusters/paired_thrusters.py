from .thrusters import Thruster, NEUTRAL
from config import DEFAULT_POWER

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
        self.power = min(self.power + 2, 25)

    def decrease_power(self):
        self.power = max(self.power - 2, 5)

    def get_power_percentage(self):
        return int(((self.power - 5) / (25 - 5)) * 100)