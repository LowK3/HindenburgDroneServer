import socket 
import traceback
import json
import threading
import select
from config import (
    CONTROL_TCP_PORT, TCP_SEND_TIMEOUT, TCP_BUFFER_SIZE, TCP_RECV_CHUNK, 
    TCP_ACCEPT_TIMEOUT, TCP_WAKE_SIGNAL, TCP_WAKE_RECV_CHUNK, TCP_BACKLOG,
    TCP_ENCODING, TCP_CMD_PING, TCP_CMD_STOP, TCP_TELEMETRY_CATEGORIES
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

        self._update_lock = threading.Lock()
        self._pending_updates = set()

        self._wake_reader = None
        self._wake_writer = None

        self.telemetry.set_update_callback(self._telemetry_update)

        self._telemetry_getters = {
            "IMU": self.telemetry.get_imu,
            "THRUSTERS": self.telemetry.get_thrusters,
            "LEAK": self.telemetry.get_leak,
            "ENVIRONMENT": self.telemetry.get_environment
        }

    def _create_wake_sockets(self):
        """Creates the socket pair used for telemetry notifications."""
        with self._update_lock:
            if self._wake_reader is not None:
                return

            self._wake_reader, self._wake_writer = socket.socketpair()
            self._wake_reader.setblocking(False)
            self._wake_writer.setblocking(False)


    def _close_wake_sockets(self):
        """Closes the telemetry notification socket pair."""
        with self._update_lock:
            for wake_socket in (self._wake_reader, self._wake_writer):
                if wake_socket is not None:
                    try:
                        wake_socket.close()
                    except OSError:
                        pass

            self._wake_reader = None
            self._wake_writer = None

    def _telemetry_update(self, category: str):
        """Queues a telemetry update and wakes the TCP handler."""
        with self._update_lock:
            self._pending_updates.add(category)

            if self._wake_writer is None:
                return

            try:
                self._wake_writer.send(TCP_WAKE_SIGNAL)
            except BlockingIOError:
                # Wake-up signal is already pending in the socket buffer
                pass
            except OSError:
                if not self._stop_event.is_set():
                    log("Telemetry wake-up socket error.")


    def _get_pending_updates(self):
        """Returns and clears pending telemetry categories."""
        with self._update_lock:
            pending = self._pending_updates.copy()
            self._pending_updates.clear()

        return pending


    def _drain_wake_socket(self):
        """Clears pending wake-up signals."""
        try:
            while self._wake_reader.recv(TCP_WAKE_RECV_CHUNK):
                pass
        except BlockingIOError:
            pass

    def start(self):
        self._stop_event.clear()
        self._create_wake_sockets()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", CONTROL_TCP_PORT))
        self.sock.listen(TCP_BACKLOG)
        self.sock.settimeout(TCP_ACCEPT_TIMEOUT)
        log(f"Control server listening on TCP {CONTROL_TCP_PORT}.")

    def accept_client(self):
        """ Blocking accept loop for incoming command connections. """
        try:
            while not self._stop_event.is_set():
                try:
                    conn, addr = self.sock.accept()
                    # Disable Nagle's Algorithm to prevent artificial latency
                    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    conn.settimeout(TCP_SEND_TIMEOUT)
                    log(f"Control client connected: {addr}")
                    self._handle_client(conn, addr)
                except socket.timeout:
                    continue
                except OSError:
                    break
        finally:
            self._close_wake_sockets()

    def _handle_client(self, conn: socket.socket, addr: tuple):
        buffer = bytearray()
        self.is_connected = True
        self.connected_event.set()
        self.disconnected_event.clear()
        try:
            while not self._stop_event.is_set():
                # Wait for incoming commands or telemetry update notifications
                readable, _, _ = select.select(
                    [conn, self._wake_reader],
                    [],
                    [],
                    None
                )

                if self._stop_event.is_set():
                    break

                # Drain wake-up signals
                if self._wake_reader in readable:
                    self._drain_wake_socket()

                # Process incoming control commands first
                if conn in readable:
                    try:
                        data = conn.recv(TCP_RECV_CHUNK)
                    except socket.timeout:
                        data = None

                    if data == b"":
                        break

                    if data:
                        buffer.extend(data)
                        self._process_buffer(buffer)

                        if len(buffer) > TCP_BUFFER_SIZE:
                            log("WARNING! TCP buffer overflow. Dropping corrupted data.")
                            buffer.clear()

                # Send the latest state of each pending category
                pending = self._get_pending_updates()

                for category in TCP_TELEMETRY_CATEGORIES:
                    if category in pending:
                        self._send_telemetry(conn, category)
                
        except (socket.timeout, ConnectionResetError, BrokenPipeError) as e:
            log(f"Client disconnected abruptly: {type(e).__name__}. Stopping drone safely.")
        except Exception as e:
            log(f"Control socket error: {e}\n{traceback.format_exc()}")
        finally:
            self._cleanup_connection(conn, addr)

    def _send_telemetry(self, conn: socket.socket, category: str):
        telemetry_data = self._telemetry_getters[category]()
        telemetry_data["type"] = category

        if category == "ENVIRONMENT":
            try:
                telemetry_data["camera_status"] = self.get_camera_status()
            except Exception:
                telemetry_data["camera_status"] = None

        reply_bytes = (json.dumps(telemetry_data) + "\n").encode(TCP_ENCODING)
        conn.sendall(reply_bytes)

    def _process_buffer(self, buffer: bytearray):
        while (newline_idx := buffer.find(b"\n")) != -1:
            cmd_bytes = buffer[:newline_idx]

            # Delete the processed bytes from the buffer to free memory
            del buffer[:newline_idx + 1]
            try:
                cmd_str = cmd_bytes.decode(TCP_ENCODING).strip()
                if not cmd_str:
                    continue
                
                self._execute_command(cmd_str)
            except UnicodeDecodeError:
                log("Ignored command with invalid UTF-8 sequence.")

    def _execute_command(self, cmd_str: str):
        try:
            cmd = json.loads(cmd_str)
            cmd_type = cmd.get("cmd", "").upper()
            if cmd_type != TCP_CMD_PING:
                self.thruster.execute(cmd)
        except json.JSONDecodeError:
            log(f"Ignored malformed JSON command: {cmd_str}")
        
    def _cleanup_connection(self, conn: socket.socket, addr: tuple):
        self.is_connected = False
        self.connected_event.clear()
        self.disconnected_event.set()
        conn.close()
        if not self._stop_event.is_set():
            self.thruster.execute({"cmd": TCP_CMD_STOP})
        log(f"Control client disconnected: {addr}")

    def stop(self):
        self._stop_event.set()

        # Wake the TCP handler if it is waiting for socket activity
        with self._update_lock:
            if self._wake_writer is not None:
                try:
                    self._wake_writer.send(TCP_WAKE_SIGNAL)
                except (BlockingIOError, OSError):
                    pass

        if self.sock:
            try:
                self.sock.close()
                log("Control TCP socket closed.")
            except Exception:
                pass
