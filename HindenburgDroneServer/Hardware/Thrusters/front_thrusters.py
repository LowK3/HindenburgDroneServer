from .thrusters import NEUTRAL
from .paired_thrusters import PairedThrusters

class FrontThrusters(PairedThrusters):
    """ Controls front thrusters for up/down tilt. """
    def tilt_up(self):
        self.left.set_duty(NEUTRAL + self.power)
        self.right.set_duty(NEUTRAL + self.power)

    def tilt_down(self):
        self.left.set_duty(NEUTRAL - self.power)
        self.right.set_duty(NEUTRAL - self.power)
