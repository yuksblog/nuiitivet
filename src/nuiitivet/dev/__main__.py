"""Entry point for ``python -m nuiitivet.dev`` — launch an app with hot reload.

Usage::

    python -m nuiitivet.dev path/to/app.py        # file path (matches launch.json)
    python -m nuiitivet.dev --module yourpkg.app  # dotted module name
    python -m nuiitivet.dev --entry run app.py     # custom entry function

The runner imports the user's app module under its real name (never ``__main__``,
so importing it does not run ``main()``), installs a dev session, calls the
entry once, then drives the event loop with file watching enabled. See
``docs/design/HOT_RELOAD.md``.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .controller import HotReloadController
from .loader import load_app_module, resolve_entry
from .session import DevSession, set_dev_session


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m nuiitivet.dev",
        description="Run a nuiitivet app with in-process hot reload.",
    )
    parser.add_argument(
        "target",
        help="Path to the app file (e.g. app.py), or a dotted module name with --module.",
    )
    parser.add_argument(
        "--module",
        action="store_true",
        help="Treat 'target' as a dotted module name (yourpkg.app) instead of a file path.",
    )
    parser.add_argument(
        "--entry",
        default="main",
        help="Name of the entry function to call (default: main).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.4,
        help="File-watch poll interval in seconds (default: 0.4).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)

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

        print(
            f"[nuiitivet.dev] hot reload active for '{loaded.name}' "
            f"(watching {loaded.project_root}). Save a file to reload.",
            file=sys.stderr,
        )

        from nuiitivet.backends.pyglet.runner import run_app

        controller.install()
        try:
            run_app(app, draw_fps=session.draw_fps, renderer=session.renderer)
        finally:
            controller.shutdown()
        return 0
    finally:
        set_dev_session(None)


if __name__ == "__main__":
    raise SystemExit(main())
