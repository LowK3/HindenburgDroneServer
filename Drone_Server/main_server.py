import time
from network.discovery_server import DiscoveryServer
from network.tcp_video_server import TCPServer
from hardware.camera_manager import Camera

def main():
    cam = Camera()
    disc = DiscoveryServer()
    server = TCPServer(cam)

    print("Server ready.")
    while True:
        addr = disc.listen()
        if addr:
            print("Discovery from", addr)
            server.serve_once()

if __name__ == "__main__":
    main()
