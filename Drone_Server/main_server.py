import threading, sys, time
from config import MAX_TCP_WAIT
from Hardware.camera_manager import Camera
from Network.discovery_server import DiscoveryServer
from Network.tcp_video_server import TCPServer
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

        video_server = TCPServer(cam)
        video_server.start()
        log("Server ready. Press 'q' then Enter to stop.")

        engine_mgr = EngineManager()
        control_server = ControlServer(engine_mgr)
        control_server.start()

        control_thread = threading.Thread(
            target=control_server.accept_loop,
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

                log(f"Discovered client via UDP: {addr}, waiting for TCP connection")

                # 2) Wait for TCP connection
                conn, tcp_addr = None, None
                start_wait = time.time()
                while not self.shutdown_flag() and conn is None:
                    check_keyboard(self._shutdown)
                    conn, tcp_addr = video_server.accept_client(self.shutdown_flag)

                    if conn is None and (time.time() - start_wait) > MAX_TCP_WAIT:
                        log("TCP connection timeout after discovery, returning to discovery loop")
                        break

                if self.shutdown_flag():
                    break

                if conn is None:
                    log("No TCP client connected in time, back to discovery")
                    continue

                # 3) Stream until client disconnects or error
                video_server.stream_to_client(conn, tcp_addr, self.shutdown_flag, lambda: check_keyboard(self._shutdown))

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
