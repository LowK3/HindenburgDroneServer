import socket, struct, time, traceback, json
from config import CONTROL_TCP_PORT, TCP_SEND_TIMEOUT
from Utils.rasp_telemetry import get_system_telemetry
from Utils.common import log

class ControlServer:
    """ Dedicated TCP server for receiving movement commands. """
    def __init__(self, engine_manager):
        self.engine = engine_manager
        self.sock = None
        self.is_connected = False
        self.running = False
        self.MAX_BUFFER = 4096

    def start(self):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", CONTROL_TCP_PORT))
        self.sock.listen(1)
        log(f"Control server listening on TCP {CONTROL_TCP_PORT}.")

    def accept_client(self):
        """ Blocking accept loop for incoming command connections. """
        while self.running:
            try:
                conn, addr = self.sock.accept()
                conn.settimeout(TCP_SEND_TIMEOUT)
                log(f"Control client connected: {addr}")
                self.handle_client(conn, addr)
            except socket.timeout:
                continue
            except OSError:
                break

    def handle_client(self, conn, addr):
        buffer = b""
        self.is_connected = True
        try:
            while self.running:
                data = conn.recv(1024)
                if not data:
                    break
                buffer += data

                if len(buffer) > self.MAX_BUFFER:
                    log("WARNING! TCP buffer overflow. Dropping corrupted data.")
                    buffer = b""
                    continue
                
                # Extract and execute all complete commands in the buffer
                while b"\n" in buffer:
                    cmd_bytes, buffer = buffer.split(b"\n", 1)
                    try:
                        cmd_str = cmd_bytes.decode('utf-8').strip()
                        if not cmd_str:
                            continue
                        
                        cmd = json.loads(cmd_str)
                        self.engine.execute(cmd)

                        telemetry = get_system_telemetry(self.engine)
                        reply_bytes = (json.dumps(telemetry) + "\n").encode('utf-8')
                        conn.sendall(reply_bytes)
                    except UnicodeDecodeError:
                        log("Ignored command with invalid UTF-8 sequence.")
                    except json.JSONDecodeError:
                        log(f"Ignored malformed JSON command: {cmd_str}")
        except socket.timeout:
            log("Client heartbeat lost! Stopping drone safely.")
        except ConnectionResetError:
            log("Client abruptly disconnected! Stopping drone safely.")
        except Exception as e:
            log(f"Control socket error: {e}\n{traceback.format_exc()}")
        finally:
            self.is_connected = False
            conn.close()
            if self.running:
                self.engine.execute({"cmd": "STOP"})
            log(f"Control client disconnected: {addr}")

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
                log("Control TCP socket closed.")
            except Exception:
                pass
