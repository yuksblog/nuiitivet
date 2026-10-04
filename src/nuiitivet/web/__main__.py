"""``python -m nuiitivet.web run app.py``: open an app in a browser, with no build.

The command serves the app and the framework from the source tree, so a
browser reload shows an edit. The page loads Pyodide and CanvasKit from a CDN.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path
from typing import Optional, Sequence

from nuiitivet.web.server import default_font, make_server


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m nuiitivet.web", description="Put a nuiitivet app in a browser.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Serve an app from the source tree and open it in a browser.")
    run.add_argument("app", type=Path, help="Path to the app's entry script.")
    run.add_argument("--port", type=int, default=8000, help="Port of the local server (default: 8000).")
    run.add_argument("--no-open", action="store_true", help="Do not open the browser.")
    return parser


def _run(args: argparse.Namespace) -> int:
    if not args.app.is_file():
        print(f"app not found: {args.app}", file=sys.stderr)
        return 2
    font = default_font()
    if font is None:
        print("no font file of this OS was found for the page's text", file=sys.stderr)
        return 2

    server = make_server(args.app, font, args.port)
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    return _run(args)


if __name__ == "__main__":
    sys.exit(main())
