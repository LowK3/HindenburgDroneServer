import socket 
import traceback
import json
import threading
from config import (
    CONTROL_TCP_PORT, TCP_SEND_TIMEOUT, TCP_BUFFER_SIZE, TCP_RECV_CHUNK, 
    TCP_ACCEPT_TIMEOUT
)
from Utils.common import log

class ControlServer:
    """ Dedicated TCP server for receiving movement commands. """
    def __init__(self, thruster_mgr, telemetry_gatherer, camera_status_callback):
        self.thruster = thruster_mgr
        self.telemetry = telemetry_gatherer
        self.get_camera_status = camera_status_callback
        self.connected_event = threading.Event()
        self.disconnected_event = threading.Event()
        self.disconnected_event.set()
        self._stop_event = threading.Event()
        self.sock = None
        self.is_connected = False

    def start(self):
        self._stop_event.clear()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", CONTROL_TCP_PORT))
        self.sock.listen(1)
        self.sock.settimeout(TCP_ACCEPT_TIMEOUT)
        log(f"Control server listening on TCP {CONTROL_TCP_PORT}.")

    def accept_client(self):
        """ Blocking accept loop for incoming command connections. """
        while not self._stop_event.is_set():
            try:
                conn, addr = self.sock.accept()
                # Disable Nagle's Algorithm to prevent artificial latency
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(TCP_SEND_TIMEOUT)
                log(f"Control client connected: {addr}")
                self.handle_client(conn, addr)
            except socket.timeout:
                continue
            except OSError:
                break

    def handle_client(self, conn: socket.socket, addr: tuple):
        buffer = bytearray()
        self.is_connected = True
        self.connected_event.set()
        self.disconnected_event.clear()
        try:
            while not self._stop_event.is_set():
                data = conn.recv(TCP_RECV_CHUNK)
                if not data:
                    break
                buffer.extend(data)

                if len(buffer) > TCP_BUFFER_SIZE:
                    log("WARNING! TCP buffer overflow. Dropping corrupted data.")
                    buffer.clear()
                    continue
                
                self._process_buffer(buffer, conn)
                
        except (socket.timeout, ConnectionResetError) as e:
            log(f"Client disconnected abruptly: {type(e).__name__}. Stopping drone safely.")
        except Exception as e:
            log(f"Control socket error: {e}\n{traceback.format_exc()}")
        finally:
            self._cleanup_connection(conn, addr)

    def _process_buffer(self, buffer: bytearray, conn: socket.socket):
        while (newline_idx := buffer.find(b"\n")) != -1:
            cmd_bytes = buffer[:newline_idx]
            del buffer[:newline_idx + 1]
            try:
                cmd_str = cmd_bytes.decode('utf-8').strip()
                if not cmd_str:
                    continue
                
                self._execute_command(cmd_str)
                self._send_telemetry(conn)
            except UnicodeDecodeError:
                log("Ignored command with invalid UTF-8 sequence.")

    def _execute_command(self, cmd_str: str):
        try:
            cmd = json.loads(cmd_str)
            cmd_type = cmd.get("cmd", "").upper()
            if cmd_type != "PING":
                self.thruster.execute(cmd)
        except json.JSONDecodeError:
            log(f"Ignored malformed JSON command: {cmd_str}")

    def _send_telemetry(self, conn: socket.socket):
        telemetry_data = self.telemetry.get_state()
        telemetry_data["camera_status"] = self.get_camera_status()
        reply_bytes = (json.dumps(telemetry_data) + "\n").encode('utf-8')
        conn.sendall(reply_bytes)
        
    def _cleanup_connection(self, conn: socket.socket, addr: tuple):
        self.is_connected = False
        self.connected_event.clear()
        self.disconnected_event.set()
        conn.close()
        if not self._stop_event.is_set():
            self.thruster.execute({"cmd": "STOP"})
        log(f"Control client disconnected: {addr}")

    def stop(self):
        self._stop_event.set()
        if self.sock:
            try:
                self.sock.close()
                log("Control TCP socket closed.")
            except Exception:
                pass
