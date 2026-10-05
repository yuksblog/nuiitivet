"""``python -m nuiitivet.web``: open an app in a browser, or build it into a site.

``run app.py`` serves the app and the framework from the source tree, so a
browser reload shows an edit. Its page loads Pyodide and CanvasKit from a CDN.

``build app.py -o dist`` writes a directory that any file server can serve. It
holds Pyodide and CanvasKit as well, so the page loads nothing from elsewhere.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path
from typing import Optional, Sequence

from nuiitivet.web.server import make_server, site, write_site


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m nuiitivet.web", description="Put a nuiitivet app in a browser.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Serve an app from the source tree and open it in a browser.")
    run.add_argument("app", type=Path, help="Path to the app's entry script.")
    run.add_argument("--port", type=int, default=8000, help="Port of the local server (default: 8000).")
    run.add_argument("--no-open", action="store_true", help="Do not open the browser.")

    build = subparsers.add_parser("build", help="Write an app as a directory that any file server can serve.")
    build.add_argument("app", type=Path, help="Path to the app's entry script.")
    build.add_argument("-o", "--out", type=Path, default=Path("dist"), help="Output directory (default: dist).")
    return parser


def _run(args: argparse.Namespace) -> int:
    server = make_server(site(args.app, bundle_runtime=False), args.port)
    url = f"http://localhost:{args.port}/"
    print(f"Serving {args.app} at {url} (Ctrl+C to stop)")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _build(args: argparse.Namespace) -> int:
    write_site(site(args.app, bundle_runtime=True), args.out)
    print(f"Built {args.app} into {args.out}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.app.is_file():
        print(f"app not found: {args.app}", file=sys.stderr)
        return 2
    try:
        return _run(args) if args.command == "run" else _build(args)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
