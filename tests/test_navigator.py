"""Tests for Navigator (Phase 3 MVP)."""

from nuiitivet.navigation import Navigator, PageRoute
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


def test_navigator_root_set_get() -> None:
    nav = Navigator()
    Navigator.set_root(nav)
    assert Navigator.root() is nav


def test_navigator_push_sets_built_child() -> None:
    nav = Navigator()
    page = _FlagWidget()

    nav.push(page)

    # Navigator keeps the pushed widget as a child.
    assert page in nav.children_snapshot()


def test_navigator_pop_disposes_route_widget() -> None:
    nav = Navigator([PageRoute(builder=_FlagWidget)])

    page2 = _FlagWidget()
    nav.push(page2)
    assert nav.can_pop() is True

    nav.pop()
    assert page2.unmounted is True


def test_navigator_pop_noop_when_single_route() -> None:
    nav = Navigator([PageRoute(builder=_FlagWidget)])
    nav.rebuild()
    nav.pop()
    assert nav.can_pop() is False


def test_navigator_of_context_uses_ancestor_chain() -> None:
    nav = Navigator()
    child = Widget()
    child._parent = nav  # type: ignore[attr-defined]

    assert Navigator.of(child) is nav
