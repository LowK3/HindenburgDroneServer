# network/tcp_server.py
import socket
import struct
import time
import cv2
from config import TCP_PORT, FRAME_INTERVAL, JPEG_QUALITY, TCP_ACCEPT_TIMEOUT, TCP_SEND_TIMEOUT
from Utils.common import log

class TCPServer:
    """
    Accepts a single TCP client and streams length-prefixed JPEG frames.
    On any connection error, it returns to caller so main loop can resume discovery.
    """

    def __init__(self, camera):
        self.camera = camera
        self.server_sock = None

    def start(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("", TCP_PORT))
        self.server_sock.listen(1)
        self.server_sock.settimeout(TCP_ACCEPT_TIMEOUT)
        log(f"TCP server listening on port {TCP_PORT}")

    def accept_client(self, shutdown_flag):
        """
        Wait for a TCP client. Periodically returns None if no connection,
        so caller can check shutdown_flag and/or discovery.
        """
        try:
            conn, addr = self.server_sock.accept()
            conn.settimeout(TCP_SEND_TIMEOUT)
            log(f"TCP client connected from {addr}")
            return conn, addr
        except socket.timeout:
            return None, None
        except Exception as e:
            if not shutdown_flag():
                log(f"TCP accept error: {e}")
            return None, None

    def stream_to_client(self, conn, addr, shutdown_flag):
        """
        Stream frames to a connected client.
        Returns when client disconnects or on error.
        """
        log(f"Starting TCP video stream to {addr}")
        try:
            while not shutdown_flag():
                frame = self.camera.capture_frame()
                if frame is None:
                    log("Skipping frame: camera returned None")
                    time.sleep(FRAME_INTERVAL)
                    continue

                ok, jpeg = cv2.imencode('.jpg', frame,
                                        [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if not ok:
                    log("Failed to encode frame to JPEG, skipping")
                    time.sleep(FRAME_INTERVAL)
                    continue

                data = jpeg.tobytes()
                length = len(data)
                if length == 0:
                    log("Empty JPEG buffer, skipping")
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

                # pacing
                t0 = time.time()
                while time.time() - t0 < FRAME_INTERVAL:
                    if shutdown_flag():
                        break
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
