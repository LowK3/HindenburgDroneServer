import threading, time, traceback
from Hardware.camera_manager import Camera
from Network.discovery_server import DiscoveryServer
from Network.udp_video_server import VideoServer
from Network.tcp_control_server import ControlServer
from Hardware.Engines.engine_manager import EngineManager
from Hardware.telemetry import TelemetryGatherer
from Utils.common import log
from config import CONNECTION_TIMEOUT

class ServerApp:
    def __init__(self):
        self._shutdown = threading.Event()

    def shutdown_flag(self):
        return self._shutdown.is_set()

    def request_shutdown(self):
        self._shutdown.set()

    def run(self):
        log("Starting server application")

        cam = Camera()
        camera_running = False

        for attempt in range(3): 
            try:
                cam.start()
                camera_running = True
                break
            except Exception as e:
                log(f"Camera init failed (Attempt {attempt+1}/3). Retrying in 5s...")
                time.sleep(5)
                
        if not camera_running:
            video_server = None
            log("[CRITICAL] Camera failed to initialize. Drone will run blind!")
        else:
            video_server = VideoServer(cam)
            video_server.start()

        discovery = DiscoveryServer()
        discovery.start()

        log("Server ready. Press 'Ctrl+C' to stop.")

        engine_mgr = EngineManager()

        telemetry_gatherer = TelemetryGatherer(engine_mgr)
        telemetry_gatherer.start()

        control_server = ControlServer(engine_mgr, telemetry_gatherer, camera_running)
        control_server.start()

        control_thread = threading.Thread(
            target=control_server.accept_client,
            daemon=True
        )
        control_thread.start()

        try:
            while not self.shutdown_flag():
                addr = discovery.listen_once()
                if self.shutdown_flag():
                    break
                if not addr:
                    continue

                client_ip = addr[0]
                log(f"Discovered client at {client_ip}. Waiting for TCP handshake...")

                connected = control_server.connected_event.wait(timeout=CONNECTION_TIMEOUT)

                if not connected:
                    log("Client missed the UDP reply. Returning to discovery immediately...")
                    continue

                # Stream via UDP. (Only executes if the handshake above succeeded!)
                if video_server:
                    video_server.start_stream(client_ip)

                while control_server.  and not self.shutdown_flag():
                    time.sleep(0.5)

                if video_server:
                    video_server.stop_stream()
                log("Client disconnected. Returning to discovery...")
                time.sleep(1.0)

        except KeyboardInterrupt:
            log("KeyboardInterrupt caught, shutting down")
            self.request_shutdown()
        except Exception as e:
            log(f"Unexpected error in main loop: {e}\n{traceback.format_exc()}")
            self.request_shutdown()
        finally:
            log("Pi Server shutting down...")
            control_server.stop()
            telemetry_gatherer.stop()
            engine_mgr.stop()
            log("Engine shutdown complete")
            if video_server:
                video_server.stop()
            cam.stop()
            discovery.stop()
            log("Server shutdown complete")

if __name__ == "__main__":
    ServerApp().run()
