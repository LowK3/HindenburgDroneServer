import socket
import cv2
import time
import struct
import threading
from picamera2 import Picamera2
import sys
import select

SERVER_PORT = 8485         # TCP port for video stream
DISC_PORT = 37020          # UDP discovery port
JPEG_QUALITY = 100
FRAME_INTERVAL = 0.016     # ~30 FPS (adjust)
CLIENT_TIMEOUT = 5.0
CHUNK_SIZE = 60000         # not used now (TCP handles fragmentation)

shutdown_flag = False

def setup_camera():
    cam = Picamera2()
    # Use a 4:3 resolution to avoid zoom cropping if desired; you can adjust
    config = cam.create_video_configuration(
        main={"size": (1440, 1080), "format": "RGB888"},
        controls={"FrameRate": 30}
    )
    cam.configure(config)
    cam.start()
    return cam

def setup_udp_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # bind to DISC_PORT to receive discovery messages
    s.setsockopt(socket.SOL_SOCKET, 25, b"eth0\0")  # force eth0 (Linux)
    s.bind(("0.0.0.0", DISC_PORT))
    s.settimeout(0.2)
    return s

def setup_tcp_listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("", SERVER_PORT))
    server.listen(1)
    server.settimeout(1.0)
    return server

def check_keyboard():
    global shutdown_flag
    try:
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            key = sys.stdin.read(1)
            if key.lower() == 'q':
                print("Shutdown key pressed.")
                shutdown_flag = True
    except:
        pass

def wait_for_client_udp(udp_sock):
    """Wait for PC_CLIENT discovery broadcast and reply with PI_CAM:port"""
    print("Waiting for discovery (PC_CLIENT)...")
    start = time.time()
    while not shutdown_flag:
        try:
            data, addr = udp_sock.recvfrom(1024)
            if not data:
                continue
            if data == b"PC_CLIENT":
                print(f"Discovery request from {addr}, replying with TCP port.")
                # reply directly to the client with TCP port info
                reply = f"PI_CAM:{SERVER_PORT}".encode()
                try:
                    udp_sock.sendto(reply, addr)
                except Exception as e:
                    print("Failed to send discovery reply:", e)
                return addr  # return addr if needed
        except socket.timeout:
            check_keyboard()
            continue
        except Exception as e:
            print("Discovery error:", e)
            time.sleep(0.5)
    return None

def stream_over_tcp(conn, cam):
    """Stream length-prefixed JPEG frames over the connected TCP socket."""
    print("Starting TCP stream to client:", conn.getpeername())
    frame_id = 0
    last_sent = time.time()
    try:
        while not shutdown_flag:
            check_keyboard()
            if shutdown_flag:
                return False

            frame = cam.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if not ret:
                print("Failed to encode frame")
                continue

            data = jpeg.tobytes()
            # prefix length
            try:
                conn.sendall(struct.pack("<I", len(data)) + data)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                print("TCP send error (client disconnected?)", e)
                return False

            frame_id += 1
            last_sent = time.time()

            # Sleep to keep frame rate stable but allow early exit
            t0 = time.time()
            while time.time() - t0 < FRAME_INTERVAL:
                check_keyboard()
                if shutdown_flag:
                    return False
                time.sleep(0.005)

            # optionally check for new discovery request to allow client switch
            # we will check discovery socket in outer loop

    except Exception as e:
        print("Streaming exception:", e)
        return False

    return False

def main():
    global shutdown_flag
    udp_sock = setup_udp_socket()
    tcp_listener = setup_tcp_listener()
    cam = setup_camera()

    print("Server started. Press 'q' then Enter at any time to shutdown.")

    try:
        while not shutdown_flag:
            check_keyboard()

            # Wait for discovery
            client_addr = wait_for_client_udp(udp_sock)
            if shutdown_flag:
                break
            if not client_addr:
                continue

            # Now wait for TCP connection from that client (or any client)
            print("Waiting for TCP connection from client...")
            tcp_conn = None
            start_wait = time.time()
            while not shutdown_flag and tcp_conn is None:
                try:
                    conn, addr = tcp_listener.accept()
                    print("TCP connection accepted from:", addr)
                    tcp_conn = conn
                    tcp_conn.settimeout(None)
                except socket.timeout:
                    # periodically allow checking discovery socket (so new clients can be discovered)
                    try:
                        # see if a new discovery arrives asking to switch client
                        data, addr = udp_sock.recvfrom(1024)
                        if data == b"PC_CLIENT":
                            print("Another discovery while waiting for TCP connection:", addr)
                            # reply to new discoverer too
                            udp_sock.sendto(f"PI_CAM:{SERVER_PORT}".encode(), addr)
                    except socket.timeout:
                        pass
                    except Exception:
                        pass
                    check_keyboard()
                except Exception as e:
                    print("TCP accept error:", e)
                    time.sleep(0.2)

            if tcp_conn:
                # stream until disconnected or error
                ok = stream_over_tcp(tcp_conn, cam)
                try:
                    tcp_conn.close()
                except:
                    pass
                if not ok:
                    print("Client disconnected or stream ended. Returning to discovery.")
                else:
                    print("Stream ended cleanly. Returning to discovery.")

    except KeyboardInterrupt:
        print("\nCtrl+C received, shutting down...")
        shutdown_flag = True
    except Exception as e:
        print(f"Unexpected error: {e}")
        shutdown_flag = True
    finally:
        print("Server shutting down...")
        try:
            cam.stop()
        except:
            pass
        try:
            udp_sock.close()
        except:
            pass
        try:
            tcp_listener.close()
        except:
            pass

if __name__ == "__main__":
    main()