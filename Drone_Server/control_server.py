import socket
import threading
import json
import pigpio
import time

# ======================== ENGINE CLASSES ========================

class Engine:
    """Base class for an ESC-controlled engine using PWM via pigpio."""
    def __init__(self, pi, pin, name):
        self.pi = pi
        self.pin = pin
        self.name = name
        self.pwm_freq = 50
        self.range = 1000
        self.neutral = 75   # 7.5% = 1500 µs pulse (stop)
        self.min_duty = 60  # ~5% = full reverse
        self.max_duty = 100 # ~10% = full forward
        self.current_duty = self.neutral

        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        self.pi.set_PWM_frequency(self.pin, self.pwm_freq)
        self.pi.set_PWM_range(self.pin, self.range)
        self.stop()

    def set_duty(self, duty):
        """Clamp and apply PWM duty cycle."""
        duty = max(self.min_duty, min(self.max_duty, duty))
        self.pi.set_PWM_dutycycle(self.pin, duty)
        self.current_duty = duty
        print(f"[{self.name}] duty={duty}")

    def stop(self):
        """Set motor to neutral."""
        self.set_duty(self.neutral)

    def forward(self, power=0.5):
        """Move forward: 0–1 range duty between neutral and max."""
        duty = self.neutral + (self.max_duty - self.neutral) * power
        self.set_duty(duty)

    def reverse(self, power=0.5):
        """Move backward: 0–1 range → duty between neutral and min."""
        duty = self.neutral - (self.neutral - self.min_duty) * power
        self.set_duty(duty)


class RearEngine(Engine):
    """Rear engine for forward/backward and turning."""
    pass


class FrontEngine(Engine):
    """Front engine for vertical movement."""
    pass


# ======================== SUBMARINE SERVER ========================

class SubmarineServer:
    def __init__(self, host="0.0.0.0", port=9000):
        self.host = host
        self.port = port
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("pigpio daemon not running. Start it with 'sudo pigpiod'.")

        # Four motors
        self.engines = {
            "rear_left":  RearEngine(self.pi, 13, "RearLeft"),
            "rear_right": RearEngine(self.pi, 5,  "RearRight"),
            "front_left": FrontEngine(self.pi, 20, "FrontLeft"),
            "front_right":FrontEngine(self.pi, 7,  "FrontRight"),
        }

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.shutdown_event = threading.Event()

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"[Server] Listening on {self.host}:{self.port}")

        while not self.shutdown_event.is_set():
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"[Server] Client connected: {addr}")
                self.handle_client(client_socket)
            except KeyboardInterrupt:
                self.shutdown_event.set()
            except Exception as e:
                print(f"[Server Error] {e}")
                time.sleep(1)

        self.cleanup()

    def handle_client(self, client_socket):
        client_socket.settimeout(0.1)
        while not self.shutdown_event.is_set():
            try:
                data = client_socket.recv(1024)
                if not data:
                    print("[Server] Client disconnected")
                    break

                msg = json.loads(data.decode())
                self.process_command(msg)

            except socket.timeout:
                continue
            except Exception as e:
                print(f"[Server] Error: {e}")
                break

        for e in self.engines.values():
            e.stop()
        client_socket.close()

    def process_command(self, msg):
        """Interpret JSON messages from client."""
        cmd = msg.get("command")
        power = float(msg.get("power", 0.5))
        print(f"[Server] Received command: {cmd} power={power}")

        # Movement logic
        if cmd == "forward":
            self.engines["rear_left"].forward(power)
            self.engines["rear_right"].forward(power)
        elif cmd == "backward":
            self.engines["rear_left"].reverse(power)
            self.engines["rear_right"].reverse(power)
        elif cmd == "left":
            self.engines["rear_left"].reverse(power)
            self.engines["rear_right"].forward(power)
        elif cmd == "right":
            self.engines["rear_left"].forward(power)
            self.engines["rear_right"].reverse(power)
        elif cmd == "up":
            self.engines["front_left"].forward(power)
            self.engines["front_right"].forward(power)
        elif cmd == "down":
            self.engines["front_left"].reverse(power)
            self.engines["front_right"].reverse(power)
        elif cmd == "stop":
            for e in self.engines.values():
                e.stop()

    def cleanup(self):
        print("[Server] Stopping all motors and cleaning up.")
        for e in self.engines.values():
            e.stop()
        self.pi.stop()
        self.server_socket.close()


if __name__ == "__main__":
    server = SubmarineServer()
    server.start()
