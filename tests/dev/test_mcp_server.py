"""Tests for the MCP server that wraps the dev bridge (#376).

The server holds no app logic: every tool forwards to a discovered
:class:`~nuiitivet.dev.client.BridgeClient`. These tests patch
``BridgeClient.discover`` to return a fake client and drive the tools through
the server's ``call_tool`` boundary, so tool schemas, result conversion
(including the ``screenshot`` image), and error propagation are all exercised.

They run against either ``mcp`` SDK major (#489). The SDK's own result shapes
differ between them -- ``call_tool``'s return type and a mime-type field rename
-- so the helpers below normalize those; the tools themselves behave
identically and are asserted the same way for both.

They ``pytest.importorskip('mcp')`` because the SDK is an optional dependency;
the two import-failure tests instead simulate an absent or unusable SDK by
patching the module's recorded import error.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest import mock

import pytest

pytest.importorskip("mcp")

from nuiitivet.dev import mcp_server  # noqa: E402
from nuiitivet.dev.client import BridgeClient, BridgeNotFoundError  # noqa: E402


def _fake_client() -> Any:
    """A stand-in BridgeClient with canned responses for every forwarded call."""
    client = mock.Mock(spec=BridgeClient)
    client.status.return_value = {
        "running": True,
        "title": "Counter",
        "blank": False,
        "last_reload": {"seq": 3, "outcome": "success"},
        "error_count": 0,
    }
    client.describe_tree.return_value = {"type": "Root", "label": "increment"}
    client.describe_state.return_value = {
        "type": "Root",
        "state": {"count": 3, "doubled": {"value": 6, "kind": "computed"}},
    }
    client.screenshot.return_value = b"\x89PNG\r\n\x1a\n-fake-image-bytes"
    client.click.return_value = {"clicked": {"key": "submit"}, "x": 5, "y": 5}
    client.scroll.return_value = {
        "scrolled": {"key": "feed"},
        "x": 5,
        "y": 5,
        "dx": 0.0,
        "dy": 5.0,
        "handled": True,
        "offset": 100.0,
        "max_extent": 300.0,
        "at_end": False,
    }
    client.scroll_into_view.return_value = {
        "scrolled_into_view": {"key": "row-42"},
        "already_visible": False,
        "offset": 640.0,
        "max_extent": 900.0,
    }
    client.type_text.return_value = {"typed": "hi", "handled": True}
    client.key.return_value = {"key": "enter", "modifiers": 2, "handled": True}
    client.reload_log.return_value = [
        {
            "seq": 1,
            "timestamp": 1.0,
            "outcome": "success",
            "modules": ["pkg.a"],
            "changed": ["pkg.a"],
        },
    ]
    client.interaction_log.return_value = [
        {"seq": 1, "timestamp": 1.0, "kind": "click", "target": {"type": "Button"}},
    ]
    client.runtime_log.return_value = [
        {
            "seq": 1,
            "timestamp": 1.0,
            "level": "ERROR",
            "source": "logging",
            "thread": "MainThread",
            "message": "boom",
            "exc_type": "ValueError",
        },
    ]
    client.set_runtime_log_verbose.return_value = True
    client.wait_for.return_value = {
        "satisfied": True,
        "timed_out": False,
        "waited": 0.12,
        "polls": 3,
        "condition": {"present": True, "label": "Saved"},
    }
    return client


def _call(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    """Invoke a tool and return its structured result (dict tools).

    For a tool that returns a mapping, SDK 1.x hands back a
    ``(content, structured)`` tuple and SDK 2.x a ``CallToolResult``; this
    unwraps the structured half of either for straightforward assertions.
    """
    result = asyncio.run(server.call_tool(name, arguments))
    if isinstance(result, tuple):  # mcp < 2.0
        _content, structured = result
        return structured
    return result.structured_content


def _call_content(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    """Invoke a tool and return its content blocks (for non-dict results).

    SDK 1.x returns the block list itself; SDK 2.x wraps it in a
    ``CallToolResult``.
    """
    result = asyncio.run(server.call_tool(name, arguments))
    if isinstance(result, list):  # mcp < 2.0
        return result
    return result.content


def _mime_type(block: Any) -> str:
    """Return a content block's mime type across the SDK's field rename."""
    return getattr(block, "mime_type", None) or block.mimeType  # 2.x / 1.x


def test_build_server_registers_the_tools() -> None:
    server = mcp_server.build_server()
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {
        "status",
        "describe_tree",
        "describe_state",
        "describe_selection",
        "reload_log",
        "interaction_log",
        "runtime_log",
        "set_runtime_log_verbose",
        "screenshot",
        "click",
        "scroll",
        "scroll_into_view",
        "type",
        "key",
        "wait_for",
    }


def test_status_forwards_to_client() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "status", {})
    assert result["running"] is True
    assert result["title"] == "Counter"
    assert result["blank"] is False
    assert result["last_reload"] == {"seq": 3, "outcome": "success"}
    assert result["error_count"] == 0
    client.status.assert_called_once_with()


def test_describe_tree_forwards_to_client() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "describe_tree", {})
    assert result == {"type": "Root", "label": "increment"}
    client.describe_tree.assert_called_once_with()


def test_describe_state_forwards_to_client() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "describe_state", {})
    assert result["state"]["count"] == 3
    assert result["state"]["doubled"] == {"value": 6, "kind": "computed"}
    # Animation channels are opt-in, so the default call must forward False.
    client.describe_state.assert_called_once_with(include_animations=False)


def test_describe_state_forwards_the_animation_opt_in() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        _call(server, "describe_state", {"include_animations": True})
    client.describe_state.assert_called_once_with(include_animations=True)


def test_reload_log_forwards_to_client() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "reload_log", {"limit": 5})
    assert result["events"][0]["outcome"] == "success"
    client.reload_log.assert_called_once_with(limit=5)


def test_interaction_log_forwards_to_client() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "interaction_log", {"limit": 3})
    assert result["events"][0]["kind"] == "click"
    client.interaction_log.assert_called_once_with(limit=3)


def test_runtime_log_forwards_to_client() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "runtime_log", {"limit": 10})
    assert result["events"][0]["exc_type"] == "ValueError"
    client.runtime_log.assert_called_once_with(limit=10)


def test_set_runtime_log_verbose_forwards_to_client() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "set_runtime_log_verbose", {"enabled": True})
    assert result == {"verbose": True}
    client.set_runtime_log_verbose.assert_called_once_with(True)


def test_screenshot_returns_png_image_content() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        content = _call_content(server, "screenshot", {})
    # A single ImageContent block carrying the PNG as base64 with a png mime.
    assert len(content) == 1
    block = content[0]
    assert block.type == "image"
    assert _mime_type(block) == "image/png"
    client.screenshot.assert_called_once_with()


def test_click_forwards_target_identifiers() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "click", {"key": "submit"})
    assert result["clicked"]["key"] == "submit"
    client.click.assert_called_once_with(key="submit", label=None, x=None, y=None)


def test_scroll_forwards_target_and_deltas() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "scroll", {"key": "feed", "dy": 5.0})
    assert result["handled"] is True
    assert result["offset"] == 100.0
    client.scroll.assert_called_once_with(key="feed", label=None, x=None, y=None, dx=0.0, dy=5.0)


def test_scroll_into_view_forwards_target_and_alignment() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "scroll_into_view", {"key": "row-42", "align": "center"})
    assert result["already_visible"] is False
    client.scroll_into_view.assert_called_once_with(key="row-42", label=None, align="center")


def test_type_forwards_text() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "type", {"text": "hi"})
    assert result == {"typed": "hi", "handled": True}
    client.type_text.assert_called_once_with("hi")


def test_key_forwards_name_and_modifiers() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "key", {"name": "enter", "modifiers": ["accel"]})
    assert result["handled"] is True
    client.key.assert_called_once_with("enter", modifiers=["accel"])


def test_wait_for_forwards_condition() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(
            server, "wait_for", {"label": "Saved", "present": False, "timeout": 2.0}
        )
    assert result["satisfied"] is True
    client.wait_for.assert_called_once_with(
        key=None, label="Saved", text=None, present=False, timeout=2.0
    )


def test_tool_surfaces_bridge_not_found() -> None:
    try:
        from mcp.server.mcpserver.exceptions import ToolError  # mcp >= 2.0
    except ImportError:
        from mcp.server.fastmcp.exceptions import ToolError  # type: ignore[no-redef]

    with mock.patch.object(
        BridgeClient, "discover", side_effect=BridgeNotFoundError("No running app")
    ):
        server = mcp_server.build_server()
        with pytest.raises(ToolError, match="No running app"):
            asyncio.run(server.call_tool("describe_tree", {}))


def test_missing_mcp_dependency_is_a_helpful_error() -> None:
    # The SDK is genuinely absent, so the fix really is to install it.
    with mock.patch.object(mcp_server, "_MCP_IMPORT_ERROR", ImportError("no mcp")):
        with mock.patch.object(mcp_server, "_mcp_is_installed", return_value=False):
            with pytest.raises(
                mcp_server.MissingMCPDependencyError, match=r"optional dependency"
            ) as excinfo:
                mcp_server.build_server()
    assert "nuiitivet[dev]" in str(excinfo.value)


def test_incompatible_mcp_version_is_reported_as_such() -> None:
    """An unusable-but-present SDK must not be reported as a missing one.

    This is the mcp 2.0 failure mode (#489): the server package was renamed, so
    the import fails while the package is installed. Telling that user to
    install what they already have is a dead end, so the message says which
    version it found and that neither module path worked.
    """
    with mock.patch.object(mcp_server, "_MCP_IMPORT_ERROR", ImportError("renamed")):
        with mock.patch.object(mcp_server, "_mcp_is_installed", return_value=True):
            with mock.patch.object(
                mcp_server, "_installed_mcp_version", return_value="9.9.9"
            ):
                with pytest.raises(mcp_server.MissingMCPDependencyError) as excinfo:
                    mcp_server.build_server()
    message = str(excinfo.value)
    assert "9.9.9" in message
    assert "mcp.server.mcpserver" in message
    assert "mcp.server.fastmcp" in message
    assert "optional dependency" not in message


def test_run_returns_1_when_mcp_missing(capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch.object(mcp_server, "_MCP_IMPORT_ERROR", ImportError("no mcp")):
        with mock.patch.object(mcp_server, "_mcp_is_installed", return_value=False):
            assert mcp_server.run() == 1
    assert "nuiitivet[dev]" in capsys.readouterr().err
