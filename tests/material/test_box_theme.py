"""A Box follows the theme by reading it, not by subscribing to it.

``BackgroundRenderer`` resolves ``Box``'s colours through ``Theme.of`` at paint
time. That read registers the Box as a theme reader, and a theme change drops
its paint cache. Nothing subscribes, so nothing has to unsubscribe.
"""

from __future__ import annotations

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.runtime.app import AppScope
from nuiitivet.theme.manager import ThemeManager
from nuiitivet.theme.theme import Theme
from nuiitivet.widgets.box import Box


class _StubApp:
    """Minimum an ``AppScope`` needs: a theme manager and a weak-referenceable
    identity."""

    def __init__(self, manager: ThemeManager) -> None:
        self._theme_manager = manager


def _scope(box: Box, theme: Theme) -> ThemeManager:
    from nuiitivet.theme.dependency import invalidate_theme_readers

    manager = ThemeManager(theme)
    app = _StubApp(manager)
    scope = AppScope(app, box)  # type: ignore[arg-type]
    # The real App fans a theme change out to each window's tree; mimic it.
    manager.on_change = lambda _theme: invalidate_theme_readers(scope)
    scope.mount(app)
    box._test_scope = scope  # type: ignore[attr-defined]
    return manager


def test_reading_a_theme_colour_marks_the_box_as_a_reader() -> None:
    box = Box(background_color=ColorRole.PRIMARY)
    _scope(box, Theme(mode="light", extensions=[]))

    assert getattr(box, "_reads_theme", False) is False
    Theme.of(box)
    assert getattr(box, "_reads_theme", False) is True


def test_a_theme_change_drops_the_readers_paint_cache() -> None:
    box = Box(background_color=ColorRole.PRIMARY)
    manager = _scope(box, Theme(mode="light", extensions=[]))
    Theme.of(box)

    calls: list[str] = []
    box.invalidate_paint_cache = lambda: calls.append("cache")  # type: ignore[method-assign]

    manager.set_theme(Theme(mode="dark", extensions=[]))

    assert calls == ["cache"]


def test_a_box_that_never_read_the_theme_is_left_alone() -> None:
    box = Box(background_color="#FFFFFF")
    manager = _scope(box, Theme(mode="light", extensions=[]))

    calls: list[str] = []
    box.invalidate_paint_cache = lambda: calls.append("cache")  # type: ignore[method-assign]

    manager.set_theme(Theme(mode="dark", extensions=[]))

    assert calls == []


def test_the_box_holds_no_reference_from_the_provider() -> None:
    """The mark lives on the reader, so there is nothing to unsubscribe."""
    box = Box(background_color=ColorRole.PRIMARY)
    manager = _scope(box, Theme(mode="light", extensions=[]))
    Theme.of(box)

    assert not hasattr(manager, "_subscribers")
