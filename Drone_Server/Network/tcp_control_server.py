import socket, struct, time, traceback, json, threading
from config import CONTROL_TCP_PORT, TCP_SEND_TIMEOUT
from Utils.common import log

class ControlServer:
    """ Dedicated TCP server for receiving movement commands. """
    def __init__(self, engine_manager, telemetry_gatherer, camera_status: bool):
        self.engine = engine_manager
        self.telemetry = telemetry_gatherer
        self.camera_status = camera_status
        self.connected_event = threading.Event()
        self.sock = None
        self.is_connected = False
        self.running = False
        self.max_buffer = 4096

    def start(self):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", CONTROL_TCP_PORT))
        self.sock.listen(1)
        self.sock.settimeout(1.0)
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
        buffer = bytearray()
        self.is_connected = True
        self.connected_event.set()
        try:
            while self.running:
                data = conn.recv(1024)
                if not data:
                    break
                buffer.extend(data)

                if len(buffer) > self.max_buffer:
                    log("WARNING! TCP buffer overflow. Dropping corrupted data.")
                    buffer.clear()
                    continue
                
                # Extract and execute all complete commands in the buffer
                while (newline_idx := buffer.find(b"\n")) != -1:
                    cmd_bytes = buffer[:newline_idx]
                    del buffer[:newline_idx + 1]
                    try:
                        cmd_str = cmd_bytes.decode('utf-8').strip()
                        if not cmd_str:
                            continue
                        
                        cmd = json.loads(cmd_str)
                        cmd_type = cmd.get("cmd", "").upper()

                        if cmd_type != "PING":
                            self.engine.execute(cmd)

                        telemetry_data = self.telemetry.get_state()
                        telemetry_data["camera_status"] = self.camera_status

                        reply_bytes = (json.dumps(telemetry_data) + "\n").encode('utf-8')
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
            self.connected_event.clear()
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
