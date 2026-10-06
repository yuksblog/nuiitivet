"""Spike: serve the page that tries a second Pyodide in a Web Worker as a process pool's child.

Setup:  npm install            (in the parent directory)
Run:    uv run python scripts/investigation/spike_web_pyodide/worker/serve.py [port]
        then open http://localhost:8770/, or run chrome.mjs
"""

from __future__ import annotations

import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nuiitivet.web.server import build_bundle

HERE = Path(__file__).parent
PYODIDE = HERE.parent / "node_modules" / "pyodide"
TYPES = {".html": "text/html; charset=utf-8", ".mjs": "text/javascript", ".wasm": "application/wasm"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        route = self.path.split("?", 1)[0]
        suffix = Path(route).suffix or ".html"
        if route == "/bundle.zip":
            body = build_bundle(HERE / "app" / "app.py")
        else:
            path = PYODIDE / route[9:] if route.startswith("/pyodide/") else HERE / (route.lstrip("/") or "index.html")
            if not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", TYPES.get(suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    print(f"http://localhost:{port}/")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
