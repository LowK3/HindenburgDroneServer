import socket
import struct
import math
import time
import threading
import traceback
import simplejpeg
from config import UDP_VIDEO_PORT, JPEG_QUALITY, CONNECTION_TIMEOUT, MAGIC_BYTE, CHUNK_BYTE_LIMIT
from Utils.common import log

class VideoServer:
    def __init__(self, camera):
        self.camera = camera
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.frame_id = 0
        self.max_chunk_size = CHUNK_BYTE_LIMIT
        self._stream_event = threading.Event()
        self.stream_thread = None
        self.last_frame_time = time.time()

    def start(self):
        log("UDP Video server initialized.")

    def start_stream(self, client_ip: str):
        if self._stream_event.is_set() or (self.stream_thread and self.stream_thread.is_alive()):
            self.stop_stream()

            if self.stream_thread and self.stream_thread.is_alive():
                log("[CRITICAL] Previous video thread is deadlocked. Cannot start new stream.")
                return
        
        self._stream_event.set()
        self.last_frame_time = time.time()
        self.stream_thread = threading.Thread(
            target=self.stream_to_client,
            args=(client_ip,),
            daemon=True
        )
        self.stream_thread.start()

    def stream_to_client(self, client_ip: str):
        log(f"Starting UDP stream to {client_ip}:{UDP_VIDEO_PORT}")
        try:
            while self._stream_event.is_set():
                frame = self.camera.capture_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                try:
                    data = simplejpeg.encode_jpeg(frame, quality=JPEG_QUALITY, colorspace='BGR')
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

                self.frame_id = (self.frame_id + 1) % 4294967296
                self.last_frame_time = time.time()
                
        except Exception as e:
            log(f"UDP Stream error: {e}\n{traceback.format_exc()}")
        finally:
            log(f"Stopped streaming to {client_ip}")
            self._stream_event.clear()

    def stop_stream(self):
        self._stream_event.clear()
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=1.0)
            if self.stream_thread.is_alive():
                log("WARNING! Video stream thread refused to terminate. Camera hardware may be locked.")

    def stop(self):
        self.stop_stream()
        if self.sock:
            try:
                self.sock.close()
                log("Video UDP socket closed")
            except Exception as e:
                log(f"Video socket close error: {e}\n")
            self.sock = None
