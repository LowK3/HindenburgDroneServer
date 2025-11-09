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
        try:
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            if dr:
                key = sys.stdin.read(1)
                if key.lower() == 'q':
                    log("Shutdown key pressed (q), shutting down")
                    self.request_shutdown()
        except Exception:
            # Non-fatal: ignore stdin issues
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

                # Phase 1: Discovery
                addr = discovery.listen_once()
                if self.shutdown_flag():
                    break
                if not addr:
                    continue  # timeout, loop again

                log(f"Discovered client via UDP: {addr}, waiting for TCP connect")

                # Phase 2: Accept TCP client
                conn, tcp_addr = None, None
                while not self.shutdown_flag() and conn is None:
                    self._check_keyboard()
                    conn, tcp_addr = tcp_server.accept_client(self.shutdown_flag)
                    if conn is None and not self.shutdown_flag():
                        # No TCP yet still log occasionally
                        continue

                if self.shutdown_flag():
                    break
                if conn is None:
                    # Something went wrong; back to discovery
                    log("Failed to establish TCP connection, returning to discovery")
                    continue

                # Phase 3: Stream until client dies or error
                tcp_server.stream_to_client(conn, tcp_addr, self.shutdown_flag)

                # At this point: stream ended (client disconnect, error, etc.)
                log("Client disconnected or stream ended. Returning to discovery loop.")

        except KeyboardInterrupt:
            log("KeyboardInterrupt caught, shutting down")
            self.request_shutdown()
        except Exception as e:
            log(f"Unexpected fatal error in main loop: {e}")
            self.request_shutdown()
        finally:
            log("Server shutting down, cleaning up...")
            try:
                tcp_server.stop()
            except Exception as e:
                log(f"Error stopping TCP server: {e}")

            try:
                discovery.stop()
            except Exception as e:
                log(f"Error stopping discovery: {e}")

            try:
                cam.stop()
            except Exception as e:
                log(f"Error stopping camera: {e}")

            log("Shutdown complete")

if __name__ == "__main__":
    app = ServerApp()
    app.run()
