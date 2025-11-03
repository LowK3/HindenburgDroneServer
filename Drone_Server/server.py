import socket
import cv2
import time
import struct
import threading
from picamera2 import Picamera2
import sys
import select

SERVER_PORT = 8485
CHUNK_SIZE = 60000
FRAME_INTERVAL = 0.016
CLIENT_TIMEOUT = 5.0

shutdown_flag = False

def setup_camera():
    cam = Picamera2()
    config = cam.create_video_configuration(
        main = {"size": (1440, 1080),},
        controls = {"FrameRate": 60})
    cam.configure(config)
    cam.start()
    return cam

def setup_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, 25, b"eth0\0")
    s.bind(("0.0.0.0", SERVER_PORT))
    s.settimeout(0.2)
    return s

def listen_for_client(s):
    global shutdown_flag
    print("Waiting for client...")
    last_msg = time.time()

    while not shutdown_flag:
        try:
            data, addr = s.recvfrom(1024)
            if data == b"PC_CLIENT":
                last_msg = time.time()
                print(f"Client connected: {addr}")
                return addr
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Listen error: {e}")
            time.sleep(1)
    return None

def stream_frames(s, cam, client_addr):
    global shutdown_flag
    print("Starting video stream...")
    frame_id = 0
    last_sent = time.time()

    while not shutdown_flag:
        try:
            frame = cam.capture_array()
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

        except (OSError, ConnectionResetError) as e:
            print(f"Connection lost: {e}")
            return

        except Exception as e:
            if time.time() - last_sent > CLIENT_TIMEOUT:
                print("Client timeout, returning to listen mode.")
                return
            time.sleep(0.5)

def check_keyboard():
    # Check if a key is pressed in the terminal (non-blocking)
    global shutdown_flag
    dr, _, _ = select.select([sys.stdin], [], [], 0)
    if dr:
        key = sys.stdin.read(1)
        if key.lower() == 'q':
            print("Shutdown key pressed.")
            shutdown_flag = True

def main():
    global shutdown_flag
    s = setup_socket()
    cam = setup_camera()

    print("Server started. Press 'q' then Enter at any time to shutdown.")

    while not shutdown_flag:
        check_keyboard()
        client_addr = listen_for_client(s)
        if shutdown_flag:
            break
        if client_addr:
            stream_frames(s, cam, client_addr)
            print("Restarting client discovery...")

    print("Server shutting down...")
    cam.stop()
    s.close()

if __name__ == "__main__":
    main()
