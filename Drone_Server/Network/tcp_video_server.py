import socket, struct, cv2, time
from config import TCP_PORT, JPEG_QUALITY, FRAME_INTERVAL

class TCPServer:
    def __init__(self, camera):
        self.camera = camera
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("", TCP_PORT))
        self.server.listen(1)

    def serve_once(self):
        conn, addr = self.server.accept()
        print("TCP client connected:", addr)
        with conn:
            while True:
                frame = self.camera.capture_frame()
                if frame is None:
                    continue
                ok, jpeg = cv2.imencode(".jpg", frame,
                                        [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if not ok:
                    continue
                data = jpeg.tobytes()
                conn.sendall(struct.pack("<I", len(data)) + data)
                time.sleep(FRAME_INTERVAL)
