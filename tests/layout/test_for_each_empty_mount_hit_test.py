"""A ``*.builder`` list that was empty at mount stays hit-testable once filled.

``ForEach`` lifts its children into the parent's coordinate space and carries no
``layout_rect`` -- except when laid out empty, which stamped it with a zero-area
one that then gated away its own subtree.

Two things every test here is shaped around:

* **Assert the side effect, not the action.** ``click(key=...)`` resolves the
  target's rect and dispatches at the right coordinates either way, so it
  reports success even when the press lands on nothing.
* **Assert from a cold mount.** A rebuild re-runs ``build()`` with the list
  already populated, and the fresh provider gets no rect -- which is why hot
  reload hid this bug entirely.
"""

from __future__ import annotations

from typing import Callable, List

from nuiitivet.layout.column import Column
from nuiitivet.layout.flow import Flow
from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.row import Row
from nuiitivet.layout.stack import Stack
from nuiitivet.material.buttons import Button
from nuiitivet.material.text import Text
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget

import pytest

ITEMS = ("a", "b", "c")


class _BuilderScreen(ComposableWidget):
    """One ``*.builder`` fed by an ``Observable``, offset from the origin.

    The sibling ``Text`` is not decoration: it pushes the list off ``x = 0`` so a
    wrong descent cannot pass by landing on the origin.
    """

    def __init__(self, make: Callable[[Observable, Callable], Widget], items: Observable) -> None:
        super().__init__()
        self.make = make
        self.items = items
        self.clicks: List[str] = []

    def build(self) -> Widget:
        return Row(
            [
                Text("label", width=100),
                self.make(self.items, self._button),
            ],
            gap=8,
        )

    def _button(self, value: str, index: int) -> Widget:
        return Button(value, on_click=lambda value=value: self.clicks.append(value), key=f"b-{value}")


BUILDERS = {
    "row": lambda items, build: Row.builder(items, build, gap=8),
    "column": lambda items, build: Column.builder(items, build, gap=8),
    "flow": lambda items, build: Flow.builder(items, build, main_gap=8, cross_gap=8),
    "stack": lambda items, build: Stack.builder(items, build),
}


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_builder_items_arriving_after_mount_stay_clickable(nuiitivet_app, name: str) -> None:
    """The regression: empty at mount, filled afterwards, clicked from that mount."""

    screen = _BuilderScreen(BUILDERS[name], Observable(()))
    app = nuiitivet_app(screen, size=(600, 400))

    screen.items.value = ITEMS
    app.settle()
    app.click(key="b-c")

    assert screen.clicks == ["c"]


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_builder_items_present_at_mount_stay_clickable(nuiitivet_app, name: str) -> None:
    """The control: a list populated at mount always worked."""

    screen = _BuilderScreen(BUILDERS[name], Observable(ITEMS))
    app = nuiitivet_app(screen, size=(600, 400))

    app.click(key="b-c")

    assert screen.clicks == ["c"]


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_builder_grown_after_mount_stays_clickable(nuiitivet_app, name: str) -> None:
    """A list that was non-empty at mount never carried a rect to go stale."""

    screen = _BuilderScreen(BUILDERS[name], Observable(("a",)))
    app = nuiitivet_app(screen, size=(600, 400))

    screen.items.value = ITEMS
    app.settle()
    app.click(key="b-c")

    assert screen.clicks == ["c"]


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_builder_emptied_after_mount_stays_clickable_when_refilled(nuiitivet_app, name: str) -> None:
    """Emptying the list re-stamps the provider; refilling must clear the rect again."""

    screen = _BuilderScreen(BUILDERS[name], Observable(ITEMS))
    app = nuiitivet_app(screen, size=(600, 400))

    screen.items.value = ()
    app.settle()
    screen.items.value = ITEMS
    app.settle()
    app.click(key="b-c")

    assert screen.clicks == ["c"]


def test_provider_does_not_retain_a_layout_rect_once_it_has_items(nuiitivet_app) -> None:
    """The mechanism, asserted directly: no stale zero-area rect survives the refill."""

    screen = _BuilderScreen(BUILDERS["row"], Observable(()))
    app = nuiitivet_app(screen, size=(600, 400))

    screen.items.value = ITEMS
    app.settle()

    providers = _find(screen, ForEach)
    assert providers, "the builder should have materialized a ForEach"
    assert all(p.layout_rect is None for p in providers), [p.layout_rect for p in providers]


def _find(widget: Widget, kind: type) -> List[Widget]:
    """Collect every descendant of ``kind``, the built subtree included."""

    found: List[Widget] = []
    stack: List[Widget] = [widget]
    seen: set[int] = set()
    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        if isinstance(node, kind):
            found.append(node)
        stack.extend(getattr(node, "children", ()))
        built = getattr(node, "_built", None)
        if built is not None:
            stack.append(built)
    return found
