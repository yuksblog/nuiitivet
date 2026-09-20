"""MCP server exposing the dev bridge as tools (dev-only).

Every tool is a thin forward to a freshly discovered
:class:`~nuiitivet.dev.client.BridgeClient`, which talks to the running
``python -m nuiitivet.dev run <app.py>`` process over localhost. The server holds
no app logic and inherits the bridge's dev-session gate.

The ``mcp`` SDK is an optional dependency (``pip install 'nuiitivet[dev]'``); SDK
1.x and 2.x are both supported. Without a usable SDK, building the server raises
:class:`MissingMCPDependencyError`. Run it over stdio with
``python -m nuiitivet.dev mcp``.
"""

from __future__ import annotations

import importlib.util
import inspect
from typing import Any, Callable, Optional, TypeVar

from .client import BridgeClient, BridgeNotFoundError

# Imported at module scope so the tool annotations resolve; absence is tolerated
# so that probing this module never hard-fails. SDK 2.0 renamed
# ``mcp.server.fastmcp.FastMCP`` to ``mcp.server.mcpserver.MCPServer``: try the
# newer path first.
try:
    from mcp.server.mcpserver import MCPServer as FastMCP  # mcp >= 2.0
    from mcp.server.mcpserver import Image

    _MCP_IMPORT_ERROR: Optional[ImportError] = None
except ImportError:  # pragma: no cover - depends on the installed SDK major
    try:
        from mcp.server.fastmcp import FastMCP, Image  # type: ignore[no-redef]  # mcp < 2.0

        _MCP_IMPORT_ERROR = None
    except ImportError as _exc:  # pragma: no cover - depends on install extras
        FastMCP = None  # type: ignore[assignment,misc]
        Image = None  # type: ignore[assignment,misc]
        _MCP_IMPORT_ERROR = _exc


_Tool = TypeVar("_Tool", bound=Callable[..., Any])


class MissingMCPDependencyError(RuntimeError):
    """The optional ``mcp`` SDK is missing, or is a version we cannot drive."""


_INSTALL_HINT = (
    "The MCP server needs the 'mcp' package, which is an optional dependency. "
    "Install it with: pip install 'nuiitivet[dev]'"
)

# Telling someone to install a package they already have is the worst possible
# message, so an import failure with 'mcp' present is reported as what it is: a
# version we do not know how to drive (a third rename, or a broken install).
_INCOMPATIBLE_HINT = (
    "The MCP server found an 'mcp' package (version {version}) it cannot use: "
    "neither 'mcp.server.mcpserver' (SDK 2.x) nor 'mcp.server.fastmcp' "
    "(SDK 1.x) could be imported from it. Try: "
    "pip install --upgrade 'nuiitivet[dev]'"
)

# `screenshot` appears only by its own job: beside `status` / `describe_tree` it
# would read as the costly way to look, an option the model may pay for.
_SERVER_INSTRUCTIONS = (
    "Tools to drive a running nuiitivet dev app (started with "
    "'python -m nuiitivet.dev run <app.py>'). The nuiitivet-debug skill carries the "
    "working loop and the choice between these tools, and the "
    "nuiitivet-see-comments skill reads the human's comments; install both with "
    "'python -m nuiitivet.skills install'. Which tool answers which question: is "
    "the app up and healthy -- `status`; what is on screen, and what can I target "
    "-- `describe_tree`; is the state behind the tree right -- `describe_state`; "
    "what did the human point at in the app, and write there -- `see_comments`; "
    "did the code hot-reload under me -- `reload_log`; what did the human do in "
    "the app -- `interaction_log`; why did an action do nothing -- `runtime_log` "
    "(`set_runtime_log_verbose` records every occurrence of a repeated error); a "
    "human reported a visual discrepancy that tree and state cannot explain -- "
    "`screenshot`; a human reported jank -- `profile_start`, then `profile_stop`. "
    "Act with `click`, `type`, `key` and `scroll`; `scroll_into_view` when a "
    "target is not visible; `wait_for` before reading the tree after an action "
    "that starts async work."
)


def _mcp_is_installed() -> bool:
    """Report whether an ``mcp`` package exists on the path, importable or not."""
    return importlib.util.find_spec("mcp") is not None


def _installed_mcp_version() -> str:
    """Return the installed ``mcp`` distribution version, or ``"unknown"``."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("mcp")
    except PackageNotFoundError:  # pragma: no cover - a path-only/source install
        return "unknown"


def _import_failure_hint() -> str:
    """Explain the recorded import failure: SDK absent, or SDK unusable."""
    if not _mcp_is_installed():
        return _INSTALL_HINT
    return _INCOMPATIBLE_HINT.format(version=_installed_mcp_version())


def _require_mcp() -> None:
    """Confirm the optional ``mcp`` SDK is importable, or raise a helpful error."""
    if _MCP_IMPORT_ERROR is not None:
        raise MissingMCPDependencyError(_import_failure_hint()) from _MCP_IMPORT_ERROR


def _client() -> BridgeClient:
    """Discover the running dev bridge for a single tool call.

    A fresh client per call keeps the server stateless: the target app may be
    restarted (a new port) between calls, and rediscovering each time picks up
    the current one rather than clinging to a dead handle.
    """
    return BridgeClient.discover()


def build_server() -> "FastMCP":
    """Construct the FastMCP server with the bridge-backed tools registered.

    Raises:
        MissingMCPDependencyError: If the optional ``mcp`` SDK is not installed.
    """
    _require_mcp()

    server = FastMCP("nuiitivet-dev", instructions=_SERVER_INSTRUCTIONS)

    def tool(fn: _Tool) -> _Tool:
        """Register ``fn``, sending its docstring without the source indentation."""
        server.tool(description=inspect.cleandoc(fn.__doc__ or ""))(fn)
        return fn

    @tool
    def status() -> dict[str, Any]:
        """Return a cheap liveness and health snapshot of the running app.

        Call it first -- after starting the app, or after an edit. No tree, no image.
        Fails with "no running dev app" when the app is not up.

        - ``last_reload``: ``outcome: "error"`` means the last save did not compile and
          the live UI is stale.
        - ``error_count``: retained ERROR/CRITICAL runtime events, cumulative; the
          details are in `runtime_log`.
        - ``blank``: the frame is one uniform color -- nothing painted. An
          intentionally solid screen also reads blank.
        - ``windows``: pass an ``id`` as ``window`` to the other tools; omitted, they
          address the main window.
        - ``comments``: a ``seq`` you have not seen means the human left a comment
          since your last turn -- call `see_comments`. ``committed: false`` means they
          are still writing.
        """
        return _client().status()

    @tool
    def describe_tree(window: Optional[int] = None) -> dict[str, Any]:
        """Return the running app's widget tree as compact JSON.

        The default for reading what is on screen and for resolving `click` / `type`
        targets. ``rect`` is ``[x, y, w, h]`` as laid out: inside a scrolled region it
        does not subtract the scroll offset, so it is not where the widget is painted --
        target by ``key`` / ``label`` there, never by ``rect``. ``state`` is what the
        widget publishes: ``disabled`` / ``focused`` / ``selected`` appear only when
        true, ``value`` whenever the widget has one (a tri-state checkbox reports
        ``null``, a range slider a ``[start, end]`` pair).

        ``window`` is an id from `status`; omit it for the main window.
        """
        return _client().describe_tree(window=window)

    @tool
    def describe_state(
        include_animations: bool = False, window: Optional[int] = None
    ) -> dict[str, Any]:
        """Return the live `Observable` values behind the tree.

        Call it when the tree looks wrong and you need to know whether the state is
        wrong too: the value updated but the UI did not, or the reverse. Same nested
        shape as `describe_tree`, pruned to the nodes that hold state, so the two join
        node for node. Names are the widget's own attributes (``_state_internal``), so
        they differ per widget; a computed value is ``{"value", "kind": "computed"}``.
        Animation state is omitted unless ``include_animations=True`` -- pass it when
        the animation itself is the bug.
        """
        return _client().describe_state(include_animations=include_animations, window=window)

    @tool
    def see_comments() -> dict[str, Any]:
        """Return the human's comments: the widgets and areas they marked in the app, and what they wrote on each.

        The one channel from the human to you. Call it when the human says
        `see_comments`, when `status` reports a `comments` ``seq`` you have not seen,
        and when they say "this is wrong" without naming a widget.

        ``nodes`` and ``regions`` share one numbering: ``index`` is the badge on the
        human's screen. ``instruction`` is what they wrote, in their words -- a change
        to make, or a problem they saw. Reproduce a problem before editing;
        `interaction_log` holds their steps. A mark without ``instruction`` is still a
        comment: they say what they mean in chat, by number. Answer every comment in
        one turn, by number: ``comment 2: refused``, with the reason.

        A region is an area, not a widget. ``container`` is the widget enclosing the
        box and ``contents`` is what the box crosses: "the gap between these things" is
        ``container``, "these things" is ``contents``. Empty ``contents`` means nothing
        is painted there.
        """
        return _client().see_comments()

    @tool
    def reload_log(limit: Optional[int] = None) -> dict[str, Any]:
        """Return recent hot-reload events, oldest first.

        Call it to notice edits the human saved between your turns, before trusting a
        cached `describe_tree`. Compare ``seq`` with the last one you saw.

        - ``outcome: "error"``: the save did not compile; the previous UI is still
          running.
        - ``changed``: the modules whose source changed. Empty means a no-op save (an
          autosave or a formatter).
        - ``inert_windows``: window ids whose root is a widget instance, not a factory.
          No edit reaches them until ``Window(content=...)`` takes a factory.

        ``limit`` caps the result to the newest N events.
        """
        return {"events": _client().reload_log(limit=limit)}

    @tool
    def interaction_log(limit: Optional[int] = None) -> dict[str, Any]:
        """Return what the human did in the running app, oldest first.

        Call it to re-sync before acting: they may have clicked through a screen since
        your last `describe_tree`. When they report a problem, the events before the
        newest ``comment`` marker are the steps that led to it: replay them with
        `click` / `key` / `scroll` to reproduce it, and again after the fix.

        ``kind`` is ``click``, ``key``, ``text``, ``scroll``, ``comment``,
        ``window_opened`` or ``window_closed``; compare ``seq`` with the last one you
        saw. A ``click`` carries the ``target`` widget, never a coordinate. Only
        shortcut and navigation keys are recorded, and a ``text`` marker carries no
        content. One ``scroll`` entry is one gesture, in the units `scroll` takes; read
        ``at_end`` rather than the delta. A ``window_closed`` for an id you remembered
        means that id is stale. Navigation and dialogs are not recorded: infer them
        from the clicks and `describe_tree`.

        ``limit`` caps the result to the newest N events.
        """
        return {"events": _client().interaction_log(limit=limit)}

    @tool
    def runtime_log(limit: Optional[int] = None) -> dict[str, Any]:
        """Return the app's recent log output and uncaught exceptions, oldest first.

        Call it when an action had no visible effect: a callback that raised is
        swallowed to keep the app alive, and reported here. It also carries
        background-thread and asyncio failures and WARNING+ log output. Compare ``seq``
        with the last one you saw. Repeated identical failures collapse to one entry;
        `set_runtime_log_verbose(True)` records every occurrence. ``limit`` caps the
        result to the newest N events.
        """
        return {"events": _client().runtime_log(limit=limit)}

    @tool
    def set_runtime_log_verbose(enabled: bool) -> dict[str, Any]:
        """Turn verbose `runtime_log` capture on or off; return ``{"verbose": bool}``.

        On, every occurrence of a repeated failure is recorded instead of one. Turn it
        on when a collapsed entry hides the error you are chasing, and off again
        afterwards.
        """
        return {"verbose": _client().set_runtime_log_verbose(enabled)}

    @tool
    def profile_start() -> dict[str, Any]:
        """Start recording rebuild and repaint counters and frame timings.

        Call it only when a human reports jank or slowness: you cannot perceive
        either. Then reproduce the interaction they named, and call `profile_stop`.
        Painted frames run about 10% slower while recording. ``was_active: true`` means
        a session was already running and kept its counters.
        """
        return _client().profile_start()

    @tool
    def profile_stop() -> dict[str, Any]:
        """Stop the profiling session and return its report (``null`` when nothing was recording).

        ``frames`` is the painted count with mean / p95 / max tree-walk ms. ``paints``
        tracks frames, not damage: every painted frame walks the whole tree.
        ``rebuilds`` and ``bindings`` are the signal, largest first: a widget that
        rebuilds far more often than the interaction warrants is doing wasted work.
        """
        return _client().profile_stop()

    @tool
    def screenshot(
        key: Optional[str] = None,
        label: Optional[str] = None,
        rect: Optional[list[float]] = None,
        padding: Optional[float] = None,
        window: Optional[int] = None,
    ) -> Image:
        """Return a PNG of the widget tree, re-rendered offscreen.

        One job: a human-reported visual or layout discrepancy that `describe_tree`
        and `describe_state` cannot explain.

        ``key`` / ``label`` crop to that widget plus ``padding`` logical pixels a side
        (default 8); ``rect=[x, y, w, h]`` crops to a raw region; omit all three for
        the whole frame. A widget scrolled wholly out of view fails with "not visible":
        `scroll_into_view` it first.

        The render is offscreen, so it can come back clean while the screen is visibly
        broken (GPU path, swap chain): ask the human for their own screenshot instead
        of dismissing the report.
        """
        return Image(
            data=_client().screenshot(
                key=key, label=label, rect=rect, padding=padding, window=window
            ),
            format="png",
        )

    @tool
    def click(
        key: Optional[str] = None,
        label: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Click a widget in the running app.

        Target it by ``key`` or ``label`` (its visible label, text or title), found
        with `describe_tree`; ``x`` / ``y`` root coordinates are the fallback. A target
        scrolled out of view or covered fails with "not visible" instead of landing
        elsewhere.
        """
        return _client().click(key=key, label=label, x=x, y=y, window=window)

    @tool
    def scroll(
        key: Optional[str] = None,
        label: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        dx: float = 0.0,
        dy: float = 0.0,
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Send a mouse wheel event to a scrollable region.

        ``key`` / ``label`` name the scroll region itself. A widget inside the region is
        refused, and the error names the enclosing region and the coordinates that
        reach it. A region without a ``key`` takes the ``x`` / ``y`` centre of its rect,
        which does not move as the content scrolls.

        ``dx`` / ``dy`` are wheel notches, 20 px each by default; positive is down /
        right. There is no inertia: send one ``dy=10``, not ten ``dy=1``.

        ``handled: false`` means no scrollable region is there. ``at_end: true`` with an
        unchanged ``offset`` means the region is already at its end: that is the stop
        condition. To bring one widget on screen, call `scroll_into_view`.
        """
        return _client().scroll(key=key, label=label, x=x, y=y, dx=dx, dy=dy, window=window)

    @tool
    def scroll_into_view(
        key: Optional[str] = None,
        label: Optional[str] = None,
        align: str = "nearest",
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Scroll a widget's region(s) until the widget is on screen.

        The fix for a `click` or `scroll` that failed with "not visible". One call,
        minimum movement, nested regions outermost first. ``align`` is ``"nearest"``
        (default), ``"start"``, ``"center"`` or ``"end"``. ``already_visible: true``
        means nothing moved. A target in no scrollable region is an error.
        """
        return _client().scroll_into_view(key=key, label=label, align=align, window=window)

    @tool
    def type(  # noqa: A001 (MCP tool name is intentional)
        text: str, window: Optional[int] = None
    ) -> dict[str, Any]:
        """Type ``text`` into the app's focused widget.

        Focus a target first (e.g. `click` a text field); with nothing focused
        the app has nowhere to route the text and ``handled`` is ``False``.
        """
        return _client().type_text(text, window=window)

    @tool
    def key(
        name: str,
        modifiers: Optional[list[str]] = None,
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Press a key (e.g. ``enter``, ``tab``, ``a``) in the running app.

        ``modifiers`` holds any of ``shift``, ``ctrl``, ``alt``, ``meta`` or ``accel``
        (the platform Ctrl/Cmd). ``backspace``, ``delete``, ``left``, ``right``, ``home``
        and ``end`` edit the focused text field: that is how you delete what `type`
        inserted or move the caret; ``shift`` with one extends the selection.
        """
        return _client().key(name, modifiers=modifiers, window=window)

    @tool
    def wait_for(
        key: Optional[str] = None,
        label: Optional[str] = None,
        text: Optional[str] = None,
        present: bool = True,
        timeout: Optional[float] = None,
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Wait for a tree condition after an action that starts async work.

        Call it before `describe_tree` when a `click` / `type` / `key` starts loading,
        a timer or an animation. Name the condition by ``key``, ``label`` and/or
        ``text`` (a substring of a visible identity); ``present=False`` waits for it to
        disappear. Polls until it holds or ``timeout`` seconds pass (default 3.0). A
        timeout is ``satisfied: false``, not an error.
        """
        return _client().wait_for(
            key=key, label=label, text=text, present=present, timeout=timeout, window=window
        )

    return server


def run(argv: Optional[list[str]] = None) -> int:
    """Build and serve the MCP server over stdio.

    Returns a process exit code: ``0`` on a clean shutdown, ``1`` if the ``mcp``
    SDK is missing. A missing *running app* is not an error here -- the server
    starts regardless and each tool call reports :class:`BridgeNotFoundError` if
    no app is up yet, so a host can launch the server before the app.
    """
    import sys

    try:
        server = build_server()
    except MissingMCPDependencyError as exc:
        print(f"[nuiitivet.dev] {exc}", file=sys.stderr)
        return 1
    server.run(transport="stdio")
    return 0


__all__ = [
    "BridgeNotFoundError",
    "MissingMCPDependencyError",
    "build_server",
    "run",
]
