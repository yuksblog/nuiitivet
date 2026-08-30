"""Tests for Phase 6 app initialization patterns."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.layout.geometry import Geometry
from nuiitivet.rendering.size import Size
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.stack import Stack
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.window import MaterialWindow
from nuiitivet.navigation import Navigator
from nuiitivet.runtime.app import App, AppScope
from nuiitivet.runtime.window import Window, WindowScope
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


def test_app_content_is_wrapped_in_a_navigator_and_overlay_stack() -> None:
    app = App(Window(content=_FlagWidget(label="content"))).main_window

    assert isinstance(app.root, AppScope)
    window_scope = app.root.children_snapshot()[0]
    assert isinstance(window_scope, WindowScope)
    geometry = window_scope.children_snapshot()[0]
    assert isinstance(geometry, Geometry)
    stack = geometry.children_snapshot()[0]
    assert isinstance(stack, Stack)
    assert stack.children_snapshot()[0] is app.navigator
    assert stack.children_snapshot()[1] is app.overlay


def test_app_installs_root_geometry_provider() -> None:
    content = _FlagWidget(label="content")
    app = App(Window(content=content)).main_window

    geometry = app.root.children_snapshot()[0].children_snapshot()[0]
    assert isinstance(geometry, Geometry)

    # The root Geometry measures the window through the normal layout pass:
    # laying out the app root publishes the window size, and a content widget
    # resolves Geometry.of(...) to this root provider.
    app.root.layout(800, 600)
    assert geometry.size.value == Size(800, 600)
    assert Geometry.of(content) is geometry


@dataclass(frozen=True, slots=True)
class _HomeIntent:
    label: str


def test_app_with_intents_navigator_becomes_the_app_navigator() -> None:
    app = App(
        Window(
            content=Navigator.intents(
                initial_route=_HomeIntent(label="home"),
                routes={
                    _HomeIntent: lambda i: _FlagWidget(label=i.label),
                },
            ),
        ),
    ).main_window

    assert isinstance(app.root, AppScope)
    window_scope = app.root.children_snapshot()[0]
    assert isinstance(window_scope, WindowScope)
    geometry = window_scope.children_snapshot()[0]
    assert isinstance(geometry, Geometry)
    stack = geometry.children_snapshot()[0]
    assert isinstance(stack, Stack)
    assert stack.children_snapshot()[0] is app.navigator
    assert stack.children_snapshot()[1] is app.overlay


def test_two_apps_resolve_their_own_navigator_and_overlay() -> None:
    """The point of #518: no process-global root to collide over."""
    first = App(Window(content=_FlagWidget(label="first"))).main_window
    second = App(Window(content=_FlagWidget(label="second"))).main_window

    assert first.navigator is not second.navigator
    assert first.overlay is not second.overlay


def test_a_rebuild_is_adopted_only_once_committed() -> None:
    """Building must not touch the App; only the commit hands over (#518)."""
    app = App(Window(content=_FlagWidget(label="first"))).main_window
    original_navigator = app.navigator
    original_overlay = app.overlay

    rebuilt = app._rebuild_content_root(lambda: _FlagWidget(label="second"))

    # Built but not installed: the App still points at what is on screen.
    assert rebuilt.navigator is not original_navigator
    assert app.navigator is original_navigator
    assert app.overlay is original_overlay

    app._commit_content_root(rebuilt)

    assert app.navigator is rebuilt.navigator
    assert app.overlay is rebuilt.overlay


def test_a_reload_that_fails_to_commit_leaves_the_live_tree_addressable() -> None:
    """A build that never goes on screen must not become what the App reaches for.

    Otherwise the reload error banner is shown on an unmounted overlay and back
    handling drives a navigator the user cannot see.
    """
    app = App(Window(content=_FlagWidget(label="first"))).main_window
    original_navigator = app.navigator
    original_overlay = app.overlay

    def _explode() -> Widget:
        raise RuntimeError("boom")

    try:
        app._commit_content_root(app._rebuild_content_root(_explode))
    except RuntimeError:
        pass

    assert app.navigator is original_navigator
    assert app.overlay is original_overlay


def test_app_auto_window_size_measures_unmounted_composable_children() -> None:
    content = Column(
        children=[_ComposableFixedBox()],
        gap=16,
        padding=16,
    )

    app = App(Window(content=content, width="auto", height="auto")).main_window

    assert app.width == 232
    assert app.height == 82


def test_app_resizable_default_true() -> None:
    app = App(Window(content=_FlagWidget())).main_window

    assert app.resizable is True


def test_app_resizable_explicit_false() -> None:
    app = App(Window(content=_FlagWidget(), resizable=False)).main_window

    assert app.resizable is False


def test_app_with_intents_navigator_resizable_default_true() -> None:
    app = App(
        Window(
            content=Navigator.intents(
                initial_route=_HomeIntent(label="home"),
                routes={_HomeIntent: lambda i: _FlagWidget(label=i.label)},
            ),
        ),
    ).main_window

    assert app.resizable is True


def test_app_with_intents_navigator_resizable_explicit_false() -> None:
    app = App(
        Window(
            content=Navigator.intents(
                initial_route=_HomeIntent(label="home"),
                routes={_HomeIntent: lambda i: _FlagWidget(label=i.label)},
            ),
            resizable=False,
        ),
    ).main_window

    assert app.resizable is False


def test_material_app_resizable_default_true() -> None:
    app = MaterialApp(MaterialWindow(content=_FlagWidget())).main_window

    assert app.resizable is True


def test_material_app_resizable_explicit_false() -> None:
    app = MaterialApp(MaterialWindow(content=_FlagWidget(), resizable=False)).main_window

    assert app.resizable is False
