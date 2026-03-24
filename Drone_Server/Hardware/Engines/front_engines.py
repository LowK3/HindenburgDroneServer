from .engines import Engine, NEUTRAL
from config import DEFAULT_POWER

class FrontEngines:
    """ Controls front thrusters for up/down tilt. """

    def __init__(self, pi, left_pin, right_pin):
        self.left = Engine(pi, left_pin)
        self.right = Engine(pi, right_pin)
        self.power = DEFAULT_POWER

    def tilt_up(self):
        self.left.set_duty(NEUTRAL + self.power)
        self.right.set_duty(NEUTRAL + self.power)

    def tilt_down(self):
        self.left.set_duty(NEUTRAL - self.power)
        self.right.set_duty(NEUTRAL - self.power)

    def stop(self):
        self.left.stop()
        self.right.stop()

    def increase_power(self):
        self.power = min(self.power + 2, 25)

    def decrease_power(self):
        self.power = max(self.power - 2, 5)

    def get_power_percentage(self):
        return int(((self.power - 5) / (25 - 5)) * 100)
