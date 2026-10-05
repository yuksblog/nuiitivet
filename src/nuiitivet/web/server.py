"""The files of an app's page, served from the source tree or written out as a site."""

from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Iterator, Union

import nuiitivet
from nuiitivet.web.assets import CANVASKIT_CDN, LICENSES, PYODIDE_CDN, RUNTIME, TEXT_FONTS, fetch

# A file on disk, or bytes made at each read.
Source = Union[Path, Callable[[], bytes]]

_PACKAGE = Path(nuiitivet.__file__).parent
STATIC = _PACKAGE / "backends" / "web" / "static"
_SYMBOLS = _PACKAGE / "material" / "symbols"

# Where the page unpacks the bundle in Pyodide's file system.
_PAGE_ROOT = "/nuiitivet"

# The icon font of the default style. The page writes it where the package
# keeps it, so the icon code finds it as on the desktop.
_ICON_FONT = "MaterialSymbolsOutlined[FILL,GRAD,opsz,wght].ttf"
_ICON_FONT_URL = "fonts/MaterialSymbolsOutlined.ttf"

# Pyodide cannot load a native extension built for the desktop.
_NATIVE_SUFFIXES = {".pyc", ".so", ".pyd", ".dylib"}
# The page gets the framework's fonts as files of their own.
_FONT_SUFFIXES = {".ttf", ".otf", ".woff", ".woff2"}
_SKIPPED_DIRS = {"__pycache__", "node_modules", "venv"}

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".mjs": "text/javascript",
    ".js": "text/javascript",
    ".json": "application/json",
    ".wasm": "application/wasm",
    ".zip": "application/zip",
    ".otf": "font/otf",
    ".ttf": "font/ttf",
    ".txt": "text/plain; charset=utf-8",
}


def _source_files(root: Path, skipped_suffixes: set[str]) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        parts = path.relative_to(root).parts
        if any(part in _SKIPPED_DIRS or part.startswith(".") for part in parts):
            continue
        if path.is_file() and path.suffix not in skipped_suffixes:
            yield path


def _package_dir(name: str) -> Path:
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise RuntimeError(f"the package {name!r} is not installed")
    return Path(spec.origin).parent


def build_bundle(app_path: Path) -> bytes:
    """Zip what the page unpacks: the framework under ``lib/``, the app's directory under ``app/``.

    The sources are read at every call, so a browser reload shows an edit.

    Args:
        app_path: The app's entry script. Everything in its directory goes along.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for package in ("nuiitivet", "materialyoucolor"):
            directory = _package_dir(package)
            for path in _source_files(directory, _NATIVE_SUFFIXES | _FONT_SUFFIXES):
                archive.write(path, Path("lib", package, path.relative_to(directory)).as_posix())
        for path in _source_files(app_path.parent, _NATIVE_SUFFIXES):
            archive.write(path, Path("app", path.relative_to(app_path.parent)).as_posix())
    return buffer.getvalue()


def site(app_path: Path, *, bundle_runtime: bool) -> dict[str, Source]:
    """Every file of the app's page, by its path relative to the page.

    The text fonts are downloaded on their first use, and so are the runtimes
    when they are bundled.

    Args:
        app_path: The app's entry script.
        bundle_runtime: ``True`` puts Pyodide and CanvasKit and the licences of
            everything redistributed among the files, so the page needs no
            other server. ``False`` has the page load both from a CDN.
    """
    app_path = app_path.resolve()
    config = {
        "entry": app_path.name,
        "pyodide": "pyodide/" if bundle_runtime else PYODIDE_CDN,
        "canvaskit": "canvaskit/" if bundle_runtime else CANVASKIT_CDN + "bin/",
        "fonts": [{"url": asset.path, "weight": weight} for weight, asset in TEXT_FONTS],
        "files": [{"url": _ICON_FONT_URL, "path": f"{_PAGE_ROOT}/lib/nuiitivet/material/symbols/{_ICON_FONT}"}],
    }
    files: dict[str, Source] = {
        "index.html": STATIC / "index.html",
        "boot.mjs": STATIC / "boot.mjs",
        "host.mjs": STATIC / "host.mjs",
        "config.json": lambda: json.dumps(config).encode(),
        "bundle.zip": lambda: build_bundle(app_path),
        _ICON_FONT_URL: _SYMBOLS / _ICON_FONT,
    }
    for _weight, asset in TEXT_FONTS:
        files[asset.path] = fetch(asset)
    if bundle_runtime:
        for asset in RUNTIME + LICENSES:
            files[asset.path] = fetch(asset)
        files["licenses/material-symbols-LICENSE.txt"] = _SYMBOLS / "LICENSE.txt"
        files["licenses/nuiitivet-LICENSE.txt"] = lambda: _license_of("nuiitivet")
        files["licenses/materialyoucolor-LICENSE.txt"] = lambda: _license_of("materialyoucolor")
    return files


def _license_of(distribution: str) -> bytes:
    """The licence files an installed distribution carries, joined."""
    from importlib import metadata

    dist = metadata.distribution(distribution)
    texts = [
        Path(str(dist.locate_file(file))).read_bytes()
        for file in dist.files or ()
        if "licen" in file.name.lower() and ".dist-info" in str(file)
    ]
    return b"\n\n".join(texts) or f"See the {distribution} distribution for its licence.\n".encode()


def read(source: Source) -> bytes:
    """The bytes of one file of a site."""
    return source.read_bytes() if isinstance(source, Path) else source()


def write_site(files: dict[str, Source], out: Path) -> None:
    """Write a site into ``out``, which any file server can then serve.

    Args:
        files: What :func:`site` returned.
        out: The output directory. Files already there with the same names are replaced.
    """
    for relative, source in files.items():
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(read(source))


def make_server(files: dict[str, Source], port: int) -> ThreadingHTTPServer:
    """A local server for a site.

    Args:
        files: What :func:`site` returned.
        port: The port to listen on; 0 picks a free one.
    """

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            route = self.path.split("?", 1)[0].lstrip("/") or "index.html"
            source = files.get(route)
            if source is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = read(source)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", _CONTENT_TYPES.get(Path(route).suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            # A font never changes under its name; the sources change between reloads.
            self.send_header("Cache-Control", "max-age=86400" if route.startswith("fonts/") else "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


__all__ = ["Source", "build_bundle", "make_server", "read", "site", "write_site"]
