import socket
import cv2
import time
import struct
import threading
from picamera2 import Picamera2

SERVER_PORT = 8485
CHUNK_SIZE = 60000
FRAME_INTERVAL = 0.016
CLIENT_TIMEOUT = 5.0

def setup_camera():
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main = {"size": (1440, 1080),},
        controls = {"FrameRate": 60})
    picam2.configure(config)
    picam2.start()
    return picam2

def setup_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, 25, b"eth0\0")
    s.bind(("0.0.0.0", SERVER_PORT))
    s.settimeout(0.2)
    return s

def listen_for_client(s):
    print("Waiting for client...")
    last_hello = time.time()
    client_addr = None

    while True:
        try:
            data, addr = s.recvfrom(1024)
            if data == b"PC_CLIENT":
                client_addr = addr
                last_hello = time.time()
                print(f"Client connected: {addr}")
                return client_addr
        except socket.timeout:
            pass
        except Exception as e:
            print("Listen error:", e)
            time.sleep(1)

def stream_frames(s, picam2, client_addr):
    print("Starting video stream...")
    frame_id = 0
    last_sent = time.time()

    while True:
        try:
            frame = picam2.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                continue

            data = jpeg.tobytes()
            for i in range(0, len(data), CHUNK_SIZE):
                chunk = data[i:i + CHUNK_SIZE]
                header = struct.pack("<III", frame_id, i // CHUNK_SIZE, len(data))
                s.sendto(header + chunk, client_addr)

            frame_id += 1
            last_sent = time.time()
            time.sleep(FRAME_INTERVAL)

        except (OSError, ConnectionResetError):
            print("Lost connection to client.")
            return

        except Exception as e:
            if time.time() - last_sent > CLIENT_TIMEOUT:
                print("Client timeout, returning to listen mode.")
                return
            time.sleep(0.1)

def main():
    s = setup_socket()
    picam2 = setup_camera()

    while True:
        client_addr = listen_for_client(s)
        stream_frames(s, picam2, client_addr)
        print("Restarting client discovery...")

if __name__ == "__main__":
    main()
