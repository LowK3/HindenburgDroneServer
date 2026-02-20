import socket, struct, math, time, cv2, simplejpeg
from config import UDP_VIDEO_PORT, FRAME_INTERVAL, JPEG_QUALITY, FORMAT
from Utils.common import log

class VideoServer:
    def __init__(self, camera):
        self.camera = camera
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.frame_id = 0
        self.max_chunk_size = 1500 # Lan byte limit

    def start(self):
        log("UDP Video server initialized.")

    def stream_to_client(self, client_ip, shutdown_flag, poll_keyboard):
        log(f"Starting UDP stream to {client_ip}:{UDP_VIDEO_PORT}")
        try:
            while not shutdown_flag():
                poll_keyboard()

                frame = self.camera.capture_frame()
                if frame is None:
                    continue

                try:
                    data = simplejpeg.encode_jpeg(frame, quality=JPEG_QUALITY, colorspace='BGR')
                except Exception as e:
                    log(f"Encode failed: {e}")
                    continue

                length = len(data)
                num_chunks = math.ceil(length / self.max_chunk_size)

                # Send chunks
                for i in range(num_chunks):
                    chunk = data[i * self.max_chunk_size : (i+1) * self.max_chunk_size]
                    # Header: MagicByte(0xAA), FrameID, ChunkIndex, TotalChunks
                    header = struct.pack("<BIBB", 0xAA, self.frame_id, i, num_chunks)
                    self.sock.sendto(header + chunk, (client_ip, UDP_VIDEO_PORT))

                self.frame_id = (self.frame_id + 1) % 4294967295
                time.sleep(FRAME_INTERVAL)
                
        except Exception as e:
            log(f"UDP Stream error: {e}")
        finally:
            log(f"Stopped streaming to {client_ip}")

    def stop(self):
        if self.sock:
            try:
                self.sock.close()
                log("Video UDP socket closed")
            except Exception as e:
                log(f"Video socket close error: {e}")
            self.sock = None
