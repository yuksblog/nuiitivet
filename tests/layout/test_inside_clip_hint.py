"""Which wrappers carry the inside-clip hint to a container below them, and which stop it."""

from __future__ import annotations

from typing import Any, Callable, List, Sequence
from unittest.mock import patch

import pytest
import skia

from nuiitivet.layout import layout_utils
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.cross_aligned import CrossAligned
from nuiitivet.layout.deck import Deck
from nuiitivet.layout.geometry import Geometry
from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.layout.stack import Stack
from nuiitivet.modifiers.clickable import clickable
from nuiitivet.modifiers.clip import clip
from nuiitivet.modifiers.transform import opacity, translate
from nuiitivet.modifiers.visible import visible
from nuiitivet.modifiers.will_pop import will_pop
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.testing import mount
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box

SIZE = 400


class _Leaf(Box):
    def __init__(self) -> None:
        super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(50))
        self.painted = 0

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1


def _canvas(width: int = SIZE, height: int = SIZE) -> Any:
    surface: Any = skia.Surface  # the local stub declares no constructor
    return surface(width, height).getCanvas()


def _painted(leaves: Sequence[Any]) -> list[int]:
    return [i for i, leaf in enumerate(leaves) if leaf.painted]


def _composable(child: Widget) -> Widget:
    class _Host(ComposableWidget):
        def build(self) -> Widget:
            return child

    return _Host()


PASSING: dict[str, Callable[[Widget], Widget]] = {
    "composable": _composable,
    "container": lambda child: Container(child),
    "box": lambda child: Box(child),
    "stack": lambda child: Stack([child]),
    "deck": lambda child: Deck([child]),
    "geometry": lambda child: Geometry(child),
    "cross_aligned": lambda child: CrossAligned(child, "start"),
    "opacity": lambda child: child.modifier(opacity(1.0)),
    "visible": lambda child: child.modifier(visible(True)),
    "clickable": lambda child: child.modifier(clickable(lambda: None)),
    "will_pop": lambda child: child.modifier(will_pop(lambda: True)),
}


def _clip_reads() -> Any:
    return patch.object(layout_utils, "local_clip_bounds", wraps=layout_utils.local_clip_bounds)


@pytest.mark.parametrize("wrap", list(PASSING.values()), ids=list(PASSING))
def test_a_container_under_a_passing_wrapper_does_not_read_the_clip(wrap) -> None:
    leaves: List[Widget] = [_Leaf() for _ in range(3)]
    outer = Column(children=[wrap(Column(children=leaves))])
    with mount(outer, leak_check="off") as host:
        host.layout(SIZE, SIZE)
        canvas = _canvas()

        with _clip_reads() as reads:
            outer.paint(canvas, 0, 0, SIZE, SIZE)

    assert reads.call_count == 1
    assert _painted(leaves) == [0, 1, 2]


@pytest.mark.parametrize("wrap", list(PASSING.values()), ids=list(PASSING))
def test_a_passing_wrapper_that_crosses_the_clip_passes_nothing(wrap) -> None:
    # Ten 50px leaves on a 100px canvas: the wrapper is not inside the clip, so
    # the container below it reads the clip and culls.
    leaves: List[Widget] = [_Leaf() for _ in range(10)]
    outer = Column(children=[wrap(Column(children=leaves))])
    with mount(outer, leak_check="off") as host:
        host.layout(100, 500)

        with _clip_reads() as reads:
            outer.paint(_canvas(100, 100), 0, 0, 100, 500)

    assert reads.call_count == 2
    assert _painted(leaves) == [0, 1, 2]


def test_a_scroll_viewport_stops_the_hint() -> None:
    leaves = [_Leaf() for _ in range(10)]
    viewport = ScrollViewport(
        child=Column(children=leaves),
        controller=ScrollController(),
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
    )
    outer = Column(children=[viewport])
    outer.layout(SIZE, SIZE)

    with _clip_reads() as reads:
        outer.paint(_canvas(), 0, 0, SIZE, SIZE)

    assert reads.call_count == 2
    assert _painted(leaves) == [0, 1, 2]


def test_a_clipping_box_stops_the_hint() -> None:
    # The clipped box is 100px tall and lies inside the canvas; its content is 500px.
    leaves: List[Widget] = [_Leaf() for _ in range(10)]
    clipped = Container(Column(children=leaves), height=100).modifier(clip())
    outer = Column(children=[clipped])
    with mount(outer, leak_check="off") as host:
        host.layout(SIZE, SIZE)

        with _clip_reads() as reads:
            outer.paint(_canvas(), 0, 0, SIZE, SIZE)

    assert reads.call_count == 2
    assert _painted(leaves) == [0, 1, 2]


def test_a_transform_stops_the_hint() -> None:
    # The list is moved wholly above the canvas: nothing of it should be painted.
    leaves: List[Widget] = [_Leaf() for _ in range(4)]
    moved = Column(children=leaves).modifier(translate((0, -300)))
    outer = Column(children=[moved])
    with mount(outer, leak_check="off") as host:
        host.layout(SIZE, SIZE)

        with _clip_reads() as reads:
            outer.paint(_canvas(), 0, 0, SIZE, SIZE)

    assert reads.call_count == 2
    assert _painted(leaves) == []


def test_a_hint_that_was_not_passed_is_not_kept_for_the_next_paint() -> None:
    leaves: List[Widget] = [_Leaf() for _ in range(10)]
    inner = Column(children=leaves)
    clipped: Any = Container(inner, height=100).modifier(clip())
    with mount(clipped, leak_check="off") as host:
        host.layout(100, 100)

        clipped._paint_inside_clip = True
        clipped.paint(_canvas(100, 100), 0, 0, 100, 100)

        assert clipped._paint_inside_clip is False
        assert inner._paint_inside_clip is False
        assert _painted(leaves) == [0, 1, 2]


def test_take_inside_clip_forgets_the_hint() -> None:
    widget: Any = _Leaf()
    assert widget._take_inside_clip() is False

    widget._paint_inside_clip = True

    assert widget._take_inside_clip() is True
    assert widget._take_inside_clip() is False
