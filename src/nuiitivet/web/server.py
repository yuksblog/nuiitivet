"""Serve an app to a browser straight from the source tree."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator, Optional

import nuiitivet

STATIC = Path(nuiitivet.__file__).parent / "backends" / "web" / "static"

_PAGE_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/boot.mjs": ("boot.mjs", "text/javascript"),
    "/host.mjs": ("host.mjs", "text/javascript"),
}

# Pyodide cannot load a native extension built for the desktop, and fonts
# reach the page on their own.
_SKIPPED_SUFFIXES = {".pyc", ".so", ".pyd", ".dylib", ".ttf", ".otf", ".woff", ".woff2"}
_SKIPPED_DIRS = {"__pycache__", "node_modules", "venv"}

_DEFAULT_FONTS = {
    "darwin": ("/System/Library/Fonts/Supplemental/Arial.ttf",),
    "win32": ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"),
    "linux": (
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ),
}


def default_font() -> Optional[Path]:
    """A font file of this machine for the page's text, or ``None`` when none is known."""
    for candidate in _DEFAULT_FONTS.get(sys.platform, ()):
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def _source_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        parts = path.relative_to(root).parts
        if any(part in _SKIPPED_DIRS or part.startswith(".") for part in parts):
            continue
        if path.is_file() and path.suffix not in _SKIPPED_SUFFIXES:
            yield path


def _package_dir(name: str) -> Path:
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise RuntimeError(f"the package {name!r} is not installed")
    return Path(spec.origin).parent


def build_bundle(app_path: Path) -> bytes:
    """Zip what the page unpacks: the framework under ``lib/``, the app's directory under ``app/``.

    The sources are read at every call, so a browser reload shows an edit.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for package in ("nuiitivet", "materialyoucolor"):
            directory = _package_dir(package)
            for path in _source_files(directory):
                archive.write(path, Path("lib", package, path.relative_to(directory)).as_posix())
        for path in _source_files(app_path.parent):
            archive.write(path, Path("app", path.relative_to(app_path.parent)).as_posix())
    return buffer.getvalue()


def make_server(app_path: Path, font: Path, port: int) -> ThreadingHTTPServer:
    """A local server for the app at ``app_path``, with ``font`` as the page's one typeface."""
    app_path = app_path.resolve()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            route = self.path.split("?", 1)[0]
            if route in _PAGE_FILES:
                name, content_type = _PAGE_FILES[route]
                self._send((STATIC / name).read_bytes(), content_type)
            elif route == "/config.json":
                self._send(json.dumps({"entry": app_path.name}).encode(), "application/json")
            elif route == "/bundle.zip":
                self._send(build_bundle(app_path), "application/zip")
            elif route == "/font.ttf":
                self._send(font.read_bytes(), "font/ttf")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def _send(self, body: bytes, content_type: str) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            # The sources change between reloads.
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


__all__ = ["build_bundle", "default_font", "make_server"]
