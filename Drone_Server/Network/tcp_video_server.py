import socket, struct, time, cv2
from config import TCP_PORT, FRAME_INTERVAL, JPEG_QUALITY, TCP_ACCEPT_TIMEOUT, TCP_SEND_TIMEOUT, FORMAT
from Utils.common import log

class TCPServer:
    """
    Accepts a single TCP client and streams length-prefixed JPEG frames.
    On any error/disconnect, returns to caller so main loop can rediscover.
    """
    def __init__(self, camera):
        self.camera = camera
        self.server_sock = None

    def start(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
        self.server_sock.bind(("", TCP_PORT))
        self.server_sock.listen(1)
        self.server_sock.settimeout(TCP_ACCEPT_TIMEOUT)
        log(f"TCP server listening on {TCP_PORT}")

    def accept_client(self, shutdown_flag):
        """Wait for TCP client; returns (conn, addr) or (None, None) on timeout/error."""
        try:
            conn, addr = self.server_sock.accept()
            conn.settimeout(TCP_SEND_TIMEOUT)
            log(f"TCP client connected: {addr}")
            return conn, addr
        except socket.timeout:
            return None, None
        except Exception as e:
            if not shutdown_flag():
                log(f"TCP accept error: {e}")
            return None, None

    def stream_to_client(self, conn, addr, shutdown_flag, poll_keyboard):
        """
        Stream frames to client until:
          - shutdown_flag() is True
          - send fails
        Then closes connection and returns.
        """
        log(f"Starting TCP stream to {addr}")
        try:
            while not shutdown_flag():
                poll_keyboard()  # Allows "q" to work during streaming

                frame = self.camera.capture_frame()
                if frame is None:
                    log("Camera returned None, skipping frame")
                    time.sleep(FRAME_INTERVAL)
                    continue

                ok, jpeg = cv2.imencode(FORMAT, frame,
                                        [int(cv2.IMWRITE_JPEG_QUALITY)])
                if not ok:
                    log("JPEG encode failed, skipping frame")
                    time.sleep(FRAME_INTERVAL)
                    continue

                data = jpeg.tobytes()
                length = len(data)
                if length == 0:
                    log("Empty JPEG buffer, skipping frame")
                    time.sleep(FRAME_INTERVAL)
                    continue

                try:
                    conn.sendall(struct.pack("<I", length) + data)
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    log(f"Client {addr} disconnected during send: {e}")
                    break
                except Exception as e:
                    log(f"Unexpected send error to {addr}: {e}")
                    break

                t0 = time.time()
                while time.time() - t0 < FRAME_INTERVAL:
                    if shutdown_flag():
                        break
                    poll_keyboard()
                    time.sleep(0.003)

        finally:
            try:
                conn.close()
            except Exception as e:
                log(f"Error closing client socket {addr}: {e}")
            log(f"Stream to {addr} ended, returning to discovery")

    def stop(self):
        if self.server_sock:
            try:
                self.server_sock.close()
                log("TCP server socket closed")
            except Exception as e:
                log(f"TCP server close error: {e}")
            self.server_sock = None
