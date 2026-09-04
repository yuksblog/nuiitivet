"""Tests for Navigator (Phase 3 MVP)."""

from nuiitivet.layout.container import Container
from nuiitivet.navigation import Navigator, Route
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgeting.widget import Widget


class _FlagWidget(Widget):
    def __init__(self) -> None:
        super().__init__()
        self.unmounted = False

    def on_unmount(self) -> None:
        self.unmounted = True
        super().on_unmount()

    def build(self) -> Widget:
        return self


def test_navigator_of_falls_back_to_the_app_navigator() -> None:
    """An overlay entry hangs beside the Navigator, not under it.

    So there is no ancestor to walk to, and the App-scoped fallback is the only
    thing that makes ``Navigator.of`` work from inside a dialog.
    """
    app = App(Window(content=Container())).main_window
    app.root.mount(app)
    dialog = Container()
    app.overlay.show(dialog)

    assert Navigator.of(dialog) is app.navigator


def test_navigator_push_sets_built_child() -> None:
    nav = Navigator()
    page = _FlagWidget()

    nav.push(page)

    # Navigator keeps the pushed widget as a child.
    assert page in nav.children_snapshot()


async def test_navigator_pop_disposes_route_widget(nuiitivet_mount) -> None:
    nav = Navigator(Route(builder=_FlagWidget))
    host = nuiitivet_mount(nav)
    host.layout(200, 100)

    page2 = _FlagWidget()
    nav.push(page2)
    assert nav.can_pop() is True

    nav.pop()
    await host.idle()  # the pop runs as a task; idle() is what awaits it
    assert page2.unmounted is True


async def test_navigator_pop_noop_when_single_route(nuiitivet_mount) -> None:
    nav = Navigator(Route(builder=_FlagWidget))
    host = nuiitivet_mount(nav)
    host.layout(200, 100)
    nav.rebuild()

    nav.pop()
    await host.idle()
    assert nav.can_pop() is False


def test_navigator_of_context_uses_ancestor_chain() -> None:
    nav = Navigator()
    child = Widget()
    child._parent = nav  # type: ignore[attr-defined]

    assert Navigator.of(child) is nav
