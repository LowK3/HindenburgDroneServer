import socket, struct, math, time, threading, traceback, simplejpeg
from config import UDP_VIDEO_PORT, JPEG_QUALITY, CONNECTION_TIMEOUT, MAGIC_BYTE
from Utils.common import log

class VideoServer:
    def __init__(self, camera):
        self.camera = camera
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.frame_id = 0
        self.max_chunk_size = 1400 # Safe byte limit
        self.streaming = False
        self.stream_thread = None

    def start(self):
        log("UDP Video server initialized.")

    def start_stream(self, client_ip):
        if self.streaming or (self.stream_thread and self.stream_thread.is_alive()):
            self.stop_stream()

            if self.stream_thread and self.stream_thread.is_alive():
                log("[CRITICAL] Previous video thread is deadlocked. Cannot start new stream.")
                return
        
        self.streaming = True
        self.stream_thread = threading.Thread(
            target=self.stream_to_client,
            args=(client_ip,),
            daemon=True
        )
        self.stream_thread.start()

    def stream_to_client(self, client_ip):
        log(f"Starting UDP stream to {client_ip}:{UDP_VIDEO_PORT}")
        try:
            while self.streaming:
                frame = self.camera.capture_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                try:
                    data = simplejpeg.encode_jpeg(frame, quality=JPEG_QUALITY, colorspace='RGB')
                except Exception as e:
                    log(f"Encode failed: {e}\n")
                    continue

                length = len(data)
                num_chunks = math.ceil(length / self.max_chunk_size)

                for i in range(num_chunks):
                    chunk = data[i * self.max_chunk_size : (i+1) * self.max_chunk_size]
                    # Header: MagicByte(0xAA), FrameID, ChunkIndex, TotalChunks
                    header = struct.pack("<BIBB", MAGIC_BYTE, self.frame_id, i, num_chunks)
                    self.sock.sendto(header + chunk, (client_ip, UDP_VIDEO_PORT))

                self.frame_id = (self.frame_id + 1) % 4294967295
                
        except Exception as e:
            log(f"UDP Stream error: {e}\n{traceback.format_exc()}")
        finally:
            log(f"Stopped streaming to {client_ip}")
            self.streaming = False

    def stop_stream(self):
        self.streaming = False
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=1.0)
            if self.stream_thread.is_alive():
                log("ERROR: Video stream thread refused to terminate. Camera hardware may be locked.")

    def stop(self):
        self.stop_stream()
        if self.sock:
            try:
                self.sock.close()
                log("Video UDP socket closed")
            except Exception as e:
                log(f"Video socket close error: {e}\n")
            self.sock = None
