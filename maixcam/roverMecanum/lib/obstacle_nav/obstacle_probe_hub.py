"""TCP text log for obstacle / stuck probes (readable from a PC)."""

from __future__ import annotations

import socket
import threading


class ObstacleProbeHub:
  """Broadcast newline text probes to any TCP clients (e.g. ``nc IP 9400``)."""

  def __init__(self, port: int = 9400) -> None:
    """Create a stopped hub."""
    self._port = max(1, int(port))
    self._sock: socket.socket | None = None
    self._clients: list[socket.socket] = []
    self._lock = threading.Lock()
    self._thread: threading.Thread | None = None
    self._stop = threading.Event()

  def start(self) -> None:
    """Bind and accept clients on a background thread."""
    if self._thread is not None:
      return
    self._stop.clear()
    try:
      listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      listener.bind(("0.0.0.0", self._port))
      listener.listen(2)
      listener.settimeout(0.5)
      self._sock = listener
    except OSError as bind_error:
      print(f"obstacle probe hub: bind :{self._port} failed: {bind_error}")
      return
    self._thread = threading.Thread(target=self._accept_loop, daemon=True)
    self._thread.start()
    print(f"obstacle probe hub: tcp://0.0.0.0:{self._port} (nc <cam-ip> {self._port})")

  def stop(self) -> None:
    """Close listener and clients."""
    self._stop.set()
    with self._lock:
      for client in self._clients:
        try:
          client.close()
        except OSError as close_error:
          print(f"obstacle probe hub: client close: {close_error}")
      self._clients.clear()
      listener = self._sock
      self._sock = None
    if listener is not None:
      try:
        listener.close()
      except OSError as close_error:
        print(f"obstacle probe hub: listener close: {close_error}")
    thread = self._thread
    self._thread = None
    if thread is not None:
      thread.join(timeout=1.0)

  def publish(self, line: str) -> None:
    """Send one text line to every connected client (best-effort)."""
    payload = (line.rstrip() + "\n").encode("utf-8", "replace")
    dead: list[socket.socket] = []
    with self._lock:
      clients = list(self._clients)
    for client in clients:
      try:
        client.sendall(payload)
      except OSError:
        dead.append(client)
    if not dead:
      return
    with self._lock:
      for client in dead:
        if client in self._clients:
          self._clients.remove(client)
        try:
          client.close()
        except OSError as close_error:
          print(f"obstacle probe hub: dead client close: {close_error}")

  def _accept_loop(self) -> None:
    while not self._stop.is_set():
      listener = self._sock
      if listener is None:
        return
      try:
        client, addr = listener.accept()
      except socket.timeout:
        client = None
        addr = None
      except OSError as accept_error:
        print(f"obstacle probe hub: accept: {accept_error}")
        return
      if client is None:
        continue
      try:
        client.settimeout(0.0)
      except OSError as timeout_error:
        print(f"obstacle probe hub: settimeout: {timeout_error}")
      with self._lock:
        self._clients.append(client)
      print(f"obstacle probe hub: client {addr[0]}:{addr[1]}")
      try:
        client.sendall(b"obstacle probe hub ready\n")
      except OSError as greet_error:
        print(f"obstacle probe hub: greet: {greet_error}")
