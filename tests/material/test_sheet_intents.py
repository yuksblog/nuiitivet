"""side_sheet() and bottom_sheet() accept an intent, which survives a hot reload."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pytest

from nuiitivet.dev.overlay_snapshot import restore_overlay, snapshot_overlay
from nuiitivet.layout.container import Container
from nuiitivet.material.overlay import MaterialOverlay, _find_descendant
from nuiitivet.material.sheet import BottomSheet, SideSheet
from nuiitivet.material.window import MaterialWindow
from nuiitivet.overlay.result import OverlayDismissReason
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.material.text import Text
from nuiitivet.widgeting.widget import Widget


@dataclass(frozen=True)
class _SettingsIntent:
    headline: str


@dataclass(frozen=True)
class _OptionsIntent:
    headline: str


@dataclass(frozen=True)
class _PlainIntent:
    text: str


class _SpyOverlay(MaterialOverlay):
    """Records the keyword arguments of every show() call."""

    def __init__(self, version: int) -> None:
        super().__init__(
            intents={
                _SettingsIntent: lambda i: SideSheet(Text(f"v{version}"), headline=i.headline),
                _OptionsIntent: lambda i: BottomSheet(Text(f"v{version}"), headline=i.headline),
                _PlainIntent: lambda i: Text(i.text),
            }
        )
        self.version = version
        self.shows: list[dict[str, Any]] = []

    def show(self, content: Widget, **kwargs: Any) -> Any:
        self.shows.append(kwargs)
        return super().show(content, **kwargs)


def _factory(version: int) -> Callable[[], _SpyOverlay]:
    return lambda: _SpyOverlay(version)


def _window(version: int) -> Window:
    return App(MaterialWindow(content=Container, overlay=_factory(version))).main_window


def _overlay(window: Window) -> _SpyOverlay:
    overlay = window.overlay
    assert isinstance(overlay, _SpyOverlay)
    return overlay


def _reload(window: Window, version: int) -> int:
    window._overlay_factory = _factory(version)
    content = window._rebuild_content_root()
    records = snapshot_overlay(window)
    window._commit_content_root(content)
    return restore_overlay(window, records)


def _headlines(window: Window, sheet_type: type[SideSheet] | type[BottomSheet]) -> list[Any]:
    contents = [e.content for e in _overlay(window).open_entries if e.content is not None]
    found = [_find_descendant(c, sheet_type) for c in contents]
    return [s._headline for s in found if s is not None]


def test_an_intent_resolving_to_a_non_sheet_raises() -> None:
    overlay = _overlay(_window(1))

    with pytest.raises(TypeError, match="SideSheet"):
        overlay.side_sheet(_PlainIntent("x"))
    with pytest.raises(TypeError, match="BottomSheet"):
        overlay.bottom_sheet(_PlainIntent("x"))


def test_an_intent_side_sheet_stays_open_with_its_placement() -> None:
    window = _window(1)
    handle = _overlay(window).side_sheet(_SettingsIntent("Settings"), side="left", dismiss_on_outside_tap=False)
    assert _headlines(window, SideSheet) == ["Settings"]

    assert _reload(window, 2) == 1

    overlay = _overlay(window)
    assert overlay.version == 2
    assert _headlines(window, SideSheet) == ["Settings"]
    assert overlay.shows[-1]["dismiss_on_outside_tap"] is False
    assert overlay.shows[-1]["position"].alignment_key == "top-left"
    handle.close("done")
    result = handle.result()
    assert result is not None and result.value == "done"


def test_an_intent_bottom_sheet_stays_open_with_its_placement() -> None:
    window = _window(1)
    _overlay(window).bottom_sheet(_OptionsIntent("Options"), dismiss_on_outside_tap=False)
    assert _headlines(window, BottomSheet) == ["Options"]

    assert _reload(window, 2) == 1

    assert _headlines(window, BottomSheet) == ["Options"]
    assert _overlay(window).shows[-1]["dismiss_on_outside_tap"] is False


def test_a_widget_sheet_closes_on_reload() -> None:
    window = _window(1)
    handle = _overlay(window).bottom_sheet(BottomSheet(Text("w"), headline="Widget"))

    assert _reload(window, 2) == 0

    assert _overlay(window).open_entries == ()
    result = handle.result()
    assert result is not None and result.reason is OverlayDismissReason.DISPOSED
