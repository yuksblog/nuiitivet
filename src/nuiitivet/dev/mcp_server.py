"""MCP server exposing the dev bridge as assistant-native tools (dev-only).

This is the polished, MCP-host-facing surface over the dev bridge:
it turns the localhost control channel into first-class tools any MCP host
(Claude Desktop, IDE integrations, other agents) can call to close the
perception-action loop over hot reload -- edit code (hot reload) ->
``describe_tree`` / ``describe_state`` (see) -> ``click`` / ``type`` / ``key``
(act) -> ``wait_for`` (settle async work) -> verify -> edit again.

``screenshot`` serves a separate purpose: investigating a human-reported
visual/layout discrepancy that ``describe_tree`` + ``describe_state`` cannot
explain (see its docstring).

The server holds no app logic. Every tool is a thin forward to a freshly
discovered :class:`~nuiitivet.dev.client.BridgeClient`, which talks to the
running ``python -m nuiitivet.dev run <app.py>`` process over localhost. It inherits
that bridge's dev-session gate, so it is never a path into a production app.

The ``mcp`` SDK is an optional dependency; install it with
``pip install 'nuiitivet[dev]'``. Both SDK majors are supported (1.x and 2.x,
which renamed the server class). Importing this module without a usable SDK
raises a :class:`MissingMCPDependencyError` -- saying which of the two cases it
is -- rather than a bare ``ImportError``.

Run it over stdio (the transport every MCP host supports) with::

    python -m nuiitivet.dev mcp
"""

from __future__ import annotations

import importlib.util
from typing import Any, Optional

from .client import BridgeClient, BridgeNotFoundError

# The 'mcp' SDK is an optional dependency (the ``[dev]`` extra). Import it at
# module scope so type annotations on the tool functions resolve -- the server
# evaluates them against these module globals -- but tolerate its absence so
# merely importing this module (e.g. to probe availability) never hard-fails.
#
# SDK 2.0 renamed the server package: ``mcp.server.fastmcp.FastMCP`` became
# ``mcp.server.mcpserver.MCPServer``. No release ships both, so support the two
# majors by trying the newer path first and falling back. Everything we use of
# the class -- the constructor, ``@tool()``, ``Image``, ``run(transport=...)``,
# and the resulting tool schemas -- is identical across them, so the rest of
# this module is written once against the ``FastMCP`` alias.
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

# Guidance surfaced to the calling model. Two ways to "check the app": `status`
# answers "is it up and healthy?" and `describe_tree` answers "is the right thing
# on screen?" (and resolves action targets); `describe_state` covers the reactive
# values behind the tree.
#
# Design note, for maintainers -- do not fold this into the model-facing
# text below: `screenshot` is classified by trigger, not cost. It is described
# only by its own job -- a human-reported visual discrepancy tree+state can't
# explain -- and is kept out of every see/verify/cost description entirely. The
# reason for silence rather than a disclaimer: naming it even to say "not a
# see-option" re-associates it with the loop, and "expensive see-option" framing
# puts it back on a cost gradient whose top is always a legal move. So it is
# absent here by design; do not reintroduce it as the pricey alternative to
# `status`/`describe_tree`.
_SERVER_INSTRUCTIONS = (
    "Tools to drive a running nuiitivet dev app (started with "
    "'python -m nuiitivet.dev run <app.py>'). To confirm the app is up and healthy "
    "-- after starting it, or after an edit -- call `status`: it is the cheapest "
    "check and returns liveness, the current title, the last hot-reload outcome, "
    "an error count, and a `blank` flag for a white/blank screen, all without the "
    "tree or an image. To reason about the UI or check that the right thing is on "
    "screen, and to resolve click/type targets by key or label, use "
    "`describe_tree` -- a compact JSON tree, cheap in tokens. Use `screenshot` "
    "for one thing: investigating a human-reported visual/layout discrepancy that "
    "`describe_tree` + `describe_state` cannot explain; a human's report is what "
    "puts it in play. When the displayed tree looks wrong but you need to know "
    "whether "
    "the *state* behind it is wrong too -- a reactive bug where the value "
    "updated but the UI did not, or the reverse -- call `describe_state`: it "
    "returns the live `Observable` values behind the tree, in the same shape as "
    "`describe_tree` so you can join them node-for-node. Act with `click`, "
    "`scroll`, `type`, and `key`, then re-`describe_tree` to "
    "verify the effect. An action on a target that is scrolled out of its "
    "region or covered by an overlay fails rather than quietly landing "
    "elsewhere; when it does, call `scroll_into_view` on that target and retry. "
    "In a pair session the human may edit and save while you "
    "work; call `reload_log` to see whether the code hot-reloaded under you (and "
    "whether it even compiled) before trusting a stale `describe_tree`. The human "
    "may also drive the app itself between your turns; call `interaction_log` to "
    "see their recent clicks, keys, and typing so you can tell where they are and "
    "how they got there before acting. When an action seems to do nothing, call "
    "`runtime_log`: a callback that raised is swallowed to keep the app alive and "
    "reported there, so it tells you *why* nothing changed, not just that it "
    "didn't -- it also carries background-thread and asyncio failures and general "
    "log output. If a repeated error has collapsed to one line and you need every "
    "occurrence, call `set_runtime_log_verbose(True)`."
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

    @server.tool()
    def status() -> dict[str, Any]:
        """Return a cheap liveness/health snapshot of the running app.

        The first thing to call to confirm the app is up and healthy -- after
        starting it, or after an edit -- and the right tool for a health check.
        Cheaper than `describe_tree` (no tree). Returns:

        - ``running`` -- always ``True`` when this returns; if the app is not up,
          the call fails instead with a "no running dev app" error.
        - ``title`` -- the current window title, so you can confirm *which* app is
          running (or ``null`` if unset).
        - ``last_reload`` -- the newest hot-reload as ``{"seq", "outcome"}`` (or
          ``null``); ``outcome: "error"`` means your last save did not compile and
          the live UI is stale. Compare ``seq`` to tell a new reload from an old.
        - ``error_count`` -- number of retained ERROR/CRITICAL runtime events
          (uncaught exceptions and swallowed callback errors, not WARNING noise);
          nonzero means something failed at runtime -- see `runtime_log`.
        - ``blank`` -- ``True`` if the frame is a single uniform color, i.e. a
          white/blank screen where nothing painted (a build that produced no
          content, or a paint that raised). A heuristic: an intentionally solid
          screen also reads blank.
        - ``windows`` -- the open windows as ``[{"id", "title", "main",
          "focused"}]`` (or ``null`` on a single-host build). Pass an ``id`` as
          the ``window`` argument of the tree/state/screenshot/action tools to
          address that window; omitting it addresses the main window.
        - ``selection`` -- ``{"seq", "active", "nodes", "regions"}`` (or ``null``):
          what the human has pointed at in inspect mode. A ``seq`` you have not
          seen before means they designated something for you since your last
          turn -- call `describe_selection` to read it. ``active: true`` means
          they are still designating.

        Use `describe_tree` when you need the actual on-screen structure.
        """
        return _client().status()

    @server.tool()
    def describe_tree(window: Optional[int] = None) -> dict[str, Any]:
        """Return the running app's widget tree as compact structural JSON.

        This is the token-cheap default for reasoning about the UI and for
        resolving `click` / `type` targets. Each node is
        ``{"type", optional "key"/"label"/"text"/"title", optional "rect",
        optional "children"}`` where ``rect`` is ``[x, y, w, h]`` in root
        coordinates. This is the default for reading what is on screen.

        ``window`` selects an open window by id (from `status`'s ``windows``
        listing); omit it for the main window.
        """
        return _client().describe_tree(window=window)

    @server.tool()
    def describe_state(
        include_animations: bool = False, window: Optional[int] = None
    ) -> dict[str, Any]:
        """Return the running app's reactive `Observable` state as structural JSON.

        The complement to `describe_tree`: where that gives the UI *output*
        (types, identities, rects), this gives the *state that produced it* -- the
        live observable values behind the tree. Use it to diagnose reactive bugs
        where the tree looks wrong but you need to know whether the underlying
        state is wrong too: "the value updated but the UI didn't", or the reverse.

        The result mirrors `describe_tree`'s nested shape -- each node is
        ``{"type", optional "key"/"label"/"text"/"title", optional "state",
        optional "children"}`` -- but is pruned to nodes that hold state (or
        contain one that does), so you can join it to `describe_tree` node-for-node
        by type and identity. ``state`` maps a name to its current value (e.g.
        ``{"checked": true}``); a derived/computed value is instead
        ``{"value", "kind": "computed"}``. Values are length- and depth-capped and
        opaque objects render as ``type: repr``.

        Animation state is **omitted by default**: an interactive widget's
        `Animatable` channels (`state_layer_anim`, `bg_color_anim`, …) change
        every frame and carry visual, not semantic, state -- they used to bury
        the state you are looking for. Set `include_animations=True` only when
        the animation itself is the bug ("the button never returns to its rest
        state").
        """
        return _client().describe_state(include_animations=include_animations, window=window)

    @server.tool()
    def describe_selection() -> dict[str, Any]:
        """Return what the human deliberately pointed at in the running app.

        The one channel that runs *from* the human *to* you. `describe_tree` and
        `describe_state` tell you what the app is; `interaction_log` tells you
        what the human did. This tells you what the human **meant** -- the widgets
        they entered inspect mode and designated on purpose.

        Reach for it whenever `status` reports a `selection` whose `seq` you have
        not seen, and whenever the human says "this is wrong" / "look at this
        part" without naming a widget: they may well have pointed at it already,
        and guessing from a screenshot when a designation is waiting is wasted
        effort.

        Returns ``{"seq", "active", "nodes", "regions", "lost"}`` -- two
        independent lists, either of which may be empty. Each node is
        ``{"index", "type", optional "key"/"label", "path", "rect", "tree",
        "state"}`` -- `index` matches the number badged on screen, so "the second
        one" means `index: 2`; `key`/`label` are directly usable as a `click`
        target; `path` is the root -> node type chain for locating it in
        `describe_tree`; `tree` and `state` are those dumps **scoped to that
        node**, which is usually all you need instead of a whole-tree read.

        A **region** is an area they dragged a box over rather than a widget,
        numbered in the same sequence as `nodes`. It carries `rect`, the
        `container` enclosing it (with that container's immediate children), and
        `contents` -- a nested tree of the nodes it covers, each tagged
        `contained` or `clipped` (a node with no tag is only on the path to one).

        The two fields answer two readings of the same rectangle, and **you**
        pick: "the gap between these things" is `container`, "these things" is
        `contents`. The geometry cannot tell them apart, so nothing is collapsed
        for you -- decide from what the human actually said. **An empty
        `contents` is the answer, not a miss**: they drew a box where nothing is
        painted, and `container` names the widget that should have put something
        there. Regions are re-derived on every call, so read one again after your
        fix to see what occupies the area now.

        `active: true` means inspect mode is still on: the human may still be
        designating, and has not yet pressed `Enter` to keep it (`Esc` throws the
        session away). Prefer waiting over acting on a half-made set -- and if
        they say they pointed at something but the lists are empty, this is why. `lost` is
        how many designated widgets a hot reload could not re-resolve; when it is
        non-zero, say so rather than reasoning over a silently shortened list.
        """
        return _client().describe_selection()

    @server.tool()
    def reload_log(limit: Optional[int] = None) -> dict[str, Any]:
        """Return recent hot-reload events in the running app, oldest-first.

        Use this to notice edits the human made between your turns: in a pair
        session they may save a file while you work, so your last `describe_tree`
        and your assumptions about the source can go stale. Each event is
        ``{"seq", "timestamp", "outcome": "success"|"error", optional "modules",
        "changed", optional "error"}``. ``seq`` is monotonic -- compare it to the
        last one you saw to tell whether new reloads happened. ``changed`` lists
        the modules whose *source actually changed*: an empty ``changed`` is a
        no-op save (mtime bumped but bytes identical -- an editor autosave or
        formatter), so you can skip re-reading; a non-empty ``changed`` pinpoints
        which file(s) to re-read. An ``"error"`` outcome means the human's save
        did *not* compile and the previous UI is still running, so the live tree
        does not reflect the code you are reading; re-read the files (and
        re-`describe_tree`) before acting. ``limit`` caps the result to the
        newest N events.
        """
        return {"events": _client().reload_log(limit=limit)}

    @server.tool()
    def interaction_log(limit: Optional[int] = None) -> dict[str, Any]:
        """Return the human's recent coarse UI actions in the running app, oldest-first.

        Use this to see what the human *did in the app* between your turns: in a
        pair session they may click through a screen or reproduce a bug while you
        work, so your last `describe_tree` can be of a stale screen. It lets you
        answer "where is the human now, and how did they get here?" and re-sync
        before acting -- e.g. so you do not dismiss a dialog they just opened.

        Each event is ``{"seq", "timestamp", "kind", ...}`` where ``kind`` is
        ``"click"``, ``"key"``, ``"text"``, ``"scroll"``, ``"window_opened"``,
        or ``"window_closed"``. ``seq`` is monotonic
        -- compare it to the last one you saw to tell whether new actions
        happened. A ``click`` carries ``target`` (the resolved widget
        ``{"type", optional "key"/"label"}``, never a coordinate); a ``key``
        carries ``key`` and optional ``modifiers`` (only shortcuts and navigation
        keys are recorded); a ``text`` marker means the human typed into a field
        -- the content is deliberately never recorded. Semantic transitions
        (navigation, dialogs) are not recorded; infer them from the click sequence
        plus `describe_tree`. ``limit`` caps the result to the newest N events.

        A ``scroll`` carries the region's ``target``, the ``direction``, the
        distance in wheel notches (``dx`` / ``dy``, the units and signs `scroll`
        takes), and where the region ended up: ``axis``, ``offset``,
        ``max_extent``, ``at_start``, ``at_end``. Prefer the position over the
        delta -- ``at_end: true`` tells "scrolled to the bottom" from "still
        going". One entry is one **gesture**: consecutive scrolls of one region in
        one direction merge (delta accumulates, ``seq`` is re-issued,
        ``started_at`` keeps the start), while a reversal, another region, or any
        click / key / text starts a new entry. Unconsumed scrolling is not
        recorded.

        A ``window_opened`` / ``window_closed`` carries ``window``
        (``{"id", optional "title", "main"}``, the ids `status` lists and
        ``window=`` takes) and covers every open/close path, including an
        OS-title-bar close or a parent-cascade close that no click event shows.
        A ``window_closed`` for an id you remembered means that id is stale --
        re-run `status` before addressing it.
        """
        return {"events": _client().interaction_log(limit=limit)}

    @server.tool()
    def runtime_log(limit: Optional[int] = None) -> dict[str, Any]:
        """Return the running app's recent log output and uncaught exceptions, oldest-first.

        Use this to see *why* an action had no visible effect. When an
        assistant-driven `click` / `type` / `key` triggers a callback that
        raises, the framework swallows it (the app stays alive) and reports it
        here -- so a `describe_tree` that looks unchanged is explained by an
        exception in this log, not a no-op. It also carries uncaught
        background-thread and asyncio failures and general WARNING+ log output.

        Each event is ``{"seq", "timestamp", "level", "source", "thread",
        "message", optional "logger"/"exc_type"/"traceback"}``. ``source`` is
        ``"logging"``, ``"thread"``, or ``"excepthook"``. ``seq`` is monotonic --
        compare it to the last one you saw to tell whether new output happened
        since your turn. Repeated identical failures collapse to one entry by
        default; if that hides one you need, call `set_runtime_log_verbose(True)`.
        ``limit`` caps the result to the newest N events.
        """
        return {"events": _client().runtime_log(limit=limit)}

    @server.tool()
    def set_runtime_log_verbose(enabled: bool) -> dict[str, Any]:
        """Enable or disable verbose `runtime_log` capture; return the new state.

        By default the running app de-duplicates repeated failures, so a callback
        that raises every frame shows once rather than flooding the log. Enabling
        verbose turns that off process-wide so *every* occurrence is recorded --
        use it when a collapsed entry is hiding a distinct error you are chasing,
        then disable it again to restore the quiet default. Returns
        ``{"verbose": true|false}``.
        """
        return {"verbose": _client().set_runtime_log_verbose(enabled)}

    @server.tool()
    def screenshot(window: Optional[int] = None) -> Image:
        """Return a PNG of the widget tree, re-rendered offscreen.

        Use it for one job: investigating a *human-reported* visual or layout
        discrepancy that `describe_tree` + `describe_state` cannot explain. A
        human's report is the trigger that puts it in play; the pixels are where
        you look once tree and state have failed to reproduce what they saw. For
        everything else the other tools are the answer -- `status` (with its
        `blank` flag) for whether the app started or is healthy, `describe_tree`
        for on-screen structure and action targets.

        **It can come back clean while the screen is visibly broken** (GPU path,
        swap chain), so never dismiss a human's visual report on that basis --
        ask them for their own screenshot.
        """
        return Image(data=_client().screenshot(window=window), format="png")

    @server.tool()
    def click(
        key: Optional[str] = None,
        label: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Click a widget in the running app.

        Target it by a stable identifier -- ``key`` (a widget's key/testID) or
        ``label`` (its visible label/text/title) -- which survives layout
        changes. Raw ``x`` / ``y`` root coordinates are a fallback. Find valid
        identifiers with `describe_tree`.
        """
        return _client().click(key=key, label=label, x=x, y=y, window=window)

    @server.tool()
    def scroll(
        key: Optional[str] = None,
        label: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        dx: float = 0.0,
        dy: float = 0.0,
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Send a mouse wheel event to a scrollable region in the running app.

        ``key`` / ``label`` name **the scroll region itself** (the list, the
        feed), exactly as they name a widget everywhere else. Naming something
        *inside* the region is an error, and deliberately so: the wheel would
        move that widget out of view, so the anchor that aimed your first call
        no longer exists for the second. The error tells you which region
        encloses it and the coordinates that reach it.

        Regions often carry no ``key`` in `describe_tree`. Two ways through:
        give the region a ``key=`` in its constructor, or pass the ``x`` / ``y`` centre of the
        region's rect -- that rect does not move as the content scrolls, so the
        same coordinates stay valid for the whole loop.

        ``dx`` / ``dy`` are **wheel notches, not pixels**: a region moves 20 px
        per notch by default, so ``dy=5`` scrolls about 100 px. Positive is
        toward the content's end (``dy`` down, ``dx`` right). Scrolling is
        linear with no inertia -- send one ``dy=10`` rather than ten ``dy=1``.

        Returns ``handled`` plus the region's resulting ``offset``,
        ``max_extent``, ``at_start`` and ``at_end``. Read them: ``handled:
        false`` means nothing consumed the wheel (wrong target -- there is no
        scrollable region there), while ``handled: true`` with an unchanged
        ``offset`` and ``at_end: true`` means the region is already at the end.
        Both look identical on screen, and ``at_end`` is your stop condition.

        To bring a specific widget on screen, prefer `scroll_into_view` -- it
        computes the offset in one shot instead of stepping by notches.
        """
        return _client().scroll(key=key, label=label, x=x, y=y, dx=dx, dy=dy, window=window)

    @server.tool()
    def scroll_into_view(
        key: Optional[str] = None,
        label: Optional[str] = None,
        align: str = "nearest",
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Scroll a widget's region(s) until that widget is on screen.

        The fix for a `click` (or `scroll`) that failed with "not visible": the
        target exists in the tree but is scrolled out of its region, so the
        coordinates it resolves to reach nothing. This moves the minimum amount
        needed and guarantees the widget is reachable, in one call rather than a
        `scroll` poll loop. Nested regions are handled outermost-inward.

        ``align`` places the target: ``"nearest"`` (default, move as little as
        possible), ``"start"``, ``"center"`` or ``"end"``.

        Returns ``already_visible`` (``true`` when nothing had to move) and the
        region's resulting ``offset`` / ``max_extent``. A target in no
        scrollable region at all is an error, not a silent success.
        """
        return _client().scroll_into_view(key=key, label=label, align=align, window=window)

    @server.tool()
    def type(  # noqa: A001 (MCP tool name is intentional)
        text: str, window: Optional[int] = None
    ) -> dict[str, Any]:
        """Type ``text`` into the app's focused widget.

        Focus a target first (e.g. `click` a text field); with nothing focused
        the app has nowhere to route the text and ``handled`` is ``False``.
        """
        return _client().type_text(text, window=window)

    @server.tool()
    def key(
        name: str,
        modifiers: Optional[list[str]] = None,
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Press a key (e.g. ``enter``, ``tab``, ``a``) in the running app.

        ``modifiers`` is an optional list of names to hold -- ``shift``,
        ``ctrl``, ``alt``, ``meta``, or ``accel`` (the platform Ctrl/Cmd) -- so
        shortcuts and focus traversal behave like real key events.

        The editing keys -- ``backspace``, ``delete``, ``left``, ``right``,
        ``home``, ``end`` -- edit the focused text field, which is how you
        delete what `type` inserted or move the caret; hold ``shift`` with one
        to extend the selection instead.
        """
        return _client().key(name, modifiers=modifiers, window=window)

    @server.tool()
    def wait_for(
        key: Optional[str] = None,
        label: Optional[str] = None,
        text: Optional[str] = None,
        present: bool = True,
        timeout: Optional[float] = None,
        window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Wait for a tree condition after an action that starts async work.

        After a `click` / `type` / `key` that kicks off async loading (network,
        a timer, an animation), the tree updates over several frames -- an
        immediate `describe_tree` can race it and see a spinner or stale value.
        Call this first to wait for the settled state.

        Name the condition by ``key`` (a widget's key/testID), ``label`` (its
        visible label/text/title), and/or ``text`` (a substring of a visible
        identity). The bridge polls -- re-settling each time -- until it holds or
        ``timeout`` seconds elapse (default 3.0). Set ``present=False`` to wait
        for the target to *disappear* (e.g. a loading spinner).

        Returns ``{"satisfied", "timed_out", "waited", "polls", "condition"}``.
        A plain timeout is reported as ``satisfied: false`` (not an error) --
        follow up with `describe_tree` to see what state the app is actually in.
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
