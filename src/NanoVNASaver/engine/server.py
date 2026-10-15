#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020ff NanoVNA-Saver Authors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Local REST + WebSocket API (standard library only).

Endpoints (JSON):
  GET  /api/info                 device information
  POST /api/sweep                {"start", "stop", "points", "segments",
                                  "averages", "smoothing"} -> sweep data
  GET  /api/last                 last sweep
  GET  /api/touchstone?ports=2   last sweep as Touchstone text
  POST /api/check                {"limits": {...limit spec...}} -> result
  POST /api/continuous           {"enabled": true, ...sweep args}
  GET  /ws                       WebSocket, pushes every new sweep

Only binds to localhost unless told otherwise: there is no
authentication.
"""

import base64
import hashlib
import json
import logging
import socket
import struct
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from .limits import LimitResult, LimitSpec
from .session import VNASession
from .sweepdata import SweepData

logger = logging.getLogger(__name__)

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_BODY = 1 << 20
SWEEP_KEYS = ("points", "segments", "averages", "truncates", "logarithmic")


def sweep_to_json(data: SweepData) -> dict[str, Any]:
    out: dict[str, Any] = {"freq": data.freq.tolist(), "z0": data.z0}
    for name in ("s11", "s21", "s12", "s22"):
        values = data.param(name)
        if values is not None:
            out[name] = {"re": values.real.tolist(), "im": values.imag.tolist()}
    return out


def result_to_json(result: LimitResult) -> dict[str, Any]:
    return {
        "name": result.name,
        "passed": result.passed,
        "segments": [
            {
                "limit": r.segment.describe(),
                "passed": r.passed,
                "skipped": r.skipped,
                "failed_points": r.failed_points,
                "worst_margin": None if r.skipped else r.worst_margin,
                "worst_freq": None if r.skipped else r.worst_freq,
            }
            for r in result.segments
        ],
    }


def ws_frame(text: str) -> bytes:
    payload = text.encode("utf-8")
    n = len(payload)
    if n < 126:
        header = struct.pack("!BB", 0x81, n)
    elif n < 1 << 16:
        header = struct.pack("!BBH", 0x81, 126, n)
    else:
        header = struct.pack("!BBQ", 0x81, 127, n)
    return header + payload


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return buf


def ws_read_frame(sock: socket.socket) -> tuple[int, bytes]:
    b1, b2 = _recv_exact(sock, 2)
    opcode = b1 & 0x0F
    length = b2 & 0x7F
    if length == 126:
        (length,) = struct.unpack("!H", _recv_exact(sock, 2))
    elif length == 127:
        (length,) = struct.unpack("!Q", _recv_exact(sock, 8))
    mask = _recv_exact(sock, 4) if b2 & 0x80 else b"\0\0\0\0"
    data = bytearray(_recv_exact(sock, length))
    for i in range(length):
        data[i] ^= mask[i % 4]
    return opcode, bytes(data)


class ApiState:
    def __init__(self, session: VNASession) -> None:
        self.session = session
        self.clients: set[socket.socket] = set()
        self.clients_lock = threading.Lock()
        self.continuous: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

    def do_sweep(self, args: dict[str, Any]) -> SweepData:
        start = float(args["start"])
        stop = float(args["stop"])
        if "smoothing" in args:
            self.session.smoothing_pct = float(args["smoothing"])
        kwargs = {k: args[k] for k in SWEEP_KEYS if k in args}
        data = self.session.sweep(start, stop, **kwargs)
        self.broadcast(json.dumps({"type": "sweep", **sweep_to_json(data)}))
        return data

    def broadcast(self, text: str) -> None:
        frame = ws_frame(text)
        with self.clients_lock:
            dead = []
            for client in self.clients:
                try:
                    client.sendall(frame)
                except OSError:
                    dead.append(client)
            for client in dead:
                self.clients.discard(client)

    def set_continuous(self, args: dict[str, Any]) -> None:
        self.stop_event.set()
        if self.continuous is not None:
            self.continuous.join(timeout=30)
            self.continuous = None
        if not args.get("enabled"):
            return
        self.stop_event = threading.Event()
        stop = self.stop_event

        def loop() -> None:
            while not stop.is_set():
                try:
                    self.do_sweep(args)
                except (OSError, ValueError, RuntimeError) as exc:
                    logger.error("Continuous sweep failed: %s", exc)
                    self.broadcast(
                        json.dumps({"type": "error", "error": str(exc)})
                    )
                    stop.wait(1.0)

        self.continuous = threading.Thread(target=loop, daemon=True)
        self.continuous.start()


def make_handler(state: ApiState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "NanoVNASaver-API/1.0"

        def log_message(self, fmt: str, *args) -> None:
            logger.debug("%s - %s", self.address_string(), fmt % args)

        def _json(self, payload: Any, status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status: int, message: str) -> None:
            self._json({"error": message}, status)

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_BODY:
                raise ValueError("request too large")
            if length == 0:
                return {}
            return json.loads(self.rfile.read(length))

        def do_GET(self) -> None:
            url = urlparse(self.path)
            session = state.session
            try:
                if url.path == "/api/info":
                    self._json(session.info())
                elif url.path == "/api/last":
                    if session.last is None:
                        self._error(HTTPStatus.NOT_FOUND, "no sweep yet")
                    else:
                        self._json(sweep_to_json(session.last))
                elif url.path == "/api/touchstone":
                    self._touchstone(parse_qs(url.query))
                elif url.path == "/ws":
                    self._websocket()
                else:
                    self._error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            except (RuntimeError, ValueError, OSError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def do_POST(self) -> None:
            url = urlparse(self.path)
            try:
                args = self._body()
                if url.path == "/api/sweep":
                    self._json(sweep_to_json(state.do_sweep(args)))
                elif url.path == "/api/check":
                    spec = LimitSpec.from_dict(args["limits"])
                    self._json(result_to_json(state.session.check(spec)))
                elif url.path == "/api/continuous":
                    state.set_continuous(args)
                    self._json({"continuous": bool(args.get("enabled"))})
                else:
                    self._error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            except (KeyError, TypeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, f"missing/invalid {exc}")
            except (RuntimeError, ValueError, OSError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def _touchstone(self, query: dict[str, list[str]]) -> None:
            data = state.session.last
            if data is None:
                self._error(HTTPStatus.NOT_FOUND, "no sweep yet")
                return
            ports = query.get("ports", ["1"])[0]
            ts = data.to_touchstone()
            if ports == "2":
                zeros = [type(d)(d.freq, 0.0, 0.0) for d in ts.sdata[0]]
                ts.sdata[2] = ts.sdata[2] or zeros
                ts.sdata[3] = ts.sdata[3] or zeros
            body = ts.saves(4 if ports == "2" else 1).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _websocket(self) -> None:
            key = self.headers.get("Sec-WebSocket-Key")
            if (
                not key
                or "websocket" not in self.headers.get("Upgrade", "").lower()
            ):
                self._error(HTTPStatus.BAD_REQUEST, "websocket upgrade needed")
                return
            accept = base64.b64encode(
                hashlib.sha1((key + WS_GUID).encode()).digest()
            ).decode()
            self.send_response(HTTPStatus.SWITCHING_PROTOCOLS)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", accept)
            self.end_headers()
            self.wfile.flush()
            sock = self.connection
            with state.clients_lock:
                state.clients.add(sock)
            try:
                if state.session.last is not None:
                    sock.sendall(
                        ws_frame(
                            json.dumps(
                                {
                                    "type": "sweep",
                                    **sweep_to_json(state.session.last),
                                }
                            )
                        )
                    )
                while True:
                    opcode, payload = ws_read_frame(sock)
                    if opcode == 0x8:  # close
                        sock.sendall(b"\x88\x00")
                        break
                    if opcode == 0x9:  # ping -> pong
                        sock.sendall(bytes([0x8A, len(payload)]) + payload)
            except (ConnectionError, OSError):
                pass
            finally:
                with state.clients_lock:
                    state.clients.discard(sock)
                self.close_connection = True

    return Handler


class ApiServer:
    def __init__(
        self, session: VNASession, host: str = "127.0.0.1", port: int = 8765
    ) -> None:
        self.state = ApiState(session)
        self.httpd = ThreadingHTTPServer((host, port), make_handler(self.state))
        self.httpd.daemon_threads = True
        self.thread: Optional[threading.Thread] = None

    @property
    def address(self) -> tuple[str, int]:
        host, port = self.httpd.server_address[:2]
        return str(host), int(port)

    def start(self) -> "ApiServer":
        self.thread = threading.Thread(
            target=self.httpd.serve_forever, daemon=True
        )
        self.thread.start()
        return self

    def serve_forever(self) -> None:
        self.httpd.serve_forever()

    def stop(self) -> None:
        self.state.set_continuous({"enabled": False})
        self.httpd.shutdown()
        self.httpd.server_close()


__all__ = ["ApiServer", "result_to_json", "sweep_to_json"]
