import threading
import time
import traceback
import pigpio
from Hardware.camera_manager import Camera
from Network.discovery_server import DiscoveryServer
from Network.udp_video_server import VideoServer
from Network.tcp_control_server import ControlServer
from Hardware.Engines.engine_manager import EngineManager
from Hardware.telemetry import TelemetryGatherer
from Utils.common import log ,setup_logging
from config import CONNECTION_TIMEOUT

class ServerApp:
    def __init__(self):
        self._shutdown = threading.Event()

        self.gpio_connection = pigpio.pi()
        if not self.gpio_connection.connected:
            raise RuntimeError("[CRITICAL] Failed to connect to pigpiod.")

        self.cam = Camera()
        self.engine_mgr = EngineManager(self.gpio_connection)
        self.telemetry_gatherer = TelemetryGatherer(self.engine_mgr, self.gpio_connection)
        self.discovery = DiscoveryServer()
        self.video_server = None
        self.control_server = None

    def shutdown_flag(self):
        return self._shutdown.is_set()

    def request_shutdown(self):
        self._shutdown.set()

    def run(self):
        self.setup()
        try:
            self._main_loop()
        except KeyboardInterrupt:
            log("KeyboardInterrupt caught, shutting down")
            self.request_shutdown()
        except Exception as e:
            log(f"Unexpected error in main loop: {e}\n{traceback.format_exc()}")
            self.request_shutdown()
        finally:
            self._stop()

    def _setup(self):
        setup_logging()
        log("Starting server application")
        
        camera_running = self._initialize_camera()
        if camera_running:
            self.video_server = VideoServer(self.cam)
            self.video_server.start()

        self.discovery.start()
        self.telemetry_gatherer.start()

        self.control_server = ControlServer(self.engine_mgr, self.telemetry_gatherer, camera_running)
        self.control_server.start()

        control_thread = threading.Thread(
            target=self.control_server.accept_client, 
            daemon=True
        )
        control_thread.start()
        log("Server ready. Press 'Ctrl+C' to stop.")

    def _initialize_camera(self):
        for attempt in range(3): 
            try:
                self.cam.start()
                return True
            except Exception:
                log(f"Camera init failed (Attempt {attempt+1}/3). Retrying in 5s...")
                time.sleep(5)
        log("[CRITICAL] Camera failed to initialize. Drone will run blind!")
        return False

    def _main_loop(self):
        while not self.shutdown_flag():
            addr = self.discovery.listen_once()
            if self.shutdown_flag():
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

            while self.control_server.is_connected and not self.shutdown_flag():
                time.sleep(0.5)

            if self.video_server:
                self.video_server.stop_stream()
            log("Client disconnected. Returning to discovery...")
            time.sleep(1.0)

    def _stop(self):
        log("Pi Server shutting down...")
        if self.control_server:
            self.control_server.stop()
        self.telemetry_gatherer.stop()
        self.engine_mgr.stop()
        log("Engine shutdown complete")
        if self.video_server:
            self.video_server.stop()
        self.cam.stop()
        self.discovery.stop()
        self.gpio_connection.stop()
        log("Server shutdown complete")

if __name__ == "__main__":
    ServerApp().run()
