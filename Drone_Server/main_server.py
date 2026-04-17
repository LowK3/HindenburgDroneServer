import threading
import time
import traceback
import pigpio
from Hardware.camera_manager import Camera
from Network.discovery_server import DiscoveryServer
from Network.udp_video_server import VideoServer
from Network.tcp_control_server import ControlServer
from Hardware.Thrusters.thruster_manager import ThrusterManager
from Hardware.telemetry import TelemetryGatherer
from Utils.common import log, setup_logging
from config import (
    CONNECTION_TIMEOUT, CAMERA_RETRY_DELAY, CAMERA_INIT_RETRIES, DISCONNECT_COOLDOWN,
    MAIN_LOOP_YIELD
)

class ServerApp:
    def __init__(self):
        self._stop_event = threading.Event()

        self.gpio_connection = pigpio.pi()
        if not self.gpio_connection.connected:
            raise RuntimeError("[CRITICAL] Failed to connect to pigpiod.")

        self.cam = Camera()
        self.thruster_mgr = ThrusterManager(self.gpio_connection)
        self.telemetry_gatherer = TelemetryGatherer(self.thruster_mgr, self.gpio_connection)
        self.discovery = DiscoveryServer()
        self.video_server = None
        self.control_server = None

    def run(self):
        self._setup()
        try:
            self._main_loop()
        except KeyboardInterrupt:
            log("KeyboardInterrupt caught, shutting down")
            self._stop_event.set()
        except Exception as e:
            log(f"Unexpected error in main loop: {e}\n{traceback.format_exc()}")
            self._stop_event.set()
        finally:
            self._stop()

    def _setup(self):
        setup_logging()
        log("Starting server application")
        
        camera_started = self._initialize_camera()
        if camera_started:
            self.video_server = VideoServer(self.cam)
            self.video_server.start()

        self.discovery.start()
        self.telemetry_gatherer.start()

        self.control_server = ControlServer(self.thruster_mgr, self.telemetry_gatherer, self.camera_running)
        self.control_server.start()

        control_thread = threading.Thread(
            target=self.control_server.accept_client, 
            daemon=True
        )
        control_thread.start()
        log("Server ready. Press 'Ctrl+C' to stop.")

    def _initialize_camera(self):
        for attempt in range(CAMERA_INIT_RETRIES): 
            try:
                self.cam.start()
                return True
            except Exception:
                log(f"Camera init failed (Attempt {attempt+1}/{CAMERA_INIT_RETRIES}). Retrying in 5s...")
                time.sleep(CAMERA_RETRY_DELAY)
        log("[CRITICAL] Camera failed to initialize. Drone will run blind!")
        return False

    def camera_running(self):
        if not self.video_server:
            return False
        
        if self.video_server.stream_thread and self.video_server.stream_thread.is_alive():
            if time.time() - self.video_server.last_frame_time > 1.0:
                return False
        return True

    def _main_loop(self):
        while not self._stop_event.is_set():
            addr = self.discovery.listen_once()
            if self._stop_event.is_set():
                break
            if not addr:
                continue

            client_ip = addr[0]
            log(f"Discovered client at {client_ip}. Waiting for TCP handshake...")

            connected = self.control_server.connected_event.wait(timeout=CONNECTION_TIMEOUT)
            if not connected:
                log("Client missed the UDP reply. Returning to discovery immediately...")
                continue

            if self.video_server:
                self.video_server.start_stream(client_ip)

            while self.control_server.is_connected and not self._stop_event.is_set():
                self.control_server.disconnected_event.wait(timeout=MAIN_LOOP_YIELD)

            if self.video_server:
                self.video_server.stop_stream()
            log("Client disconnected. Returning to discovery...")
            time.sleep(DISCONNECT_COOLDOWN)

    def _stop(self):
        log("Pi Server shutting down...")
        if self.control_server:
            self.control_server.stop()
        self.telemetry_gatherer.stop()
        self.thruster_mgr.stop()
        log("Thruster shutdown complete")
        if self.video_server:
            self.video_server.stop()
        self.cam.stop()
        self.discovery.stop()
        self.gpio_connection.stop()
        log("Server shutdown complete")

if __name__ == "__main__":
    ServerApp().run()
