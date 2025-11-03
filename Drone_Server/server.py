import socket
import cv2
import time
import struct
import threading
from picamera2 import Picamera2

SERVER_PORT = 8485
CHUNK_SIZE = 60000
FRAME_INTERVAL = 0.015

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
    return s

def listen_for_client(s):
    print("Waiting for client...")
    while True:
        try:
            data, addr = s.recvfrom(1024)
            if data == b"PC_CLIENT":
                print(f"Client connected: {addr}")
                return addr
        except Exception as e:
            print("Listen error:", e)
            time.sleep(1)

def main():
    s = setup_socket()
    cam = setup_camera()
    frame_id = 0
    client_addr = None

    while True:
        if not client_addr:
            client_addr = listen_for_client(s)
            continue

        try:
            frame = cam.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            data = jpeg.tobytes()

            for i in range(0, len(data), CHUNK_SIZE):
                chunk = data[i:i + CHUNK_SIZE]
                header = struct.pack("<III", frame_id, i // CHUNK_SIZE, len(data))
                s.sendto(header + chunk, client_addr)

            frame_id += 1
            time.sleep(FRAME_INTERVAL)

        except (OSError, ConnectionResetError) as e:
            print(f"Connection lost ({e}). Reconnecting...")
            client_addr = None
            time.sleep(2)

        except Exception as e:
            print("Unexpected error:", e)
            client_addr = None
            time.sleep(1)

if __name__ == "__main__":
    main()
