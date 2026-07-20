"""Entry point for ``python -m nuiitivet.dev`` — run apps and inspect them live.

Subcommands::

    python -m nuiitivet.dev run path/to/app.py     # launch with hot reload
    python -m nuiitivet.dev path/to/app.py          # same (run is the default)
    python -m nuiitivet.dev --module yourpkg.app    # dotted module name
    python -m nuiitivet.dev describe-tree           # dump the running app's tree
    python -m nuiitivet.dev reload-log              # dump recent hot-reload events
    python -m nuiitivet.dev interaction-log          # dump the human's recent UI actions
    python -m nuiitivet.dev runtime-log             # dump recent log output & exceptions
    python -m nuiitivet.dev screenshot -o out.png   # screenshot the running app
    python -m nuiitivet.dev click --label increment # click a widget by identifier
    python -m nuiitivet.dev type "hello"            # type into the focused widget
    python -m nuiitivet.dev key enter --mod accel   # press a key (with modifiers)
    python -m nuiitivet.dev mcp                      # serve the bridge as MCP tools

``run`` imports the user's app module under its real name (never ``__main__``,
so importing it does not run ``main()``), installs a dev session, calls the
entry once, then drives the event loop with file watching and the dev bridge
enabled. ``describe-tree`` / ``screenshot`` (perception) and ``click`` / ``type``
/ ``key`` (action) are bridge clients: they talk to an already-running ``run``
process over localhost. ``mcp`` serves those same primitives as MCP tools over
stdio for MCP hosts (#376). See ``docs/design/HOT_RELOAD.md``, #374 and #375.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .bridge import DevBridge
from .client import BridgeClient, BridgeNotFoundError
from .controller import HotReloadController
from .interaction import InteractionJournal, InteractionRecorder
from .journal import ReloadJournal
from .loader import find_discovery_root, load_app_module, resolve_entry
from .runtime_capture import RuntimeLogCapture
from .runtime_journal import RuntimeJournal
from .session import DevSession, set_dev_session

# Subcommands that may appear as the first token. Anything else is treated as a
# ``run`` target so ``python -m nuiitivet.dev app.py`` keeps working.
_SUBCOMMANDS = frozenset(
    {
        "run",
        "screenshot",
        "describe-tree",
        "reload-log",
        "interaction-log",
        "click",
        "type",
        "key",
        "runtime-log",
        "mcp",
    }
)


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

    reload_log = subparsers.add_parser(
        "reload-log", help="Print the running app's recent hot-reload events as JSON."
    )
    reload_log.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        help="Return only the newest N events (default: all retained).",
    )

    interaction_log = subparsers.add_parser(
        "interaction-log", help="Print the human's recent UI actions in the running app as JSON."
    )
    interaction_log.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        help="Return only the newest N events (default: all retained).",
    )

    runtime_log = subparsers.add_parser(
        "runtime-log",
        help="Print the running app's recent log output and uncaught exceptions as JSON.",
    )
    runtime_log.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        help="Return only the newest N events (default: all retained).",
    )
    runtime_log.add_argument(
        "--verbose",
        choices=("on", "off"),
        default=None,
        help=(
            "Set verbose capture and exit (does not print the log). 'on' records "
            "every repeated failure; 'off' restores the de-duplicated default."
        ),
    )

    shot = subparsers.add_parser("screenshot", help="Save a PNG screenshot of the running app.")
    shot.add_argument(
        "-o",
        "--output",
        default="screenshot.png",
        help="Where to write the PNG (default: screenshot.png; '-' for stdout).",
    )

    click = subparsers.add_parser("click", help="Click a widget in the running app by key/label.")
    target = click.add_mutually_exclusive_group(required=True)
    target.add_argument("--key", help="Target the widget whose key matches.")
    target.add_argument("--label", help="Target the widget whose label/text/title matches.")
    target.add_argument(
        "--xy",
        nargs=2,
        type=float,
        metavar=("X", "Y"),
        help="Raw root coordinates (fallback; breaks on layout changes).",
    )

    typ = subparsers.add_parser("type", help="Type text into the running app's focused widget.")
    typ.add_argument("text", help="The text to type.")

    key = subparsers.add_parser("key", help="Press a key (e.g. enter, tab, a) in the running app.")
    key.add_argument("name", help="Key name (e.g. enter, tab, escape, a).")
    key.add_argument(
        "--mod",
        action="append",
        default=[],
        metavar="MODIFIER",
        help="Modifier to hold (repeatable): shift, ctrl, alt, meta, accel.",
    )

    subparsers.add_parser(
        "mcp",
        help="Serve the dev bridge as MCP tools over stdio (needs the 'mcp' extra).",
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
        # One journal shared by both: the controller records reload outcomes
        # into it, the bridge serves them at ``/reload_log`` so an AI pair can
        # notice the code changed between its turns (#388).
        journal = ReloadJournal()
        controller = HotReloadController(
            app,
            loaded.project_root,
            session.root_factory,
            poll_interval=args.poll_interval,
            journal=journal,
        )
        # The complementary surface (#390): the recorder captures the human's
        # coarse UI actions from the real input path, and the bridge serves them
        # at ``/interaction_log`` so an AI pair can see how the human drove the
        # app between its turns.
        interaction_journal = InteractionJournal()
        app._interaction_recorder = InteractionRecorder(interaction_journal)
        # The runtime log (#409): capture taps route the app's log output and
        # uncaught exceptions (UI, background threads, asyncio) into this journal,
        # which the bridge serves at ``/runtime_log`` so an AI pair can see *why*
        # an action it drove had no visible effect.
        runtime_journal = RuntimeJournal()
        runtime_capture = RuntimeLogCapture(runtime_journal)
        # The bridge's discovery file anchors to the user-facing project root (so
        # a client finds it by searching upward, like git), which is not always
        # Python's import root -- see :func:`find_discovery_root`.
        discovery_root = find_discovery_root(loaded.project_root)
        bridge = DevBridge(
            app,
            discovery_root,
            journal=journal,
            interaction_journal=interaction_journal,
            runtime_journal=runtime_journal,
            runtime_capture=runtime_capture,
        )

        print(
            f"[nuiitivet.dev] hot reload active for '{loaded.name}' "
            f"(watching {loaded.project_root}). Save a file to reload.",
            file=sys.stderr,
        )

        from nuiitivet.backends.pyglet.runner import run_app

        controller.install()
        runtime_capture.install()
        bridge.install()
        bridge.start()
        print(
            f"[nuiitivet.dev] dev bridge listening on 127.0.0.1:{bridge.port} "
            "(describe-tree / screenshot / click / type / key / interaction-log / "
            "runtime-log).",
            file=sys.stderr,
        )
        try:
            run_app(app, draw_fps=session.draw_fps, renderer=session.renderer)
        finally:
            bridge.shutdown()
            runtime_capture.shutdown()
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


def _reload_log(args: argparse.Namespace) -> int:
    try:
        client = BridgeClient.discover()
        events = client.reload_log(limit=args.limit)
    except (BridgeNotFoundError, OSError) as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1
    import json

    print(json.dumps(events, indent=2))
    return 0


def _interaction_log(args: argparse.Namespace) -> int:
    try:
        client = BridgeClient.discover()
        events = client.interaction_log(limit=args.limit)
    except (BridgeNotFoundError, OSError) as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1
    import json

    print(json.dumps(events, indent=2))
    return 0


def _runtime_log(args: argparse.Namespace) -> int:
    import json

    try:
        client = BridgeClient.discover()
        if args.verbose is not None:
            verbose = client.set_runtime_log_verbose(args.verbose == "on")
            print(json.dumps({"verbose": verbose}, indent=2))
            return 0
        events = client.runtime_log(limit=args.limit)
    except (BridgeNotFoundError, OSError) as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(events, indent=2))
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


def _run_action(action: str, call) -> int:  # type: ignore[no-untyped-def]
    """Discover the bridge, invoke ``call(client)``, and print the JSON result.

    Shared by ``click`` / ``type`` / ``key``: each is a one-shot bridge client
    call whose only differences are the arguments and the result payload.
    """
    import json

    try:
        client = BridgeClient.discover()
        result = call(client)
    except (BridgeNotFoundError, OSError, ValueError, RuntimeError) as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def _click(args: argparse.Namespace) -> int:
    if args.xy is not None:
        x, y = args.xy
        return _run_action("click", lambda c: c.click(x=x, y=y))
    return _run_action("click", lambda c: c.click(key=args.key, label=args.label))


def _type(args: argparse.Namespace) -> int:
    return _run_action("type", lambda c: c.type_text(args.text))


def _key(args: argparse.Namespace) -> int:
    return _run_action("key", lambda c: c.key(args.name, modifiers=args.mod))


def _mcp(_args: argparse.Namespace) -> int:
    from .mcp_server import run as run_mcp

    return run_mcp()


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    if args.command == "describe-tree":
        return _describe_tree(args)
    if args.command == "reload-log":
        return _reload_log(args)
    if args.command == "interaction-log":
        return _interaction_log(args)
    if args.command == "runtime-log":
        return _runtime_log(args)
    if args.command == "screenshot":
        return _screenshot(args)
    if args.command == "click":
        return _click(args)
    if args.command == "type":
        return _type(args)
    if args.command == "key":
        return _key(args)
    if args.command == "mcp":
        return _mcp(args)
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
