import threading, sys, time
from config import MAX_TCP_WAIT
from Hardware.camera_manager import Camera
from Network.discovery_server import DiscoveryServer
from Network.udp_video_server import VideoServer
from Network.tcp_control_server import ControlServer
from Hardware.Engines.engine_manager import EngineManager
from Utils.common import log, check_keyboard

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
        cam.start()

        discovery = DiscoveryServer()
        discovery.start()

        video_server = VideoServer(cam)
        video_server.start()
        log("Server ready. Press 'q' then Enter to stop.")

        engine_mgr = EngineManager()
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

                # 1) Discovery (non-blocking)
                addr = discovery.listen_once()
                if self.shutdown_flag():
                    break
                if not addr:
                    continue

                client_ip = addr[0]
                log(f"Discovered client at {client_ip}. Starting UDP Video stream!")

                # 2) Stream via UDP. (The Control Server handles its own TCP connections in the background thread!)
                video_server.stream_to_client(client_ip, self.shutdown_flag, lambda: check_keyboard(self._shutdown), control_server)

                log("Stream ended. Returning to discovery...")
                time.sleep(1.0)

        except KeyboardInterrupt:
            log("KeyboardInterrupt caught, shutting down")
            self.request_shutdown()
        except Exception as e:
            log(f"Unexpected error in main loop: {e}")
            self.request_shutdown()
        finally:
            log("Pi Server shutting down...")
            control_server.stop()
            engine_mgr.stop()
            log("Engine shutdown complete")
            cam.stop()
            video_server.stop()
            discovery.stop()
            log("Server shutdown complete")

if __name__ == "__main__":
    ServerApp().run()
