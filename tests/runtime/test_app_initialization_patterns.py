"""Tests for Phase 6 app initialization patterns."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.geometry import Geometry, Size
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.stack import Stack
from nuiitivet.material.app import MaterialApp
from nuiitivet.navigation import Navigator
from nuiitivet.overlay import Overlay
from nuiitivet.runtime.app import App, AppScope
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class _FlagWidget(Widget):
    def __init__(self, *, label: str = "") -> None:
        super().__init__()
        self.label = label

    def build(self) -> Widget:
        return self


class _ComposableFixedBox(ComposableWidget):
    def build(self) -> Widget:
        return Container(width=200, height=50)


def test_app_content_provides_root_overlay() -> None:
    prev_overlay = Overlay._root_overlay  # type: ignore[attr-defined]
    prev_nav = Navigator._root  # type: ignore[attr-defined]
    try:
        Overlay._root_overlay = None  # type: ignore[attr-defined]
        Navigator._root = None  # type: ignore[attr-defined]

        app = App(content=_FlagWidget(label="content"))

        assert isinstance(app.root, AppScope)
        geometry = app.root.children_snapshot()[0]
        assert isinstance(geometry, Geometry)
        stack = geometry.children_snapshot()[0]
        assert isinstance(stack, Stack)
        assert stack.children_snapshot()[0] is Navigator.root()
        root_overlay = Overlay.root()
        assert stack.children_snapshot()[1] is root_overlay
    finally:
        Overlay._root_overlay = prev_overlay  # type: ignore[attr-defined]
        Navigator._root = prev_nav  # type: ignore[attr-defined]


def test_app_installs_root_geometry_provider() -> None:
    prev_overlay = Overlay._root_overlay  # type: ignore[attr-defined]
    prev_nav = Navigator._root  # type: ignore[attr-defined]
    try:
        Overlay._root_overlay = None  # type: ignore[attr-defined]
        Navigator._root = None  # type: ignore[attr-defined]

        content = _FlagWidget(label="content")
        app = App(content=content)

        geometry = app.root.children_snapshot()[0]
        assert isinstance(geometry, Geometry)

        # The root Geometry measures the window through the normal layout pass:
        # laying out the app root publishes the window size, and a content widget
        # resolves Geometry.of(...) to this root provider.
        app.root.layout(800, 600)
        assert geometry.size.value == Size(800, 600)
        assert Geometry.of(content) is geometry
    finally:
        Overlay._root_overlay = prev_overlay  # type: ignore[attr-defined]
        Navigator._root = prev_nav  # type: ignore[attr-defined]


@dataclass(frozen=True, slots=True)
class _HomeIntent:
    label: str


def test_app_with_intents_navigator_sets_root_navigator_and_overlay() -> None:
    prev_nav = Navigator._root  # type: ignore[attr-defined]
    prev_overlay = Overlay._root_overlay  # type: ignore[attr-defined]
    try:
        Navigator._root = None  # type: ignore[attr-defined]
        Overlay._root_overlay = None  # type: ignore[attr-defined]

        app = App(
            Navigator.intents(
                initial_route=_HomeIntent(label="home"),
                routes={
                    _HomeIntent: lambda i: _FlagWidget(label=i.label),
                },
            ),
        )

        assert isinstance(app.root, AppScope)
        geometry = app.root.children_snapshot()[0]
        assert isinstance(geometry, Geometry)
        stack = geometry.children_snapshot()[0]
        assert isinstance(stack, Stack)
        assert stack.children_snapshot()[0] is Navigator.root()
        assert stack.children_snapshot()[1] is Overlay.root()
    finally:
        Navigator._root = prev_nav  # type: ignore[attr-defined]
        Overlay._root_overlay = prev_overlay  # type: ignore[attr-defined]


def test_app_auto_window_size_measures_unmounted_composable_children() -> None:
    content = Column(
        children=[_ComposableFixedBox()],
        gap=16,
        padding=16,
    )

    app = App(content=content, width="auto", height="auto")

    assert app.width == 232
    assert app.height == 82


def test_app_resizable_default_true() -> None:
    app = App(content=_FlagWidget())

    assert app.resizable is True


def test_app_resizable_explicit_false() -> None:
    app = App(content=_FlagWidget(), resizable=False)

    assert app.resizable is False


def test_app_with_intents_navigator_resizable_default_true() -> None:
    prev_nav = Navigator._root  # type: ignore[attr-defined]
    prev_overlay = Overlay._root_overlay  # type: ignore[attr-defined]
    try:
        Navigator._root = None  # type: ignore[attr-defined]
        Overlay._root_overlay = None  # type: ignore[attr-defined]

        app = App(
            Navigator.intents(
                initial_route=_HomeIntent(label="home"),
                routes={_HomeIntent: lambda i: _FlagWidget(label=i.label)},
            ),
        )

        assert app.resizable is True
    finally:
        Navigator._root = prev_nav  # type: ignore[attr-defined]
        Overlay._root_overlay = prev_overlay  # type: ignore[attr-defined]


def test_app_with_intents_navigator_resizable_explicit_false() -> None:
    prev_nav = Navigator._root  # type: ignore[attr-defined]
    prev_overlay = Overlay._root_overlay  # type: ignore[attr-defined]
    try:
        Navigator._root = None  # type: ignore[attr-defined]
        Overlay._root_overlay = None  # type: ignore[attr-defined]

        app = App(
            Navigator.intents(
                initial_route=_HomeIntent(label="home"),
                routes={_HomeIntent: lambda i: _FlagWidget(label=i.label)},
            ),
            resizable=False,
        )

        assert app.resizable is False
    finally:
        Navigator._root = prev_nav  # type: ignore[attr-defined]
        Overlay._root_overlay = prev_overlay  # type: ignore[attr-defined]


def test_material_app_resizable_default_true() -> None:
    prev_nav = Navigator._root  # type: ignore[attr-defined]
    prev_overlay = Overlay._root_overlay  # type: ignore[attr-defined]
    try:
        Navigator._root = None  # type: ignore[attr-defined]
        Overlay._root_overlay = None  # type: ignore[attr-defined]

        app = MaterialApp(content=_FlagWidget())

        assert app.resizable is True
    finally:
        Navigator._root = prev_nav  # type: ignore[attr-defined]
        Overlay._root_overlay = prev_overlay  # type: ignore[attr-defined]


def test_material_app_resizable_explicit_false() -> None:
    prev_nav = Navigator._root  # type: ignore[attr-defined]
    prev_overlay = Overlay._root_overlay  # type: ignore[attr-defined]
    try:
        Navigator._root = None  # type: ignore[attr-defined]
        Overlay._root_overlay = None  # type: ignore[attr-defined]

        app = MaterialApp(content=_FlagWidget(), resizable=False)

        assert app.resizable is False
    finally:
        Navigator._root = prev_nav  # type: ignore[attr-defined]
        Overlay._root_overlay = prev_overlay  # type: ignore[attr-defined]
