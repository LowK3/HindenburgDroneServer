import pigpio
from config import PWM_FREQUENCY, PWM_RANGE, NEUTRAL, MAX_FORWARD, MAX_REVERSE
from Utils.common import log

class Thruster:
    """ Base class representing a single thruster. """
    def __init__(self, pi: pigpio.pi, pin: int):
        self.pi = pi
        self.pin = pin
        self.current = NEUTRAL

        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(self.pin, PWM_FREQUENCY)
        self.pi.set_PWM_range(self.pin, PWM_RANGE)
        self.pi.set_watchdog(self.pin, 500)
        self.set_duty(NEUTRAL)
        log(f"[Thruster] Initialized thruster on GPIO {pin}")

    def set_duty(self, duty: int):
        duty = max(MAX_REVERSE, min(MAX_FORWARD, duty))
        self.current = duty
        self.pi.set_PWM_dutycycle(self.pin, duty)

    def stop(self):
        self.set_duty(NEUTRAL)
