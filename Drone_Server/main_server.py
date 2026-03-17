from re import I
import threading, sys, time, traceback
from Hardware.camera_manager import Camera
from Network.discovery_server import DiscoveryServer
from Network.udp_video_server import VideoServer
from Network.tcp_control_server import ControlServer
from Hardware.Engines.engine_manager import EngineManager
from Utils.common import log, check_keyboard
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
            log("[CRITICAL] Camera failed to initialize. Drone will run blind!")

        discovery = DiscoveryServer()
        discovery.start()

        video_server = VideoServer(cam)
        video_server.start()
        log("Server ready. Press 'q' then Enter to stop.")

        engine_mgr = EngineManager()
        # Safety delay to allow ESCs to initialize and prevent accidental motor spin on startup
        log("Arming ESCs... Please wait 3 seconds.")
        time.sleep(3)
        log("ESCs Armed.")
        control_server = ControlServer(engine_mgr)
        control_server.start()

        control_thread = threading.Thread(
            target=control_server.accept_client,
            args=(self.shutdown_flag,),
            daemon=True
        )
        control_thread.start()

        try:
            while not self.shutdown_flag():
                check_keyboard(self._shutdown)

                addr = discovery.listen_once()
                if self.shutdown_flag():
                    break
                if not addr:
                    continue

                client_ip = addr[0]
                log(f"Discovered client at {client_ip}. Waiting for TCP handshake...")

                handshake_timeout = time.time() + CONNECTION_TIMEOUT
                while time.time() < handshake_timeout and not control_server.is_connected:
                    time.sleep(0.1)

                if not control_server.is_connected:
                    log("Client missed the UDP reply. Returning to discovery immediately...")
                    continue

                # Stream via UDP. (Only executes if the handshake above succeeded!)
                video_server.stream_to_client(client_ip, self.shutdown_flag, lambda: check_keyboard(self._shutdown), control_server)

                log("Stream ended. Returning to discovery...")
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
            engine_mgr.stop()
            log("Engine shutdown complete")
            video_server.stop()
            cam.stop()
            discovery.stop()
            log("Server shutdown complete")

if __name__ == "__main__":
    ServerApp().run()
