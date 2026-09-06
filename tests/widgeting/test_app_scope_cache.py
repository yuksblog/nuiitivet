"""``find_app_scope`` remembers the walk for a mount, and forgets it on the way out.

The lookup runs on every paint of every leaf, so it must not walk the tree each
time; but a widget that leaves its tree must neither answer with the old scope
nor keep that old tree alive through the cache.
"""

from nuiitivet.layout.container import Container
from nuiitivet.runtime.app import AppScope
from nuiitivet.theme.manager import ThemeManager
from nuiitivet.theme.theme import Theme
from nuiitivet.widgeting.context_lookup import find_app_scope
from nuiitivet.widgeting.widget import Widget


class _StubApp:
    def __init__(self) -> None:
        self._theme_manager = ThemeManager(Theme(mode="light", extensions=[]))


def _mounted_scope(child: Widget) -> AppScope:
    app = _StubApp()
    scope = AppScope(app, Container(child=child))  # type: ignore[arg-type]
    scope.mount(app)
    return scope


def test_the_walk_happens_once_per_mount() -> None:
    leaf = Widget()
    scope = _mounted_scope(leaf)

    assert find_app_scope(leaf) is scope
    # The parent link is gone, so a fresh walk would find nothing.
    leaf._parent = None
    assert find_app_scope(leaf) is scope


def test_a_detached_widget_is_not_remembered() -> None:
    leaf = Widget()
    Container().add_child(leaf)

    assert find_app_scope(leaf) is None

    scope = _mounted_scope(leaf)
    assert find_app_scope(leaf) is scope


def test_unmount_forgets_the_scope() -> None:
    leaf = Widget()
    scope = _mounted_scope(leaf)
    find_app_scope(leaf)

    scope.unmount()
    assert leaf._app_scope is None

    # Still linked, so a fresh walk finds the scope again; cut the link and it
    # does not -- the cache is not consulted.
    assert find_app_scope(leaf) is scope
    leaf._app_scope = None
    leaf._parent = None
    assert find_app_scope(leaf) is None


def test_a_remount_elsewhere_resolves_the_new_scope() -> None:
    leaf = Widget()
    first = _mounted_scope(leaf)
    assert find_app_scope(leaf) is first

    first.unmount()
    second = _mounted_scope(leaf)

    assert find_app_scope(leaf) is second
    assert Theme.of(leaf) is second.theme_manager.current
