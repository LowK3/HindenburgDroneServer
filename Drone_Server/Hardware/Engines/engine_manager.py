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
        self.last_cmd = None

    def execute(self, cmd: dict):
        cmd = cmd.get("cmd", "").upper()

        if cmd == self.last_cmd:
            return
            
        self.last_cmd = cmd

        # Movement
        if cmd == "W": self.rear.forward()
        elif cmd == "S": self.rear.backward()
        elif cmd == "A": self.rear.turn_left()
        elif cmd == "D": self.rear.turn_right()

        # Tilt
        elif cmd == "UP": self.front.tilt_up()
        elif cmd == "DOWN": self.front.tilt_down()

        # Stop
        elif cmd == "STOP": 
            self.rear.stop()
            self.front.stop()

        # Power adjustments
        elif cmd == "REAR+": self.rear.increase_power()
        elif cmd == "REAR-": self.rear.decrease_power()
        elif cmd == "FRONT+": self.front.increase_power()
        elif cmd == "FRONT-": self.front.decrease_power()

        else:
            log(f"Unknown command: {cmd}")
            return
        
        log(f"Executed engine command: {cmd}")

    def stop(self):
        log("Stopping all engines")
        self.rear.stop()
        self.front.stop()
        self.pi.stop()
