import socket, struct, time
from config import CONTROL_TCP_PORT, TCP_SEND_TIMEOUT
from Utils.common import log

class ControlServer:
    """ Dedicated TCP server for receiving movement commands. """

    def __init__(self, engine_manager):
        self.engine = engine_manager
        self.sock = None
        self.is_connected = False

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", CONTROL_TCP_PORT))
        self.sock.listen(1)
        log(f"Control server listening on TCP {CONTROL_TCP_PORT}.")

    def accept_client(self, shutdown_flag):
        """ Blocking accept loop for incoming command connections. """

        while not shutdown_flag():
            try:
                conn, addr = self.sock.accept()
                conn.settimeout(TCP_SEND_TIMEOUT)
                log(f"Control client connected: {addr}")
                self.handle_client(conn, addr, shutdown_flag)
            except socket.timeout:
                continue

    def handle_client(self, conn, addr, shutdown_flag):
        buffer = ""
        self.is_connected = True
        try:
            while not shutdown_flag():
                data = conn.recv(1024)
                if not data:
                    break
                buffer += data.decode()
                
                # Extract and execute all complete commands in the buffer
                while "\n" in buffer:
                    cmd, buffer = buffer.split("\n", 1)
                    cmd = cmd.strip()
                    if cmd:
                        self.engine.execute(cmd)
        except Exception as e:
            log(f"Control socket error: {e}")
        finally:
            self.is_connected = False
            conn.close()
            self.engine.execute("STOP")
            log(f"Control client disconnected: {addr}")

    def stop(self):
        if self.sock:
            self.sock.close()
            log("Control TCP socket closed.")
