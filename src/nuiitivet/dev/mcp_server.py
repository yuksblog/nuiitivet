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
    "expensive. Act with `click`, `type`, and `key`, then re-`describe_tree` to "
    "verify the effect."
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
