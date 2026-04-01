from .thrusters import NEUTRAL
from .paired_thrusters import PairedThrusters

class RearThrusters(PairedThrusters):
    """ Controls the rear thrusters for forward/backward and turning. """
    def forward(self):
        self.left.set_duty(NEUTRAL + self.power)
        self.right.set_duty(NEUTRAL + self.power)

    def backward(self):
        self.left.set_duty(NEUTRAL - self.power)
        self.right.set_duty(NEUTRAL - self.power)

    def turn_left(self):
        self.left.set_duty(NEUTRAL - self.power)
        self.right.set_duty(NEUTRAL + self.power)

    def turn_right(self):
        self.left.set_duty(NEUTRAL + self.power)
        self.right.set_duty(NEUTRAL - self.power)
