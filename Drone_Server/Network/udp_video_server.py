import socket, struct, math, time, cv2, traceback
from config import UDP_VIDEO_PORT, JPEG_QUALITY, CONNECTION_TIMEOUT
from Utils.common import log

class VideoServer:
    def __init__(self, camera):
        self.camera = camera
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.frame_id = 0
        self.max_chunk_size = 1400 # Safe lan byte limit

    def start(self):
        log("UDP Video server initialized.")

    def stream_to_client(self, client_ip, shutdown_flag, poll_keyboard, control_server):
        log(f"Starting UDP stream to {client_ip}:{UDP_VIDEO_PORT}")

        connection_timeout = time.time() + CONNECTION_TIMEOUT

        try:
            while not shutdown_flag():
                poll_keyboard()

                if control_server.is_connected:
                    connection_timeout = time.time() + CONNECTION_TIMEOUT
                elif time.time() > connection_timeout:
                    log("Client TCP control lost. Stopping UDP video stream.")
                    break

                frame = self.camera.capture_frame()
                if frame is None:
                    continue

                data = frame.tobytes() 
                length = len(data)
                num_chunks = math.ceil(length / self.max_chunk_size)

                length = len(data)
                num_chunks = math.ceil(length / self.max_chunk_size)

                for i in range(num_chunks):
                    chunk = data[i * self.max_chunk_size : (i+1) * self.max_chunk_size]
                    # Header: MagicByte(0xAA), FrameID, ChunkIndex, TotalChunks
                    header = struct.pack("<BIHH", 0xAA, self.frame_id, i, num_chunks)
                    self.sock.sendto(header + chunk, (client_ip, UDP_VIDEO_PORT))

                self.frame_id = (self.frame_id + 1) % 4294967295
                
        except Exception as e:
            log(f"UDP Stream error: {e}\n{traceback.format_exc()}")
        finally:
            log(f"Stopped streaming to {client_ip}")

    def stop(self):
        if self.sock:
            try:
                self.sock.close()
                log("Video UDP socket closed")
            except Exception as e:
                log(f"Video socket close error: {e}\n{traceback.format_exc()}")
            self.sock = None
