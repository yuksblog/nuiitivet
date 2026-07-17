"""Entry point for ``python -m nuiitivet.dev`` — run apps and inspect them live.

Subcommands::

    python -m nuiitivet.dev run path/to/app.py     # launch with hot reload
    python -m nuiitivet.dev path/to/app.py          # same (run is the default)
    python -m nuiitivet.dev --module yourpkg.app    # dotted module name
    python -m nuiitivet.dev describe-tree           # dump the running app's tree
    python -m nuiitivet.dev screenshot -o out.png   # screenshot the running app

``run`` imports the user's app module under its real name (never ``__main__``,
so importing it does not run ``main()``), installs a dev session, calls the
entry once, then drives the event loop with file watching and the dev bridge
enabled. ``describe-tree`` and ``screenshot`` are bridge clients: they talk to an
already-running ``run`` process over localhost. See ``docs/design/HOT_RELOAD.md``
and #374.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .bridge import DevBridge
from .client import BridgeClient, BridgeNotFoundError
from .controller import HotReloadController
from .loader import load_app_module, resolve_entry
from .session import DevSession, set_dev_session

# Subcommands that may appear as the first token. Anything else is treated as a
# ``run`` target so ``python -m nuiitivet.dev app.py`` keeps working.
_SUBCOMMANDS = frozenset({"run", "screenshot", "describe-tree"})


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m nuiitivet.dev",
        description="Run a nuiitivet app with hot reload, or inspect a running one.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="Run an app with in-process hot reload.")
    run.add_argument(
        "target",
        help="Path to the app file (e.g. app.py), or a dotted module name with --module.",
    )
    run.add_argument(
        "--module",
        action="store_true",
        help="Treat 'target' as a dotted module name (yourpkg.app) instead of a file path.",
    )
    run.add_argument(
        "--entry",
        default="main",
        help="Name of the entry function to call (default: main).",
    )
    run.add_argument(
        "--poll-interval",
        type=float,
        default=0.4,
        help="File-watch poll interval in seconds (default: 0.4).",
    )

    subparsers.add_parser("describe-tree", help="Print the running app's widget tree as JSON.")

    shot = subparsers.add_parser("screenshot", help="Save a PNG screenshot of the running app.")
    shot.add_argument(
        "-o",
        "--output",
        default="screenshot.png",
        help="Where to write the PNG (default: screenshot.png; '-' for stdout).",
    )

    return parser


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    args = list(sys.argv[1:] if argv is None else argv)
    # Backward compat / ergonomics: if no explicit subcommand leads, assume 'run'.
    if not args or (args[0] not in _SUBCOMMANDS and not (args[0] == "-h" or args[0] == "--help")):
        args = ["run", *args]
    return _build_parser().parse_args(args)


def _run(args: argparse.Namespace) -> int:
    session = DevSession()
    set_dev_session(session)
    try:
        loaded = load_app_module(args.target, is_module=args.module)
        entry = resolve_entry(loaded.module, args.entry)

        # Run the user's entry once. It builds the App and calls App.run(), which
        # detects the session and hands off instead of blocking.
        entry()

        if not session.attached or session.app is None or session.root_factory is None:
            print(
                f"[nuiitivet.dev] '{loaded.name}.{args.entry}()' did not call App.run(). "
                "Hot reload needs your entry to build an App and call app.run().",
                file=sys.stderr,
            )
            return 1

        app = session.app
        controller = HotReloadController(
            app,
            loaded.project_root,
            session.root_factory,
            poll_interval=args.poll_interval,
        )
        bridge = DevBridge(app, loaded.project_root)

        print(
            f"[nuiitivet.dev] hot reload active for '{loaded.name}' "
            f"(watching {loaded.project_root}). Save a file to reload.",
            file=sys.stderr,
        )

        from nuiitivet.backends.pyglet.runner import run_app

        controller.install()
        bridge.install()
        bridge.start()
        print(
            f"[nuiitivet.dev] dev bridge listening on 127.0.0.1:{bridge.port} "
            "(describe-tree / screenshot).",
            file=sys.stderr,
        )
        try:
            run_app(app, draw_fps=session.draw_fps, renderer=session.renderer)
        finally:
            bridge.shutdown()
            controller.shutdown()
        return 0
    finally:
        set_dev_session(None)


def _describe_tree(_args: argparse.Namespace) -> int:
    try:
        client = BridgeClient.discover()
        tree = client.describe_tree()
    except (BridgeNotFoundError, OSError) as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1
    import json

    print(json.dumps(tree, indent=2))
    return 0


def _screenshot(args: argparse.Namespace) -> int:
    try:
        client = BridgeClient.discover()
        png = client.screenshot()
    except (BridgeNotFoundError, OSError) as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1

    if args.output == "-":
        sys.stdout.buffer.write(png)
    else:
        with open(args.output, "wb") as handle:
            handle.write(png)
        print(f"[nuiitivet.dev] wrote {len(png)} bytes to {args.output}", file=sys.stderr)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    if args.command == "describe-tree":
        return _describe_tree(args)
    if args.command == "screenshot":
        return _screenshot(args)
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
