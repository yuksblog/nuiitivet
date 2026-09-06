"""The CLI's ``--window`` reaches the bridge client, and a bad id says so.

Parsing is covered in ``test_cli_args``; what matters here is the other half --
that each subcommand forwards the id to the client method that already takes
``window=``, so a multi-window app is verifiable from the CLI.
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

import pytest

from nuiitivet.dev import __main__ as cli


class _RecordingClient:
    """Stands in for :class:`BridgeClient`, recording the ``window`` it is given."""

    def __init__(self) -> None:
        self.window: Any = "unset"

    def describe_tree(self, *, window: Optional[int] = None) -> dict[str, Any]:
        self.window = window
        return {}

    def describe_state(
        self, include_animations: bool = False, *, window: Optional[int] = None
    ) -> dict[str, Any]:
        self.window = window
        return {}

    def screenshot(self, *, window: Optional[int] = None, **kwargs: Any) -> bytes:
        self.window = window
        return b"png"

    def click(self, **kwargs: Any) -> dict[str, Any]:
        self.window = kwargs.get("window")
        return {}

    def scroll(self, **kwargs: Any) -> dict[str, Any]:
        self.window = kwargs.get("window")
        return {}

    def scroll_into_view(self, **kwargs: Any) -> dict[str, Any]:
        self.window = kwargs.get("window")
        return {}

    def type_text(self, text: str, *, window: Optional[int] = None) -> dict[str, Any]:
        self.window = window
        return {}

    def key(self, name: str, **kwargs: Any) -> dict[str, Any]:
        self.window = kwargs.get("window")
        return {}

    def wait_for(self, **kwargs: Any) -> dict[str, Any]:
        self.window = kwargs.get("window")
        return {}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[_RecordingClient]:
    recorder = _RecordingClient()
    monkeypatch.setattr(cli.BridgeClient, "discover", classmethod(lambda cls: recorder))
    # 'screenshot' writes its bytes out; keep them out of the working tree.
    monkeypatch.chdir(tmp_path)
    yield recorder


_SUBCOMMANDS = [
    ["describe-tree"],
    ["describe-state"],
    ["screenshot"],
    ["click", "--key", "a"],
    ["scroll", "--key", "a", "--dy", "1"],
    ["scroll", "--xy", "10", "20", "--dy", "1"],
    ["scroll-into-view", "--key", "a"],
    ["type", "hello"],
    ["key", "enter"],
    ["wait-for", "--label", "Done"],
]


@pytest.mark.parametrize("argv", _SUBCOMMANDS, ids=lambda a: "-".join(a[:2]))
def test_window_reaches_the_client(client: _RecordingClient, argv: list[str]) -> None:
    assert cli.main([*argv, "--window", "2"]) == 0
    assert client.window == 2


@pytest.mark.parametrize("argv", _SUBCOMMANDS, ids=lambda a: "-".join(a[:2]))
def test_omitting_window_addresses_the_main_window(
    client: _RecordingClient, argv: list[str]
) -> None:
    assert cli.main(argv) == 0
    assert client.window is None


def test_click_by_xy_carries_the_window_too(client: _RecordingClient) -> None:
    assert cli.main(["click", "--xy", "10", "20", "--window", "2"]) == 0
    assert client.window == 2


def test_an_unknown_window_id_reports_the_bridge_reason(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The bridge's 404 reason has to survive, not become 'HTTP Error 404'."""

    class _Failing:
        def describe_tree(self, *, window: Optional[int] = None) -> dict[str, Any]:
            raise RuntimeError("no open window with id 9")

    monkeypatch.setattr(cli.BridgeClient, "discover", classmethod(lambda cls: _Failing()))
    assert cli.main(["describe-tree", "--window", "9"]) == 1
    assert "no open window with id 9" in capsys.readouterr().err
