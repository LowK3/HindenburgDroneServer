import socket
from config import UDP_PORT, TCP_PORT

class DiscoveryServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("0.0.0.0", UDP_PORT))
        self.sock.settimeout(0.2)

    def listen(self):
        try:
            data, addr = self.sock.recvfrom(1024)
            if data == b"PC_CLIENT":
                reply = f"PI_SERVER:{TCP_PORT}".encode()
                self.sock.sendto(reply, addr)
                return addr
        except Exception:
            return None
