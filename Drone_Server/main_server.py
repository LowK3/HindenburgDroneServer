import threading
from camera_stream import CameraServer
from motor_server import SubmarineServer

def main():
    camera_server = CameraServer(host="0.0.0.0", port=8485)
    motor_server = SubmarineServer(host="0.0.0.0", port=9000)

    t_cam = threading.Thread(target=camera_server.start, daemon=True)
    t_mot = threading.Thread(target=motor_server.start, daemon=True)

    t_cam.start()
    t_mot.start()

    print("[MainServer] Camera and motor servers running. Press Ctrl+C to exit.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n[MainServer] Shutting down.")
        camera_server.stop()
        motor_server.shutdown_event.set()

if __name__ == "__main__":
    main()
