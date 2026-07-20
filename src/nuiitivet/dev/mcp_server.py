"""MCP server exposing the dev bridge as assistant-native tools (dev-only).

This is the polished, MCP-host-facing surface over the dev bridge (#374, #375):
it turns the localhost control channel into first-class tools any MCP host
(Claude Desktop, IDE integrations, other agents) can call to close the
perception-action loop over hot reload -- edit code (hot reload) ->
``describe_tree`` / ``screenshot`` (see) -> ``click`` / ``type`` / ``key``
(act) -> verify -> edit again.

The server holds no app logic. Every tool is a thin forward to a freshly
discovered :class:`~nuiitivet.dev.client.BridgeClient`, which talks to the
running ``python -m nuiitivet.dev <app.py>`` process over localhost. It inherits
that bridge's dev-session gate, so it is never a path into a production app.

The ``mcp`` SDK is an optional dependency; install it with
``pip install 'nuiitivet[mcp]'``. Importing this module without it raises a
:class:`MissingMCPDependencyError` with that hint rather than a bare
``ImportError``.

Run it over stdio (the transport every MCP host supports) with::

    python -m nuiitivet.dev mcp

See #376 and ``docs/design/HOT_RELOAD.md``.
"""

from __future__ import annotations

from typing import Any, Optional

from .client import BridgeClient, BridgeNotFoundError

# The 'mcp' SDK is an optional dependency (the ``[mcp]`` extra). Import it at
# module scope so type annotations on the tool functions resolve -- FastMCP
# evaluates them against these module globals -- but tolerate its absence so
# merely importing this module (e.g. to probe availability) never hard-fails.
try:
    from mcp.server.fastmcp import FastMCP, Image

    _MCP_IMPORT_ERROR: Optional[ImportError] = None
except ImportError as _exc:  # pragma: no cover - depends on install extras
    FastMCP = None  # type: ignore[assignment,misc]
    Image = None  # type: ignore[assignment,misc]
    _MCP_IMPORT_ERROR = _exc


class MissingMCPDependencyError(RuntimeError):
    """The optional ``mcp`` SDK is not installed."""


_INSTALL_HINT = (
    "The MCP server needs the 'mcp' package, which is an optional dependency. "
    "Install it with: pip install 'nuiitivet[mcp]'"
)

# Guidance surfaced to the calling model so it spends tokens wisely: the
# structural tree is the default lens for reasoning and target resolution;
# screenshots are for occasional visual spot checks because image tokens are
# expensive. Kept in one place so every tool's docstring stays consistent.
_SERVER_INSTRUCTIONS = (
    "Tools to drive a running nuiitivet dev app (started with "
    "'python -m nuiitivet.dev <app.py>'). Default to `describe_tree` for "
    "reasoning about the UI and for resolving click/type targets by key or "
    "label -- it is a compact JSON tree and cheap in tokens. Reserve "
    "`screenshot` for occasional visual spot checks; image tokens are "
    "expensive. When the displayed tree looks wrong but you need to know whether "
    "the *state* behind it is wrong too -- a reactive bug where the value "
    "updated but the UI did not, or the reverse -- call `describe_state`: it "
    "returns the live `Observable` values behind the tree, in the same shape as "
    "`describe_tree` so you can join them node-for-node. Act with `click`, "
    "`type`, and `key`, then re-`describe_tree` to "
    "verify the effect. In a pair session the human may edit and save while you "
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


def _require_mcp() -> None:
    """Confirm the optional ``mcp`` SDK is importable, or raise a helpful error."""
    if _MCP_IMPORT_ERROR is not None:
        raise MissingMCPDependencyError(_INSTALL_HINT) from _MCP_IMPORT_ERROR


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
    def describe_tree() -> dict[str, Any]:
        """Return the running app's widget tree as compact structural JSON.

        This is the token-cheap default for reasoning about the UI and for
        resolving `click` / `type` targets. Each node is
        ``{"type", optional "key"/"label"/"text"/"title", optional "rect",
        optional "children"}`` where ``rect`` is ``[x, y, w, h]`` in root
        coordinates. Prefer this over `screenshot` unless you specifically need
        to see pixels.
        """
        return _client().describe_tree()

    @server.tool()
    def describe_state() -> dict[str, Any]:
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
        """
        return _client().describe_state()

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
        ``"click"``, ``"key"``, or ``"text"``. ``seq`` is monotonic -- compare it
        to the last one you saw to tell whether new actions happened. A ``click``
        carries ``target`` (the resolved widget ``{"type", optional "key"/
        "label"}``, never a coordinate); a ``key`` carries ``key`` and optional
        ``modifiers`` (only shortcuts and navigation keys are recorded); a
        ``text`` marker means the human typed into a field -- the content is
        deliberately never recorded. Semantic transitions (navigation, dialogs)
        are not recorded; infer them from the click sequence plus `describe_tree`.
        ``limit`` caps the result to the newest N events.
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
    def screenshot() -> Image:
        """Return a PNG screenshot of the running app's current frame.

        Use sparingly, for visual spot checks -- image tokens are expensive.
        For structure and for choosing action targets, use `describe_tree`
        instead.
        """
        return Image(data=_client().screenshot(), format="png")

    @server.tool()
    def click(
        key: Optional[str] = None,
        label: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> dict[str, Any]:
        """Click a widget in the running app.

        Target it by a stable identifier -- ``key`` (a widget's key/testID) or
        ``label`` (its visible label/text/title) -- which survives layout
        changes. Raw ``x`` / ``y`` root coordinates are a fallback. Find valid
        identifiers with `describe_tree`.
        """
        return _client().click(key=key, label=label, x=x, y=y)

    @server.tool()
    def type(text: str) -> dict[str, Any]:  # noqa: A001 (MCP tool name is intentional)
        """Type ``text`` into the app's focused widget.

        Focus a target first (e.g. `click` a text field); with nothing focused
        the app has nowhere to route the text and ``handled`` is ``False``.
        """
        return _client().type_text(text)

    @server.tool()
    def key(name: str, modifiers: Optional[list[str]] = None) -> dict[str, Any]:
        """Press a key (e.g. ``enter``, ``tab``, ``a``) in the running app.

        ``modifiers`` is an optional list of names to hold -- ``shift``,
        ``ctrl``, ``alt``, ``meta``, or ``accel`` (the platform Ctrl/Cmd) -- so
        shortcuts and focus traversal behave like real key events.
        """
        return _client().key(name, modifiers=modifiers)

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
