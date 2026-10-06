"""``python -m nuiitivet.web``: open an app in a browser, build it, or serve what was built.

``run app.py`` serves the app and the framework from the source tree, so a
browser reload shows an edit. Its page loads Pyodide and CanvasKit from a CDN.
The app's ``@server`` functions answer from the same process; an edit to a
server-only module needs a restart.

``build app.py -o dist`` writes ``dist/site``, the page with Pyodide and
CanvasKit so it loads nothing from elsewhere, and ``dist/server``, the app's
sources for the server functions.

``serve dist`` serves both: the site, and the calls of the server functions.
An app without server functions needs only ``dist/site`` and any file server.
"""

from __future__ import annotations

import argparse
import errno
import sys
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Optional, Sequence

from nuiitivet.web.server import load_server_functions, make_server, site, site_files, write_server, write_site


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

    serve = subparsers.add_parser("serve", help="Serve a built app: its site and its server functions.")
    serve.add_argument("dist", type=Path, help="The directory build wrote.")
    serve.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000).")
    serve.add_argument("--host", default="127.0.0.1", help="Address to listen on (default: 127.0.0.1).")
    return parser


def _serve_forever(server: ThreadingHTTPServer) -> None:
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _run(args: argparse.Namespace) -> int:
    load_server_functions(args.app.parent)
    server = make_server(site(args.app, bundle_runtime=False), args.port)
    url = f"http://localhost:{args.port}/"
    print(f"Serving {args.app} at {url} (Ctrl+C to stop)")
    if not args.no_open:
        webbrowser.open(url)
    _serve_forever(server)
    return 0


def _build(args: argparse.Namespace) -> int:
    write_site(site(args.app, bundle_runtime=True), args.out / "site")
    write_server(args.app, args.out / "server")
    print(f"Built {args.app} into {args.out}")
    return 0


def _serve(args: argparse.Namespace) -> int:
    load_server_functions(args.dist / "server")
    server = make_server(site_files(args.dist / "site"), args.port, host=args.host)
    print(f"Serving {args.dist} at http://{args.host}:{args.port}/ (Ctrl+C to stop)")
    _serve_forever(server)
    return 0


_COMMANDS = {"run": _run, "build": _build, "serve": _serve}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "serve":
        if not (args.dist / "site").is_dir():
            print(f"not a built app: {args.dist}", file=sys.stderr)
            return 2
    elif not args.app.is_file():
        print(f"app not found: {args.app}", file=sys.stderr)
        return 2
    try:
        return _COMMANDS[args.command](args)
    except OSError as error:
        if error.errno == errno.EADDRINUSE:
            print(f"port {args.port} is already in use; pick another with --port", file=sys.stderr)
        else:
            print(error, file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
