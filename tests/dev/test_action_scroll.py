"""Integration tests for the dev bridge's scroll actions (#493).

Deliberately built on real ``VerticalScrollable`` / ``HorizontalScrollable``
widgets rather than the ``_Node`` fake in ``test_action.py``: that fake sets
``global_layout_rect`` directly, so it cannot express the difference between
content space and screen space -- which is the whole bug these cover. Only a
real scroll region has an offset that makes the two disagree.
"""

from __future__ import annotations

from typing import Any, Optional

import pytest

from nuiitivet.dev.action import (
    TargetNotVisibleError,
    click,
    scroll,
    scroll_into_view,
)
from nuiitivet.dev.perception import global_visual_rect
from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.scrollable import HorizontalScrollable, VerticalScrollable
from nuiitivet.layout.stack import Stack
from nuiitivet.runtime import app_events
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.widgeting.widget import Widget

ROW_SIZE = 40
ROW_COUNT = 10
VIEWPORT = 100
#: 10 rows of 40 in a 100px viewport -> 400 - 100.
MAX_EXTENT = float(ROW_COUNT * ROW_SIZE - VIEWPORT)


class _Cell(Widget):
    """A hit-testable row/column cell that records the presses it receives.

    Overriding ``on_pointer_event`` is what makes ``hit_test`` catch on it (the
    ``auto`` policy), so a click that lands on it is observable -- and a click
    that lands somewhere else is observable by its absence.
    """

    def __init__(self, key: str, *, width: int = VIEWPORT, height: int = ROW_SIZE) -> None:
        super().__init__(width=width, height=height, key=key)
        self._size = (width, height)
        self.presses: list[tuple[float, float]] = []

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None):
        return self._size

    def on_pointer_event(self, event: PointerEvent) -> bool:
        if event.type is PointerEventType.PRESS:
            self.presses.append((event.x, event.y))
            return True
        return False


class _App:
    """A minimal app that routes synthesized input through the real dispatch.

    Only the surface the action verbs touch: the tree, its size, and the three
    ``_dispatch_*`` entry points -- which delegate to ``runtime/app_events.py``
    so hit testing, bubbling and scroll handling are the app's own, not a mock's.
    """

    def __init__(self, root: Widget, *, width: int = VIEWPORT, height: int = VIEWPORT) -> None:
        self.root = root
        self.width = width
        self.height = height
        self.invalidated = 0
        self._pointer_capture_manager = PointerCaptureManager()
        self._pressed_target: Optional[Widget] = None
        self._last_hover_target: Optional[Widget] = None
        root.layout(width, height)

    def invalidate(self, immediate: bool = False) -> None:
        self.invalidated += 1

    def request_focus(self, node: Any) -> None:
        pass

    def _dispatch_mouse_press(self, x: int, y: int, *, button: Optional[int] = None) -> None:
        app_events.dispatch_mouse_press(self, x, y, button=button)

    def _dispatch_mouse_release(self, x: int, y: int, *, button: Optional[int] = None) -> None:
        app_events.dispatch_mouse_release(self, x, y, button=button)

    def _dispatch_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float):
        return app_events.dispatch_mouse_scroll(self, x, y, scroll_x, scroll_y)


def _vertical() -> tuple[_App, VerticalScrollable, list[_Cell]]:
    cells = [_Cell(f"row-{i}") for i in range(ROW_COUNT)]
    scroller = VerticalScrollable(Column(cells), width=VIEWPORT, height=VIEWPORT)
    scroller.key = "feed"
    return (_App(scroller), scroller, cells)


def _horizontal() -> tuple[_App, HorizontalScrollable, list[_Cell]]:
    cells = [_Cell(f"col-{i}", width=ROW_SIZE, height=VIEWPORT) for i in range(ROW_COUNT)]
    scroller = HorizontalScrollable(Row(list(cells)), width=VIEWPORT, height=VIEWPORT)
    scroller.key = "strip"
    return (_App(scroller), scroller, cells)


# --- Target resolution inside a scrolled region ----------------------------


def test_global_visual_rect_follows_the_scroll_offset() -> None:
    """The painted rect tracks the offset; the layout rect stays content space."""
    app, scroller, cells = _vertical()
    scroller.scroll_to(150.0)

    row = cells[4]
    assert row.global_layout_rect == (0, 160, VIEWPORT, ROW_SIZE)
    assert global_visual_rect(row) == (0.0, 10.0, float(VIEWPORT), float(ROW_SIZE))
    assert app.root is scroller


def test_click_inside_a_scrolled_region_lands_on_the_row() -> None:
    """The click reaches the row it names, at its on-screen position."""
    app, scroller, cells = _vertical()
    scroller.scroll_to(150.0)

    result = click(app, key="row-4")

    # Content y 160..200, minus the 150 offset -> 10..50 on screen; centre 30.
    assert result == {"clicked": {"type": "_Cell", "key": "row-4"}, "x": 50, "y": 30}
    assert len(cells[4].presses) == 1
    assert not any(cell.presses for cell in cells if cell is not cells[4])


def test_click_on_a_row_scrolled_out_of_view_raises() -> None:
    """A target below the fold is an error, not a click delivered elsewhere."""
    app, _scroller, cells = _vertical()

    with pytest.raises(TargetNotVisibleError) as excinfo:
        click(app, key="row-9")

    assert "scroll_into_view" in str(excinfo.value)
    assert not any(cell.presses for cell in cells)


def test_click_on_a_row_scrolled_above_the_fold_raises() -> None:
    """Symmetric: scrolled off the *top* is just as unreachable."""
    app, scroller, _cells = _vertical()
    scroller.scroll_to(MAX_EXTENT)

    with pytest.raises(TargetNotVisibleError):
        click(app, key="row-0")


def test_click_on_a_covered_target_raises() -> None:
    """The other half of "cannot reach it": something is painted on top."""
    beneath = _Cell("beneath", height=VIEWPORT)
    modal = _Cell("modal", height=VIEWPORT)
    app = _App(Stack([beneath, modal]))

    with pytest.raises(TargetNotVisibleError, match="covered by"):
        click(app, key="beneath")

    assert not beneath.presses
    # The one on top is still perfectly clickable.
    click(app, key="modal")
    assert len(modal.presses) == 1


# --- scroll ----------------------------------------------------------------


def test_scroll_moves_the_region_and_reports_where_it_landed() -> None:
    app, scroller, _cells = _vertical()

    result = scroll(app, key="feed", dy=5.0)

    # 5 notches * the 20px default multiplier.
    assert scroller.scroll_offset == 100.0
    assert result["handled"] is True
    assert result["handled_by"] == {"type": "VerticalScrollable", "key": "feed"}
    assert result["offset"] == 100.0
    assert result["max_extent"] == MAX_EXTENT
    assert result["axis"] == "vertical"
    assert result["at_start"] is False
    assert result["at_end"] is False
    assert (result["dx"], result["dy"]) == (0.0, 5.0)


def test_scroll_sign_convention_matches_the_controller_offset() -> None:
    """Positive is toward the content's end -- the offset grows, and back."""
    app, scroller, _cells = _vertical()

    scroll(app, key="feed", dy=4.0)
    assert scroller.scroll_offset == 80.0

    scroll(app, key="feed", dy=-1.0)
    assert scroller.scroll_offset == 60.0


def test_scroll_is_linear_so_one_call_equals_many() -> None:
    app_a, scroller_a, _ = _vertical()
    app_b, scroller_b, _ = _vertical()

    scroll(app_a, key="feed", dy=5.0)
    for _ in range(5):
        scroll(app_b, key="feed", dy=1.0)

    assert scroller_a.scroll_offset == scroller_b.scroll_offset


def test_scroll_moves_a_horizontal_region_in_both_signs() -> None:
    app, scroller, _cells = _horizontal()

    result = scroll(app, key="strip", dx=3.0)
    assert scroller.scroll_offset == 60.0
    assert result["axis"] == "horizontal"
    assert result["max_extent"] == MAX_EXTENT

    scroll(app, key="strip", dx=-2.0)
    assert scroller.scroll_offset == 20.0


def test_scroll_at_the_end_reports_at_end_with_an_unchanged_offset() -> None:
    """The stop condition: consumed, but nothing moved."""
    app, scroller, _cells = _vertical()
    scroller.scroll_to(MAX_EXTENT)

    result = scroll(app, key="feed", dy=5.0)

    assert scroller.scroll_offset == MAX_EXTENT
    assert result["handled"] is True
    assert result["offset"] == MAX_EXTENT
    assert result["at_end"] is True


def test_scroll_at_the_start_reports_at_start() -> None:
    app, scroller, _cells = _vertical()

    result = scroll(app, key="feed", dy=-3.0)

    assert scroller.scroll_offset == 0.0
    assert result["at_start"] is True
    assert result["offset"] == 0.0


def test_scroll_with_no_delta_is_rejected() -> None:
    app, _scroller, _cells = _vertical()

    with pytest.raises(ValueError, match="non-zero"):
        scroll(app, key="feed")


def test_scroll_reports_unhandled_when_nothing_scrolls_at_those_coordinates() -> None:
    """Coordinates are taken as given, so a dead spot reports rather than raises."""
    app = _App(Column([_Cell("lonely")]))

    result = scroll(app, x=50, y=20, dy=3.0)

    assert result["handled"] is False
    assert "offset" not in result


def test_scroll_refuses_a_target_that_is_not_a_scroll_region() -> None:
    """Naming a row is the tempting mistake -- and a self-defeating one."""
    app, _scroller, cells = _vertical()

    with pytest.raises(ValueError) as excinfo:
        scroll(app, key="row-2", dy=5.0)

    message = str(excinfo.value)
    assert "not a scrollable region" in message
    # The error hands over what to target instead: the enclosing region, the
    # app-authored one (not its internal viewport), and coordinates that reach it.
    assert "VerticalScrollable" in message
    assert "x=50 y=50" in message
    assert "key=" in message
    assert "scroll_into_view" in message
    assert not any(cell.presses for cell in cells)


def test_scroll_refuses_a_target_outside_any_scroll_region() -> None:
    app = _App(Column([_Cell("lonely")]))

    with pytest.raises(ValueError, match="not inside one"):
        scroll(app, key="lonely", dy=3.0)


def test_scroll_repeats_with_the_region_as_its_own_anchor() -> None:
    """The loop the row anchor broke: keep wheeling the region until at_end.

    The region's rect does not move as its content scrolls, so one target stays
    valid for the whole traversal -- which is the point of insisting on it.
    """
    app, scroller, _cells = _vertical()

    offsets = []
    for _ in range(10):
        result = scroll(app, key="feed", dy=3.0)
        offsets.append(result["offset"])
        if result["at_end"]:
            break

    assert offsets[0] == 60.0
    assert offsets[-1] == MAX_EXTENT
    assert scroller.scroll_offset == MAX_EXTENT
    # Strictly increasing until it clamps: every call landed on the region.
    assert offsets == sorted(offsets)


# --- scroll_into_view ------------------------------------------------------


def test_scroll_into_view_makes_an_off_screen_target_clickable() -> None:
    """The postcondition that matters: the following click succeeds."""
    app, scroller, cells = _vertical()

    result = scroll_into_view(app, key="row-9")

    assert result["scrolled_into_view"] == {"type": "_Cell", "key": "row-9"}
    assert result["already_visible"] is False
    # "nearest" brings the bottom edge in and no further.
    assert result["offset"] == MAX_EXTENT
    assert scroller.scroll_offset == MAX_EXTENT

    click(app, key="row-9")
    assert len(cells[9].presses) == 1


def test_scroll_into_view_leaves_an_already_visible_target_alone() -> None:
    app, scroller, _cells = _vertical()

    result = scroll_into_view(app, key="row-0")

    assert result["already_visible"] is True
    assert scroller.scroll_offset == 0.0


def test_scroll_into_view_scrolls_back_up_for_a_target_above_the_fold() -> None:
    app, scroller, cells = _vertical()
    scroller.scroll_to(MAX_EXTENT)

    result = scroll_into_view(app, key="row-1")

    # "nearest" brings the top edge in: row 1 starts at content y 40.
    assert scroller.scroll_offset == 40.0
    assert result["already_visible"] is False
    click(app, key="row-1")
    assert len(cells[1].presses) == 1


def test_scroll_into_view_alignment_places_the_target() -> None:
    app, scroller, _cells = _vertical()

    scroll_into_view(app, key="row-5", align="start")
    assert scroller.scroll_offset == 200.0

    scroll_into_view(app, key="row-5", align="end")
    assert scroller.scroll_offset == 140.0

    scroll_into_view(app, key="row-5", align="center")
    assert scroller.scroll_offset == 170.0


def test_scroll_into_view_works_horizontally() -> None:
    app, scroller, cells = _horizontal()

    scroll_into_view(app, key="col-9")

    assert scroller.scroll_offset == MAX_EXTENT
    click(app, key="col-9")
    assert len(cells[9].presses) == 1


def test_scroll_into_view_rejects_an_unknown_alignment() -> None:
    app, _scroller, _cells = _vertical()

    with pytest.raises(ValueError, match="align"):
        scroll_into_view(app, key="row-3", align="sideways")


def test_scroll_into_view_without_a_scrollable_ancestor_raises() -> None:
    """Reported, rather than passed off as a successful no-op."""
    cell = _Cell("lonely")
    app = _App(Column([cell]))

    with pytest.raises(ValueError, match="not inside a scrollable region"):
        scroll_into_view(app, key="lonely")


def test_scroll_into_view_needs_an_identifier() -> None:
    app, _scroller, _cells = _vertical()

    with pytest.raises(ValueError, match="'key' or a 'label'"):
        scroll_into_view(app)
