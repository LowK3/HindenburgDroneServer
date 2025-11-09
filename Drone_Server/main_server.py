import threading
import time
from camera_stream import CameraServer
from control_server import SubmarineServer

control_server = None

def run_control(host="0.0.0.0", port=9000):
    global control_server
    try:
        control_server = SubmarineServer(host=host, port=port)
        control_server.start()
    except Exception as e:
        # Initialization failed (e.g. pigpio daemon not running)
        print(f"[MainServer] Control server failed to start: {e}")

def main():
    camera_server = CameraServer(host="0.0.0.0", port=8485)

    t_cam = threading.Thread(target=camera_server.start, daemon=True)
    t_mot = threading.Thread(target=run_control, args=("0.0.0.0", 9000), daemon=True)

    t_cam.start()
    t_mot.start()

    print("[MainServer] Camera and motor servers running. Press Ctrl+C to exit.")
    try:
        # don't busy-wait; sleep to reduce CPU use and allow KeyboardInterrupt
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MainServer] Shutting down.")
        camera_server.stop()
        if control_server:
            control_server.shutdown_event.set()
    # allow threads a moment to clean up
    time.sleep(1)

if __name__ == "__main__":
    main()