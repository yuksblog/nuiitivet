"""Reading the theme is how a widget subscribes to it.

``Theme.of`` marks its reader, and a theme change invalidates every marked
reader the provider can reach. Nothing registers with the provider, so nothing
has to deregister. See ``docs/design/THEME_CONSUMPTION.md``.
"""

from __future__ import annotations

from typing import List

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.runtime.app import AppScope
from nuiitivet.theme.manager import ThemeManager
from nuiitivet.theme.theme import Theme
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class _StubApp:
    """Minimum an ``AppScope`` needs: a theme manager and a weak-referenceable
    identity."""

    def __init__(self, manager: ThemeManager) -> None:
        self._theme_manager = manager


def _scope(root: Widget, theme: Theme | None = None) -> ThemeManager:
    """Attach ``root`` under an ``AppScope`` and return the scope's manager."""
    manager = ThemeManager(theme or Theme(mode="light", extensions=[]))
    app = _StubApp(manager)
    scope = AppScope(app, root)  # type: ignore[arg-type]
    scope.mount(app)
    root._test_scope = scope  # type: ignore[attr-defined]
    return manager


class _Leaf(Widget):
    """A leaf that reads the theme where the value is consumed."""

    def __init__(self) -> None:
        super().__init__()
        self.reads = 0
        self.relayouts = 0
        self.repaints = 0

    def preferred_size(self, max_width=None, max_height=None):  # type: ignore[no-untyped-def]
        Theme.of(self)
        self.reads += 1
        return (1, 1)

    def mark_needs_layout(self) -> None:
        self.relayouts += 1
        super().mark_needs_layout()

    def invalidate(self, immediate: bool = False) -> None:
        self.repaints += 1
        super().invalidate(immediate)


class _Composable(ComposableWidget):
    """A composable that reads the theme in ``build()``."""

    def __init__(self) -> None:
        super().__init__()
        self.modes: List[str] = []

    def build(self) -> Widget:
        self.modes.append(Theme.of(self).mode)
        return Container()


def test_reading_marks_the_reader() -> None:
    leaf = _Leaf()
    _scope(leaf)

    assert getattr(leaf, "_reads_theme", False) is False
    leaf.preferred_size()
    assert getattr(leaf, "_reads_theme", False) is True


def test_a_read_inside_build_is_attributed_to_the_building_host() -> None:
    """Not to whichever widget was handed in: a change must rebuild the build."""
    host = _Composable()
    inner = Widget()
    _scope(host)

    host.evaluate_build()

    assert getattr(host, "_reads_theme", False) is True
    assert getattr(inner, "_reads_theme", False) is False


def test_a_theme_change_re_measures_and_repaints_a_leaf_reader() -> None:
    leaf = _Leaf()
    manager = _scope(leaf)
    leaf.preferred_size()
    before_layout, before_paint = leaf.relayouts, leaf.repaints

    manager.set_theme(Theme(mode="dark", extensions=[]))

    assert leaf.relayouts > before_layout
    assert leaf.repaints > before_paint


def test_a_theme_change_rebuilds_a_composable_reader() -> None:
    host = _Composable()
    manager = _scope(host)  # mounting builds it once
    assert host.modes[-1] == "light"

    manager.set_theme(Theme(mode="dark", extensions=[]))

    assert host.modes[-1] == "dark"


def test_a_widget_that_never_read_is_left_alone() -> None:
    quiet = _Leaf()
    manager = _scope(quiet)
    # Deliberately no read.

    manager.set_theme(Theme(mode="dark", extensions=[]))

    assert quiet.relayouts == 0
    assert quiet.repaints == 0


def test_a_reader_deep_in_the_subtree_is_reached() -> None:
    leaf = _Leaf()
    middle = Container()
    middle.add_child(leaf)
    root = Container()
    root.add_child(middle)
    manager = _scope(root)
    leaf.preferred_size()

    manager.set_theme(Theme(mode="dark", extensions=[]))

    assert leaf.relayouts == 1


def test_the_provider_holds_no_reference_to_its_readers() -> None:
    """Release is automatic because the mark lives on the reader."""
    leaf = _Leaf()
    manager = _scope(leaf)
    leaf.preferred_size()

    assert not hasattr(manager, "_subscribers")
    assert manager.on_change is not None


def test_reading_before_super_init_is_an_error() -> None:
    class _TooEarly(Widget):
        def __init__(self) -> None:
            Theme.of(self)
            super().__init__()

    with pytest.raises(RuntimeError, match=r"before super\(\)\.__init__\(\)"):
        _TooEarly()


def test_reading_from_a_detached_widget_falls_back_instead_of_raising() -> None:
    """Paint code runs on every frame, including for deliberately detached
    trees, so a missing provider must not crash."""
    child = Widget()
    Container().add_child(child)

    assert Theme.of(child).mode == "light"
