"""API HTTP de solo lectura, ligada exclusivamente a 127.0.0.1."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from apc.publisher.telemetry import TelemetryStore


class TelemetryPublisher:
    def __init__(self, store: TelemetryStore, port: int = 8765):
        self.store = store
        self.port = port
        self._server = None
        self._thread = None

    def __enter__(self):
        store = self.store

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/telemetry":
                    status, payload = 200, store.snapshot()
                elif self.path == "/health":
                    status, payload = 200, {"ok": 1}
                else:
                    status, payload = 404, {"error": 404}
                body = json.dumps(payload, allow_nan=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_):
                # No mantener un registro de telemetría ni de clientes.
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self.port = self._server.server_port
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
