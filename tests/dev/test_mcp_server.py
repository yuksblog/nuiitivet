"""Tests for the MCP server that wraps the dev bridge (#376).

The server holds no app logic: every tool forwards to a discovered
:class:`~nuiitivet.dev.client.BridgeClient`. These tests patch
``BridgeClient.discover`` to return a fake client and drive the tools through
FastMCP's ``call_tool`` boundary, so tool schemas, result conversion (including
the ``screenshot`` image), and error propagation are all exercised.

They ``pytest.importorskip('mcp')`` because the SDK is an optional dependency;
the one missing-dependency test instead simulates absence by patching the
module's recorded import error.
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
    client.describe_tree.return_value = {"type": "Root", "label": "increment"}
    client.screenshot.return_value = b"\x89PNG\r\n\x1a\n-fake-image-bytes"
    client.click.return_value = {"clicked": {"key": "submit"}, "x": 5, "y": 5}
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
    return client


def _call(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    """Invoke a tool and return its structured result (dict tools).

    FastMCP returns ``(content, structured)`` for tools that return a mapping;
    this unwraps the structured half for straightforward assertions.
    """
    result = asyncio.run(server.call_tool(name, arguments))
    _content, structured = result
    return structured


def _call_content(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    """Invoke a tool and return its content blocks (for non-dict results)."""
    return asyncio.run(server.call_tool(name, arguments))


def test_build_server_registers_the_tools() -> None:
    server = mcp_server.build_server()
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {
        "describe_tree",
        "reload_log",
        "interaction_log",
        "runtime_log",
        "set_runtime_log_verbose",
        "screenshot",
        "click",
        "type",
        "key",
    }


def test_describe_tree_forwards_to_client() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "describe_tree", {})
    assert result == {"type": "Root", "label": "increment"}
    client.describe_tree.assert_called_once_with()


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
    assert block.mimeType == "image/png"
    client.screenshot.assert_called_once_with()


def test_click_forwards_target_identifiers() -> None:
    client = _fake_client()
    with mock.patch.object(BridgeClient, "discover", return_value=client):
        server = mcp_server.build_server()
        result = _call(server, "click", {"key": "submit"})
    assert result["clicked"]["key"] == "submit"
    client.click.assert_called_once_with(key="submit", label=None, x=None, y=None)


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


def test_tool_surfaces_bridge_not_found() -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    with mock.patch.object(
        BridgeClient, "discover", side_effect=BridgeNotFoundError("No running app")
    ):
        server = mcp_server.build_server()
        with pytest.raises(ToolError, match="No running app"):
            asyncio.run(server.call_tool("describe_tree", {}))


def test_missing_mcp_dependency_is_a_helpful_error() -> None:
    with mock.patch.object(mcp_server, "_MCP_IMPORT_ERROR", ImportError("no mcp")):
        with pytest.raises(mcp_server.MissingMCPDependencyError, match=r"nuiitivet\[mcp\]"):
            mcp_server.build_server()


def test_run_returns_1_when_mcp_missing(capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch.object(mcp_server, "_MCP_IMPORT_ERROR", ImportError("no mcp")):
        assert mcp_server.run() == 1
    assert "nuiitivet[mcp]" in capsys.readouterr().err
