"""Entry point for ``python -m nuiitivet.dev`` — run apps and inspect them live.

Subcommands::

    python -m nuiitivet.dev run path/to/app.py     # launch with hot reload
    python -m nuiitivet.dev path/to/app.py          # same (run is the default)
    python -m nuiitivet.dev run --module yourpkg.app  # dotted module name
    python -m nuiitivet.dev run app.py -- --png out.png  # arguments for the app
    python -m nuiitivet.dev status                  # is the app up & healthy?
    python -m nuiitivet.dev describe-tree           # dump the running app's tree
    python -m nuiitivet.dev describe-state          # dump the running app's observable state
    python -m nuiitivet.dev describe-selection      # dump what the human pointed at
    python -m nuiitivet.dev reload-log              # dump recent hot-reload events
    python -m nuiitivet.dev interaction-log          # dump the human's recent UI actions
    python -m nuiitivet.dev runtime-log             # dump recent log output & exceptions
    python -m nuiitivet.dev screenshot -o out.png   # screenshot the running app
    python -m nuiitivet.dev click --label increment # click a widget by identifier
    python -m nuiitivet.dev scroll --key feed --dy 5 # wheel a region (notches, ~20px)
    python -m nuiitivet.dev scroll-into-view --key row-42 # reveal a widget
    python -m nuiitivet.dev type "hello"            # type into the focused widget
    python -m nuiitivet.dev key enter --mod accel   # press a key (with modifiers)
    python -m nuiitivet.dev wait-for --label Done    # wait for a tree condition
    python -m nuiitivet.dev mcp                      # serve the bridge as MCP tools

``run`` imports the user's app module under its real name (never ``__main__``,
so importing it does not run ``main()``), installs a dev session, calls the
entry once, then drives the event loop with file watching and the dev bridge
enabled. It also replaces ``sys.argv`` with the app's own -- its path plus
anything after a ``--`` separator -- so an entry that parses arguments is not
handed the runner's command line. ``describe-tree`` / ``screenshot``
(perception) and ``click`` / ``scroll`` / ``type`` / ``key`` (action) are bridge
clients: they talk to an already-running ``run`` process over localhost.
``mcp`` serves those same primitives as MCP tools over stdio for MCP hosts
(#376). See ``docs/design/HOT_RELOAD.md``, #374 and #375.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Optional, Sequence

from .bridge import DevBridge
from .client import BridgeClient, BridgeNotFoundError
from .controller import HotReloadController
from .inspect import InspectMode
from .interaction import InteractionJournal, InteractionRecorder, window_identity
from .journal import ReloadJournal
from .loader import find_discovery_root, load_app_module, resolve_entry
from .runtime_capture import RuntimeLogCapture
from .runtime_journal import RuntimeJournal
from .selection import Selection
from .session import DevSession, set_dev_session
from . import editor, source

# Subcommands that may appear as the first token. Anything else is treated as a
# ``run`` target so ``python -m nuiitivet.dev app.py`` keeps working.
_SUBCOMMANDS = frozenset(
    {
        "run",
        "status",
        "screenshot",
        "describe-tree",
        "describe-state",
        "describe-selection",
        "reload-log",
        "interaction-log",
        "click",
        "scroll",
        "scroll-into-view",
        "type",
        "key",
        "wait-for",
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

    run = subparsers.add_parser(
        "run",
        help="Run an app with in-process hot reload.",
        description=(
            "Run an app with in-process hot reload. Arguments after a '--' separator "
            "are handed to the app as its own sys.argv, so an entry that parses "
            "arguments sees them: python -m nuiitivet.dev run app.py -- --png out.png"
        ),
    )
    # Filled in by _parse_args from whatever followed a '--' on the command line.
    run.set_defaults(app_args=[])
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
    run.add_argument(
        "--editor",
        help=(
            "Where a Ctrl+Click in inspect mode opens the code (default: vscode). "
            "Either 'vscode' or your editor's URL scheme as a template carrying "
            '{file} and {line}, e.g. "cursor://file{file}:{line}:1". The path is '
            "made absolute and percent-encoded for you."
        ),
    )

    subparsers.add_parser(
        "status",
        help="Print a cheap liveness/health snapshot of the running app as JSON.",
    )

    subparsers.add_parser("describe-tree", help="Print the running app's widget tree as JSON.")

    describe_state = subparsers.add_parser(
        "describe-state", help="Print the running app's reactive observable state as JSON."
    )
    describe_state.add_argument(
        "--include-animations",
        action="store_true",
        help="Also report Animatable state, which is filtered out by default.",
    )

    subparsers.add_parser(
        "describe-selection",
        help="Print what the human designated in the running app's inspect mode, as JSON.",
    )

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

    shot = subparsers.add_parser(
        "screenshot", help="Save a PNG of the running app's widget tree (not the window)."
    )
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

    scroll = subparsers.add_parser(
        "scroll", help="Scroll a region in the running app by wheel notches."
    )
    scroll_target = scroll.add_mutually_exclusive_group(required=True)
    scroll_target.add_argument("--key", help="Target the scroll region whose key matches.")
    scroll_target.add_argument(
        "--label", help="Target the scroll region whose label/text/title matches."
    )
    scroll_target.add_argument(
        "--xy",
        nargs=2,
        type=float,
        metavar=("X", "Y"),
        help="Root coordinates over the region (use when it carries no key).",
    )
    scroll.add_argument(
        "--dy",
        type=float,
        default=0.0,
        help="Vertical wheel notches (~20px each); positive scrolls down.",
    )
    scroll.add_argument(
        "--dx",
        type=float,
        default=0.0,
        help="Horizontal wheel notches (~20px each); positive scrolls right.",
    )

    into_view = subparsers.add_parser(
        "scroll-into-view", help="Scroll a widget's region(s) until the widget is on screen."
    )
    into_view_target = into_view.add_mutually_exclusive_group(required=True)
    into_view_target.add_argument("--key", help="Reveal the widget whose key matches.")
    into_view_target.add_argument("--label", help="Reveal the widget whose label/text/title matches.")
    into_view.add_argument(
        "--align",
        choices=("nearest", "start", "center", "end"),
        default="nearest",
        help="Where to land the widget in the region (default: nearest).",
    )

    typ = subparsers.add_parser("type", help="Type text into the running app's focused widget.")
    typ.add_argument("text", help="The text to type.")

    key = subparsers.add_parser("key", help="Press a key (e.g. enter, tab, a) in the running app.")
    key.add_argument(
        "name",
        help=(
            "Key name (e.g. enter, tab, escape, a). The editing keys -- backspace, delete, "
            "left, right, home, end -- edit the focused text field; add '--mod shift' to "
            "extend its selection."
        ),
    )
    key.add_argument(
        "--mod",
        action="append",
        default=[],
        metavar="MODIFIER",
        help="Modifier to hold (repeatable): shift, ctrl, alt, meta, accel.",
    )

    wait = subparsers.add_parser(
        "wait-for",
        help="Wait for a tree condition (key/label/text) after an async action.",
    )
    wait.add_argument("--key", help="Wait for the widget whose key matches.")
    wait.add_argument("--label", help="Wait for a widget with this visible label/text/title.")
    wait.add_argument("--text", help="Wait for this substring to appear in a visible identity.")
    wait.add_argument(
        "--absent",
        action="store_true",
        help="Wait for the target to disappear instead of appear (e.g. a spinner).",
    )
    wait.add_argument(
        "--timeout",
        type=float,
        default=None,
        metavar="SECONDS",
        help="How long to poll before giving up (default 3.0).",
    )

    subparsers.add_parser(
        "mcp",
        help="Serve the dev bridge as MCP tools over stdio (needs the 'mcp' extra).",
    )

    return parser


def _split_app_args(args: list[str]) -> tuple[list[str], list[str]]:
    """Split a ``run`` command line at the first ``--`` into runner and app arguments.

    Splitting before argparse rather than through a trailing ``REMAINDER``
    positional keeps the separator working under the implicit-``run`` insertion
    above, and keeps runner flags after ``--`` (``--entry``, ``--module``) from
    being claimed by the runner instead of reaching the app.
    """
    if "--" not in args:
        return args, []
    sep = args.index("--")
    return args[:sep], args[sep + 1 :]


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    args = list(sys.argv[1:] if argv is None else argv)
    # Backward compat / ergonomics: if no explicit subcommand leads, assume 'run'.
    if not args or (args[0] not in _SUBCOMMANDS and not (args[0] == "-h" or args[0] == "--help")):
        args = ["run", *args]
    app_args: list[str] = []
    # Only 'run' launches user code, so only 'run' has arguments to pass through;
    # every other subcommand leaves '--' to argparse's own end-of-options meaning.
    if args[0] == "run":
        args, app_args = _split_app_args(args)
    parsed = _build_parser().parse_args(args)
    if parsed.command == "run":
        parsed.app_args = app_args
    return parsed


def _app_argv(args: argparse.Namespace) -> list[str]:
    """The ``sys.argv`` the user's app should see: its own path, then its own arguments.

    A dotted ``--module`` target has no path until it is imported, so its name
    stands in as ``argv[0]`` until :func:`_run` can replace it with the module's
    real ``__file__``.
    """
    head = args.target if args.module else os.path.abspath(args.target)
    return [head, *args.app_args]


def _run(args: argparse.Namespace) -> int:
    session = DevSession()
    set_dev_session(session)
    # Before the user's module is even imported (#593): a construction site is
    # only knowable while the constructing frame is on the stack, so anything
    # built at import time is lost if this lands any later.
    source.install()
    if args.editor is not None:
        problem = editor.validate(args.editor)
        if problem is not None:
            print(f"[nuiitivet.dev] --editor: {problem}", file=sys.stderr)
            return 1
        editor.configure(args.editor)

    # The runner is a launcher, so the app must see an argv of its own rather
    # than this process's -- an entry that parses arguments otherwise dies on
    # the runner's command line. This lands before the import because a module
    # may parse arguments at import time too, and it is deliberately *not*
    # restored afterwards: hot reload re-imports user modules, so putting the
    # runner's argv back would spring the same trap on the next save. ``pdb``
    # and ``cProfile`` replace argv permanently for the same reason.
    sys.argv = _app_argv(args)
    try:
        loaded = load_app_module(args.target, is_module=args.module)
        # Now that the module is in hand, a dotted target can claim its real path.
        sys.argv[0] = getattr(loaded.module, "__file__", None) or sys.argv[0]
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
        # The controller anchors on the main window's tree (secondary windows
        # are reloaded through app.windows); the bridge addresses any window
        # via its ``window=`` selector.
        host = app.main_window
        # One journal shared by both: the controller records reload outcomes
        # into it, the bridge serves them at ``/reload_log`` so an AI pair can
        # notice the code changed between its turns (#388).
        journal = ReloadJournal()
        # What the human *points at* (#591), the reverse of the interaction
        # journal's "what the human did". Inspect mode writes designations from
        # the real input path; the controller re-resolves them across a reload;
        # the bridge serves them at ``/describe_selection``.
        selection = Selection()
        controller = HotReloadController(
            host,
            loaded.project_root,
            session.root_factory,
            poll_interval=args.poll_interval,
            journal=journal,
            selection=selection,
        )
        # The complementary surface (#390): the recorder captures the human's
        # coarse UI actions from the real input path, and the bridge serves them
        # at ``/interaction_log`` so an AI pair can see how the human drove the
        # app between its turns. Instrumented per window — the journal and the
        # selection are shared, but each window carries its own recorder and
        # inspect mode so hover/gesture state stays window-local and the
        # Ctrl+Shift+C latch works in every window, not just the main one.
        interaction_journal = InteractionJournal()

        def _instrument_window(win: Any) -> None:
            win._interaction_recorder = InteractionRecorder(interaction_journal)
            win._inspect_mode = InspectMode(selection, journal=interaction_journal)
            # Window lifecycle joins the same timeline (#622): the register
            # hook covers every open path, and the loop below back-fills the
            # windows opened before the hook existed (the main window, and any
            # opened before run()).
            interaction_journal.record_window_opened(window_identity(win))

        def _record_window_closed(win: Any) -> None:
            interaction_journal.record_window_closed(window_identity(win))

        app._instrument_window_hook = _instrument_window
        app._unregister_window_hook = _record_window_closed
        for win in app.windows:
            _instrument_window(win)
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
            selection=selection,
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
            "(status / describe-tree / describe-state / describe-selection / screenshot / click / scroll / "
            "scroll-into-view / type / key / wait-for / interaction-log / runtime-log).",
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


def _status(_args: argparse.Namespace) -> int:
    try:
        client = BridgeClient.discover()
        status = client.status()
    except (BridgeNotFoundError, OSError) as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1
    import json

    print(json.dumps(status, indent=2))
    return 0


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


def _describe_selection() -> int:
    try:
        client = BridgeClient.discover()
        payload = client.describe_selection()
    except (BridgeNotFoundError, OSError) as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1
    import json

    print(json.dumps(payload, indent=2))
    return 0


def _describe_state(args: argparse.Namespace) -> int:
    try:
        client = BridgeClient.discover()
        state = client.describe_state(include_animations=args.include_animations)
    except (BridgeNotFoundError, OSError) as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1
    import json

    print(json.dumps(state, indent=2))
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

    Shared by ``click`` / ``scroll`` / ``type`` / ``key``: each is a one-shot bridge client
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


def _scroll(args: argparse.Namespace) -> int:
    if args.xy is not None:
        x, y = args.xy
        return _run_action("scroll", lambda c: c.scroll(x=x, y=y, dx=args.dx, dy=args.dy))
    return _run_action(
        "scroll",
        lambda c: c.scroll(key=args.key, label=args.label, dx=args.dx, dy=args.dy),
    )


def _scroll_into_view(args: argparse.Namespace) -> int:
    return _run_action(
        "scroll-into-view",
        lambda c: c.scroll_into_view(key=args.key, label=args.label, align=args.align),
    )


def _type(args: argparse.Namespace) -> int:
    return _run_action("type", lambda c: c.type_text(args.text))


def _key(args: argparse.Namespace) -> int:
    return _run_action("key", lambda c: c.key(args.name, modifiers=args.mod))


def _wait_for(args: argparse.Namespace) -> int:
    if args.key is None and args.label is None and args.text is None:
        print(
            "[nuiitivet.dev] wait-for needs one of --key / --label / --text",
            file=sys.stderr,
        )
        return 1
    return _run_action(
        "wait-for",
        lambda c: c.wait_for(
            key=args.key,
            label=args.label,
            text=args.text,
            present=not args.absent,
            timeout=args.timeout,
        ),
    )


def _mcp(_args: argparse.Namespace) -> int:
    from .mcp_server import run as run_mcp

    return run_mcp()


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    if args.command == "status":
        return _status(args)
    if args.command == "describe-tree":
        return _describe_tree(args)
    if args.command == "describe-state":
        return _describe_state(args)
    if args.command == "describe-selection":
        return _describe_selection()
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
    if args.command == "scroll":
        return _scroll(args)
    if args.command == "scroll-into-view":
        return _scroll_into_view(args)
    if args.command == "type":
        return _type(args)
    if args.command == "key":
        return _key(args)
    if args.command == "wait-for":
        return _wait_for(args)
    if args.command == "mcp":
        return _mcp(args)
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
