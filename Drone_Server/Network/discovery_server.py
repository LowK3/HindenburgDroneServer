# network/discovery.py
import socket
from config import UDP_PORT, TCP_PORT, UDP_TIMEOUT
from Utils.common import log

class DiscoveryServer:
    """
    Listens for 'PC_CLIENT' on UDP and replies 'PI_SERVER:<TCP_PORT>'.
    """

    def __init__(self):
        self.sock = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Try binding to eth0 (Linux only). Fail-soft if not allowed.
        try:
            if hasattr(socket, "SO_BINDTODEVICE"):
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"eth0\0")
        except Exception as e:
            log(f"Could not bind UDP socket to eth0: {e}")
        self.sock.bind(("0.0.0.0", UDP_PORT))
        self.sock.settimeout(UDP_TIMEOUT)
        log(f"Discovery server listening on UDP port {UDP_PORT}")

    def listen_once(self):
        """
        Returns client address if discovered, else None.
        Does NOT block indefinitely (uses UDP_TIMEOUT).
        """
        try:
            data, addr = self.sock.recvfrom(1024)
        except socket.timeout:
            return None
        except Exception as e:
            log(f"Discovery recv error: {e}")
            return None

        if not data:
            return None

        if data == b"PC_CLIENT":
            log(f"Discovery request from {addr}, replying with TCP port {TCP_PORT}")
            reply = f"PI_SERVER:{TCP_PORT}".encode()
            try:
                self.sock.sendto(reply, addr)
            except Exception as e:
                log(f"Discovery reply send error: {e}")
                return None
            return addr

        # Unknown datagram
        log(f"Discovery: unexpected data from {addr}: {data!r}")
        return None

    def stop(self):
        if self.sock:
            try:
                self.sock.close()
                log("Discovery socket closed")
            except Exception as e:
                log(f"Discovery socket close error: {e}")
            self.sock = None
