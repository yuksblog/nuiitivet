"""Tests for Phase 6 app initialization patterns."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.layout.stack import Stack
from nuiitivet.navigation import Navigator
from nuiitivet.overlay import Overlay
from nuiitivet.runtime.app import App, AppScope
from nuiitivet.widgeting.widget import Widget


class _FlagWidget(Widget):
    def __init__(self, *, label: str = "") -> None:
        super().__init__()
        self.label = label

    def build(self) -> Widget:
        return self


def test_app_content_provides_root_overlay() -> None:
    prev_overlay = Overlay._root_overlay  # type: ignore[attr-defined]
    prev_nav = Navigator._root  # type: ignore[attr-defined]
    try:
        Overlay._root_overlay = None  # type: ignore[attr-defined]
        Navigator._root = None  # type: ignore[attr-defined]

        app = App(content=_FlagWidget(label="content"))

        assert isinstance(app.root, AppScope)
        stack = app.root.children_snapshot()[0]
        assert isinstance(stack, Stack)
        assert stack.children_snapshot()[0] is Navigator.root()
        root_overlay = Overlay.root()
        assert stack.children_snapshot()[1] is root_overlay
    finally:
        Overlay._root_overlay = prev_overlay  # type: ignore[attr-defined]
        Navigator._root = prev_nav  # type: ignore[attr-defined]


@dataclass(frozen=True, slots=True)
class _HomeIntent:
    label: str


def test_app_navigation_sets_root_navigator_and_overlay() -> None:
    prev_nav = Navigator._root  # type: ignore[attr-defined]
    prev_overlay = Overlay._root_overlay  # type: ignore[attr-defined]
    try:
        Navigator._root = None  # type: ignore[attr-defined]
        Overlay._root_overlay = None  # type: ignore[attr-defined]

        app = App.navigation(
            routes={
                _HomeIntent: lambda i: _FlagWidget(label=i.label),
            },
            initial_route=_HomeIntent(label="home"),
        )

        assert isinstance(app.root, AppScope)
        stack = app.root.children_snapshot()[0]
        assert isinstance(stack, Stack)
        assert stack.children_snapshot()[0] is Navigator.root()
        assert stack.children_snapshot()[1] is Overlay.root()
    finally:
        Navigator._root = prev_nav  # type: ignore[attr-defined]
        Overlay._root_overlay = prev_overlay  # type: ignore[attr-defined]
