"""Single-client, newline-delimited JSON server with bounded send time."""
import json
import logging
import select
import socket
import threading
import time

logger = logging.getLogger(__name__)


class TCPServer:
    def __init__(self, host, port, enabled=True, send_timeout=0.05):
        self.host, self.port, self.enabled = host, port, enabled
        self.send_timeout = send_timeout
        self.client_socket = self.server_socket = self.server_thread = None
        self.running = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    def start(self):
        if not self.enabled or self.running:
            return
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(1)
            server.settimeout(0.2)
        except Exception:
            server.close()
            raise
        self.server_socket = server
        self.running = True
        self._stop_event.clear()
        self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
        self.server_thread.start()
        logger.info('TCP监听 %s:%s', self.host, server.getsockname()[1])

    def _drop_client(self):
        # Caller owns _lock.
        if self.client_socket is not None:
            self.client_socket.close()
            self.client_socket = None

    def _server_loop(self):
        while not self._stop_event.is_set():
            with self._lock:
                has_client = self.client_socket is not None
            if not has_client:
                try:
                    client, _ = self.server_socket.accept()
                    client.settimeout(self.send_timeout)
                    with self._lock:
                        if self._stop_event.is_set():
                            client.close()
                            return
                        self.client_socket = client
                except socket.timeout:
                    continue
                except OSError:
                    if not self._stop_event.is_set():
                        logger.exception('TCP接收连接失败')
                    return
            else:
                # Detect disconnects even while no targets are visible/no packets sent.
                with self._lock:
                    client = self.client_socket
                    if client is not None:
                        try:
                            if select.select([client], [], [], 0)[0] and not client.recv(1024):
                                self._drop_client()
                        except OSError:
                            self._drop_client()
                self._stop_event.wait(0.02)

    def send_packet(self, packet):
        if not self.enabled:
            return False
        data = (json.dumps(packet, allow_nan=False) + '\n').encode('utf-8')
        with self._lock:
            if self.client_socket is None:
                return False
            try:
                self.client_socket.sendall(data)
                return True
            except OSError as error:
                logger.warning('TCP发送失败，已断开客户端，等待重连: %s', error)
                self._drop_client()
                return False

    def send_data(self, position, rotation_matrix):
        # Preserve the former single-pose helper for external callers.
        return self.send_packet({
            'position': dict(zip(('x', 'y', 'z'), map(float, position))),
            'rotation_matrix': rotation_matrix.flatten().tolist(),
            'timestamp': time.time(),
        })

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.server_socket is not None:
            self.server_socket.close()
        with self._lock:
            self._drop_client()
        if self.server_thread is not None:
            self.server_thread.join(timeout=1.0)
        self.server_socket = self.server_thread = None
