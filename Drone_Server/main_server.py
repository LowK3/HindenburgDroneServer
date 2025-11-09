# main_server.py
import threading
import sys
import select
from Hardware.camera_manager import Camera
from Network.discovery_server import DiscoveryServer
from Network.tcp_video_server import TCPServer
from Utils.common import log

class ServerApp:
    def __init__(self):
        self._shutdown = threading.Event()

    def shutdown_flag(self):
        return self._shutdown.is_set()

    def request_shutdown(self):
        self._shutdown.set()

    def _check_keyboard(self):
        """Called frequently (including during streaming) so 'q' works."""
        try:
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            if dr:
                key = sys.stdin.read(1)
                if key.lower() == 'q':
                    log("Shutdown key 'q' pressed.")
                    self.request_shutdown()
        except Exception:
            # ignore stdin issues
            pass

    def run(self):
        log("Starting server application")

        cam = Camera()
        cam.start()

        discovery = DiscoveryServer()
        discovery.start()

        tcp_server = TCPServer(cam)
        tcp_server.start()

        log("Server ready. Press 'q' then Enter to stop.")

        try:
            while not self.shutdown_flag():
                self._check_keyboard()

                # 1) Discovery (non-blocking)
                addr = discovery.listen_once()
                if self.shutdown_flag():
                    break
                if not addr:
                    continue

                log(f"Discovered client via UDP: {addr}, waiting for TCP connection")

                # 2) Wait for TCP connection
                conn, tcp_addr = None, None
                while not self.shutdown_flag() and conn is None:
                    self._check_keyboard()
                    conn, tcp_addr = tcp_server.accept_client(self.shutdown_flag)

                if self.shutdown_flag():
                    break
                if conn is None:
                    log("No TCP connection established, back to discovery")
                    continue

                # 3) Stream until client disconnects or error
                tcp_server.stream_to_client(conn, tcp_addr, self.shutdown_flag, self._check_keyboard)

                log("Client disconnected / stream ended. Returning to discovery loop.")

        except KeyboardInterrupt:
            log("KeyboardInterrupt caught, shutting down")
            self.request_shutdown()
        except Exception as e:
            log(f"Unexpected error in main loop: {e}")
            self.request_shutdown()
        finally:
            log("Server shutting down...")
            tcp_server.stop()
            discovery.stop()
            cam.stop()
            log("Server shutdown complete")

if __name__ == "__main__":
    ServerApp().run()
