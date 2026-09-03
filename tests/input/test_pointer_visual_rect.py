"""Pointer input after ``hit_test`` resolves widget rects in *visual* space.

``hit_test`` compensates for scroll offsets; everything after it -- a widget
re-checking "is this point inside me", an anchor for a popup -- must read the
same space. Reading ``global_layout_rect`` is off by the scroll offset inside a
scrolled region, and reading ``last_rect`` is ``None`` until the first paint,
which under ``AppHarness`` (which lays out without painting) is forever.

Every test here drives a real ``App`` through the harness, so nothing paints:
a control that needs paint state to be clickable fails here the way it would
for one frame in the app.
"""

from __future__ import annotations

from typing import Optional

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.scrollable import HorizontalScrollable, VerticalScrollable
from nuiitivet.material.buttons import Button, ExtendedFab
from nuiitivet.material.slider import HorizontalSlider
from nuiitivet.material.text import Text
from nuiitivet.modifiers.block_pointer import block_pointer
from nuiitivet.modifiers.clickable import clickable
from nuiitivet.modifiers.clip import clip
from nuiitivet.modifiers.corner_radius import corner_radius
from nuiitivet.modifiers.defer_pointer import defer_pointer
from nuiitivet.modifiers.popup import popup
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget, Widget

import pytest

ROW = 48
VIEWPORT = 200
ROW_COUNT = 10


class _Cell(Widget):
    """A fixed-size leaf, so a scrolled column has a known content extent."""

    def __init__(self, key: str, *, width: int = 280, height: int = ROW) -> None:
        super().__init__(width=width, height=height, key=key)
        self._size = (width, height)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None):
        return self._size


def _rows(*, keys: list[str], insert: Optional[tuple[int, Widget]] = None) -> list[Widget]:
    rows: list[Widget] = [_Cell(k) for k in keys]
    if insert is not None:
        rows.insert(*insert)
    return rows


# -- WidgetKernel.global_visual_rect ----------------------------------------


def test_global_visual_rect_adds_every_ancestor_scroll_offset(nuiitivet_app) -> None:
    inner = VerticalScrollable(
        Column(children=_rows(keys=[f"r{i}" for i in range(ROW_COUNT)])),
        width=280,
        height=VIEWPORT,
        key="inner",
    )
    outer = HorizontalScrollable(
        Container(inner, width=600, height=VIEWPORT),
        width=300,
        height=VIEWPORT,
        key="outer",
    )
    app = nuiitivet_app(outer, size=(400, 400))

    row = app.get(key="r5")
    assert row.widget.global_visual_rect == row.widget.global_layout_rect

    app.scroll(key="inner", dy=3)
    app.scroll(key="outer", dx=2)

    lx, ly, lw, lh = row.widget.global_layout_rect
    vx, vy, vw, vh = row.widget.global_visual_rect
    assert (vw, vh) == (lw, lh)
    assert vy < ly, "vertical scroll moves the row up on screen"
    assert vx < lx, "horizontal scroll moves the row left on screen"
    # And it is exactly the sum of the two displacements, not one of them.
    dx_inner, dy_inner = inner._viewport.visual_offset()
    dx_outer, dy_outer = outer._viewport.visual_offset()
    assert (vx, vy) == (lx + dx_inner + dx_outer, ly + dy_inner + dy_outer)
    assert dy_inner < 0 and dx_outer < 0


def test_global_visual_rect_is_none_before_layout() -> None:
    assert _Cell("lonely").global_visual_rect is None


# -- B: interaction bounds without a paint ----------------------------------


class _ClickList(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.clicked: Observable[str] = Observable("")

    def build(self) -> Widget:
        rows = [
            Container(Text(f"row {i}"), width=280, height=ROW, key=f"row{i}").modifier(
                clickable(lambda i=i: self.clicked.set(f"row{i}"))
            )
            for i in range(ROW_COUNT)
        ]
        return VerticalScrollable(Column(children=rows), width=300, height=VIEWPORT, key="list")


def test_click_lands_inside_a_scrolled_region(nuiitivet_app) -> None:
    screen = _ClickList()
    app = nuiitivet_app(screen, size=(400, 400))

    app.scroll(key="list", dy=3)
    app.click(key="row8")

    assert screen.clicked.value == "row8"


class _ClippedButtons(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count = Observable(0)

    def build(self) -> Widget:
        bump = lambda: self.count.set(self.count.value + 1)  # noqa: E731
        return Column(
            children=[
                Button("plain", on_click=bump, key="plain"),
                Button("clipped", on_click=bump, key="clipped").modifier(clip()),
                Button("rounded", on_click=bump, key="rounded").modifier(corner_radius(8)),
                ExtendedFab("fab", on_click=bump, key="fab"),
            ]
        )


@pytest.mark.parametrize("key", ["plain", "clipped", "rounded", "fab"])
def test_clipping_boxes_are_clickable_without_a_paint(nuiitivet_app, key: str) -> None:
    screen = _ClippedButtons()
    app = nuiitivet_app(screen, size=(400, 400))

    app.click(key=key)

    assert screen.count.value == 1


# -- A1: Slider inside a scrolled region -------------------------------------


class _SliderList(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.value = Observable(0.0)

    def build(self) -> Widget:
        rows = _rows(
            keys=[f"r{i}" for i in range(ROW_COUNT)],
            insert=(5, HorizontalSlider(self.value, width=280, key="slider")),
        )
        return VerticalScrollable(Column(children=rows), width=300, height=VIEWPORT, key="list")


def test_slider_reacts_inside_a_scrolled_region(nuiitivet_app) -> None:
    screen = _SliderList()
    app = nuiitivet_app(screen, size=(400, 400))

    app.scroll(key="list", dy=3)
    x, y, w, h = app.get(key="slider").widget.global_visual_rect
    app.click(x=x + w * 0.75, y=y + h / 2)

    assert screen.value.value > 0.5


# -- A2: popup anchored inside a scrolled region -----------------------------


class _PopupList(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.is_open: Observable[bool] = Observable(False)

    def build(self) -> Widget:
        anchor = Container(Text("anchor"), width=280, height=ROW, key="anchor").modifier(
            popup(Container(Text("panel"), width=120, height=60, key="panel"), is_open=self.is_open)
        )
        rows = _rows(keys=[f"r{i}" for i in range(ROW_COUNT)], insert=(5, anchor))
        return VerticalScrollable(Column(children=rows), width=300, height=VIEWPORT, key="list")


def test_popup_opens_at_the_anchor_as_painted(nuiitivet_app) -> None:
    screen = _PopupList()
    app = nuiitivet_app(screen, size=(400, 400))

    app.scroll(key="list", dy=3)
    ax, ay, aw, ah = app.get(key="anchor").widget.global_visual_rect
    assert ay < app.get(key="anchor").widget.global_layout_rect[1], "precondition: the anchor is scrolled"

    screen.is_open.value = True
    app.settle()

    px, py, _pw, _ph = app.get(key="panel").widget.global_visual_rect
    assert (px, py) == (ax, ay + ah)


# -- A5: block_pointer / defer_pointer over a ComposableWidget ---------------


class _Wrapped(ComposableWidget):
    """A widget with a ``build()``, so its content lives in ``_built``, not ``children``."""

    def __init__(self, on_click) -> None:
        super().__init__()
        self._on_click = on_click

    def build(self) -> Widget:
        return Container(Text("inner"), width=200, height=ROW, key="inner").modifier(clickable(self._on_click))


class _ParticipationScreen(ComposableWidget):
    def __init__(self, participation) -> None:
        super().__init__()
        self._participation = participation
        self.clicks = Observable(0)

    def build(self) -> Widget:
        return _Wrapped(lambda: self.clicks.set(self.clicks.value + 1)).modifier(self._participation())


@pytest.mark.parametrize("participation", [block_pointer, defer_pointer])
def test_pointer_participation_descends_into_a_built_subtree(nuiitivet_app, participation) -> None:
    """Both postures govern the wrapped widget's *own* surface and leave its
    content reachable; a ``build()`` must not hide that content from them."""
    screen = _ParticipationScreen(participation)
    app = nuiitivet_app(screen, size=(400, 400))

    app.click(key="inner")

    assert screen.clicks.value == 1
