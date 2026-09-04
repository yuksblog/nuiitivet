"""Tests for scroll in the interaction journal.

Built on real ``VerticalScrollable`` / ``HorizontalScrollable`` widgets driven
through the real pointer dispatch, for the same reason ``test_action_scroll.py``
is: what the recorder claims -- which region consumed the wheel, on which axis,
and where it ended up -- is decided by the scroll machinery, so a fake would only
assert the recorder against itself. ``_wheel`` reproduces the pyglet runner's
wiring: dispatch, then hand the *returned handler* to the recorder.
"""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet.dev.interaction import InteractionJournal, InteractionRecorder
from nuiitivet.input.codes import MOD_CTRL
from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.layout.scrollable import HorizontalScrollable, VerticalScrollable
from nuiitivet.runtime import app_events
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.scrolling import ScrollPhysics
from nuiitivet.widgeting.widget import Widget

ROW_SIZE = 40
ROW_COUNT = 10
VIEWPORT = 100
#: 10 rows of 40 in a 100px viewport -> 400 - 100.
MAX_EXTENT = float(ROW_COUNT * ROW_SIZE - VIEWPORT)
#: Pixels a region moves per wheel notch (``scroll_multiplier``'s default).
PX_PER_NOTCH = 20.0


class _Cell(Widget):
    """A hit-testable cell, so ``hit_test`` catches inside a region's content."""

    def __init__(self, key: str, *, width: int = VIEWPORT, height: int = ROW_SIZE) -> None:
        super().__init__(width=width, height=height, key=key)
        self._size = (width, height)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None):
        return self._size

    def on_pointer_event(self, event: PointerEvent) -> bool:
        return event.type is PointerEventType.PRESS


class _App:
    """A minimal app whose ``_dispatch_mouse_scroll`` is the real one."""

    def __init__(self, root: Widget, *, width: int = VIEWPORT, height: int = VIEWPORT) -> None:
        self.root = root
        self.width = width
        self.height = height
        self._pointer_capture_manager = PointerCaptureManager()
        self._pressed_target: Optional[Widget] = None
        self._last_hover_target: Optional[Widget] = None
        root.layout(width, height)

    def invalidate(self, immediate: bool = False) -> None:
        pass

    def request_focus(self, node: Any) -> None:
        pass

    def _dispatch_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> Any:
        return app_events.dispatch_mouse_scroll(self, x, y, scroll_x, scroll_y)


def _recorder() -> tuple[InteractionJournal, InteractionRecorder]:
    journal = InteractionJournal()
    return (journal, InteractionRecorder(journal))


def _wheel(
    app: _App,
    recorder: InteractionRecorder,
    *,
    x: int = 50,
    y: int = 50,
    dx: float = 0.0,
    dy: float = 0.0,
) -> Any:
    """Turn one wheel notch batch exactly as the pyglet backend does."""
    handler = app._dispatch_mouse_scroll(x, y, dx, dy)
    recorder.on_mouse_scroll(handler, dx, dy)
    return handler


def _vertical(key: Optional[str] = "feed") -> tuple[_App, VerticalScrollable]:
    scroller = VerticalScrollable(
        Column([_Cell(f"row-{i}") for i in range(ROW_COUNT)]), width=VIEWPORT, height=VIEWPORT
    )
    scroller.key = key
    return (_App(scroller), scroller)


def _horizontal(key: Optional[str] = "strip") -> tuple[_App, HorizontalScrollable]:
    cells: list[Widget] = [_Cell(f"col-{i}", width=ROW_SIZE, height=VIEWPORT) for i in range(ROW_COUNT)]
    scroller = HorizontalScrollable(Row(cells), width=VIEWPORT, height=VIEWPORT)
    scroller.key = key
    return (_App(scroller), scroller)


# --- what gets recorded at all ---------------------------------------------


def test_consumed_scroll_is_recorded_with_target_and_position() -> None:
    app, scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=5.0)

    (event,) = journal.recent()
    assert event.kind == "scroll"
    assert event.target == {"type": "VerticalScrollable", "key": "feed"}
    assert event.direction == "down"
    assert (event.dx, event.dy) == (0.0, 5.0)
    assert event.axis == "vertical"
    assert event.offset == 5.0 * PX_PER_NOTCH == scroller.scroll_offset
    assert event.max_extent == MAX_EXTENT
    assert event.at_start is False and event.at_end is False


def test_unconsumed_wheel_records_nothing() -> None:
    """A region that refuses to scroll leaves no trace -- nothing moved."""
    app, scroller = _vertical()
    scroller.physics = ScrollPhysics.NEVER
    journal, recorder = _recorder()

    assert _wheel(app, recorder, dy=5.0) is None
    assert journal.recent() == []


def test_wheel_on_empty_space_records_nothing() -> None:
    journal, recorder = _recorder()
    app = _App(_Cell("plain", height=VIEWPORT))

    assert _wheel(app, recorder, dy=3.0, x=500, y=500) is None  # outside the tree
    assert journal.recent() == []


def test_subnotch_jitter_is_dropped_by_the_regions_deadband() -> None:
    """Trackpad noise below the region's threshold moves nothing, so it is not logged."""
    app, scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=0.001)

    assert scroller.scroll_offset == 0.0
    assert journal.recent() == []


def test_zero_delta_records_nothing() -> None:
    app, _scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=0.0, dx=0.0)
    assert journal.recent() == []


# --- coalescing ------------------------------------------------------------


def test_continuous_scroll_is_one_event_that_accumulates() -> None:
    """A gesture arrives as dozens of events and leaves exactly one entry."""
    app, scroller = _vertical()
    journal, recorder = _recorder()

    for _ in range(12):
        _wheel(app, recorder, dy=1.0)

    (event,) = journal.recent()
    assert event.dy == 12.0
    # 12 notches * 20px = 240, clamped to the region's 300px extent.
    assert event.offset == scroller.scroll_offset == 240.0
    assert event.at_end is False


def test_coalesced_update_reissues_seq_and_keeps_started_at() -> None:
    """An ongoing gesture must read as new activity to a client polling ``seq``."""
    app, _scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=1.0)
    (first,) = journal.recent()
    _wheel(app, recorder, dy=1.0)
    (second,) = journal.recent()

    assert second.seq > first.seq
    assert second.started_at == first.started_at
    assert second.timestamp >= first.timestamp


def test_reversing_direction_starts_a_new_event() -> None:
    """Otherwise down-then-up would net to zero and read as "did not scroll"."""
    app, _scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=5.0)
    _wheel(app, recorder, dy=-5.0)

    down, up = journal.recent()
    assert (down.direction, down.dy) == ("down", 5.0)
    assert (up.direction, up.dy) == ("up", -5.0)
    assert up.offset == 0.0 and up.at_start is True


def test_intervening_click_or_key_or_text_starts_a_new_event() -> None:
    app, _scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=1.0)
    recorder.on_mouse_press(app, 50, 50)
    _wheel(app, recorder, dy=1.0)
    recorder.on_key_press("s", MOD_CTRL)
    _wheel(app, recorder, dy=1.0)
    recorder.on_text()
    _wheel(app, recorder, dy=1.0)

    assert [e.kind for e in journal.recent()] == [
        "scroll",
        "click",
        "scroll",
        "key",
        "scroll",
        "text",
        "scroll",
    ]
    assert all(e.dy == 1.0 for e in journal.recent() if e.kind == "scroll")


def test_text_marker_resets_after_a_scroll() -> None:
    """Scroll breaks the text run, so typing after it is marked again."""
    app, _scroller = _vertical()
    journal, recorder = _recorder()

    recorder.on_text()
    recorder.on_text()
    _wheel(app, recorder, dy=1.0)
    recorder.on_text()

    assert [e.kind for e in journal.recent()] == ["text", "scroll", "text"]


def test_scrolling_a_different_region_starts_a_new_event() -> None:
    outer = VerticalScrollable(
        Column(
            [
                *(_Cell(f"row-{i}") for i in range(3)),
                _nested_strip(),
                *(_Cell(f"row-{i}") for i in range(3, ROW_COUNT)),
            ]
        ),
        width=VIEWPORT,
        height=VIEWPORT,
    )
    outer.key = "feed"
    app = _App(outer)
    journal, recorder = _recorder()

    # y=50 is inside row-1, so the outer feed consumes it.
    _wheel(app, recorder, y=50, dy=1.0)
    # The nested strip sits at content y 120..220 -- bring it under the cursor.
    outer.scroll_to(140.0)
    _wheel(app, recorder, y=20, dy=1.0)

    feed, strip = journal.recent()
    assert feed.target == {"type": "VerticalScrollable", "key": "feed"}
    assert strip.target == {"type": "HorizontalScrollable", "key": "strip"}


def _nested_strip() -> HorizontalScrollable:
    cells: list[Widget] = [_Cell(f"col-{i}", width=ROW_SIZE, height=VIEWPORT) for i in range(ROW_COUNT)]
    strip = HorizontalScrollable(Row(cells), width=VIEWPORT, height=VIEWPORT)
    strip.key = "strip"
    return strip


def test_two_keyless_sibling_regions_do_not_merge() -> None:
    """Both resolve to the same coarse ``target``, but they are different regions.

    Merging would sum two regions' deltas into one entry whose ``offset``
    describes only the second -- an entry that is true of neither. Found on a real
    app whose scroll regions carry no ``key``.
    """
    top = VerticalScrollable(
        Column([_Cell(f"a-{i}") for i in range(ROW_COUNT)]), width=VIEWPORT, height=50
    )
    bottom = VerticalScrollable(
        Column([_Cell(f"b-{i}") for i in range(ROW_COUNT)]), width=VIEWPORT, height=50
    )
    app = _App(Column([top, bottom]))
    journal, recorder = _recorder()

    _wheel(app, recorder, y=25, dy=1.0)  # inside `top`
    _wheel(app, recorder, y=75, dy=1.0)  # inside `bottom`, same direction

    first, second = journal.recent()
    assert first.target == second.target == {"type": "VerticalScrollable"}
    assert first.dy == second.dy == 1.0
    assert top.scroll_offset == bottom.scroll_offset == PX_PER_NOTCH


def test_returning_to_a_region_after_another_starts_a_third_event() -> None:
    top = VerticalScrollable(
        Column([_Cell(f"a-{i}") for i in range(ROW_COUNT)]), width=VIEWPORT, height=50
    )
    bottom = VerticalScrollable(
        Column([_Cell(f"b-{i}") for i in range(ROW_COUNT)]), width=VIEWPORT, height=50
    )
    app = _App(Column([top, bottom]))
    journal, recorder = _recorder()

    _wheel(app, recorder, y=25, dy=1.0)
    _wheel(app, recorder, y=75, dy=1.0)
    _wheel(app, recorder, y=25, dy=1.0)

    assert len(journal.recent()) == 3
    assert all(e.dy == 1.0 for e in journal.recent())


def test_same_region_still_coalesces_across_repeated_hits() -> None:
    """The identity check must not defeat coalescing for the ordinary case."""
    app, _scroller = _vertical()
    journal, recorder = _recorder()

    for _ in range(5):
        _wheel(app, recorder, dy=1.0)

    (event,) = journal.recent()
    assert event.dy == 5.0


def test_nested_region_records_the_one_that_consumed_it() -> None:
    """The inner strip takes the wheel, so the outer feed is never named."""
    strip = _nested_strip()
    outer = VerticalScrollable(Column([strip]), width=VIEWPORT, height=VIEWPORT)
    outer.key = "feed"
    app = _App(outer)
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=2.0)

    (event,) = journal.recent()
    assert event.target == {"type": "HorizontalScrollable", "key": "strip"}
    assert outer.scroll_offset == 0.0
    assert strip.scroll_offset == 2.0 * PX_PER_NOTCH


# --- axis and direction follow the consuming region ------------------------


def test_horizontal_region_driven_by_a_vertical_wheel() -> None:
    """The region's axis names the gesture, not the wheel's."""
    app, strip = _horizontal()
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=3.0)  # an ordinary vertical wheel

    (event,) = journal.recent()
    assert event.axis == "horizontal"
    assert event.direction == "right"
    assert (event.dx, event.dy) == (3.0, 0.0)
    assert event.offset == strip.scroll_offset == 3.0 * PX_PER_NOTCH


def test_horizontal_region_prefers_its_own_axis_delta() -> None:
    app, _strip = _horizontal()
    journal, recorder = _recorder()

    _wheel(app, recorder, dx=-2.0, dy=7.0)

    (event,) = journal.recent()
    assert (event.direction, event.dx, event.dy) == ("left", -2.0, 0.0)


def test_vertical_region_ignores_the_horizontal_delta() -> None:
    app, _scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, dx=9.0, dy=1.0)

    (event,) = journal.recent()
    assert (event.direction, event.dx, event.dy) == ("down", 0.0, 1.0)


# --- position over delta ---------------------------------------------------


def test_scrolling_past_the_end_keeps_one_event_and_reports_at_end() -> None:
    """Pushing at the bottom is still one gesture; ``at_end`` is the stop signal."""
    app, scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=20.0)  # 400px of notches into a 300px extent
    (event,) = journal.recent()
    assert event.offset == MAX_EXTENT and event.at_end is True

    _wheel(app, recorder, dy=5.0)
    (event,) = journal.recent()
    assert event.dy == 25.0
    assert event.offset == MAX_EXTENT and event.at_end is True
    assert scroller.scroll_offset == MAX_EXTENT


# --- privacy ---------------------------------------------------------------


def test_no_coordinate_reaches_the_journal() -> None:
    app, _scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, x=37, y=61, dy=1.0)

    payload = journal.recent()[0].to_dict()
    assert payload["target"] == {"type": "VerticalScrollable", "key": "feed"}
    assert "x" not in payload and "y" not in payload


def test_unidentified_region_still_records_a_coarse_type() -> None:
    app, _scroller = _vertical(key=None)
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=1.0)

    assert journal.recent()[0].target == {"type": "VerticalScrollable"}


# --- serialization ---------------------------------------------------------


def test_to_dict_shape() -> None:
    app, _scroller = _vertical()
    journal, recorder = _recorder()

    _wheel(app, recorder, dy=2.0)
    event = journal.recent()[0]

    assert event.to_dict() == {
        "seq": event.seq,
        "timestamp": event.timestamp,
        "started_at": event.started_at,
        "kind": "scroll",
        "target": {"type": "VerticalScrollable", "key": "feed"},
        "direction": "down",
        "dy": 2.0,
        "axis": "vertical",
        "offset": 40.0,
        "max_extent": MAX_EXTENT,
        "at_start": False,
        "at_end": False,
    }
    # The unused axis is omitted, the way ``modifiers`` is on a bare key.
    assert "dx" not in event.to_dict()


def test_other_kinds_keep_their_shape() -> None:
    """The new fields never leak into a click / key / text entry."""
    journal = InteractionJournal()
    click = journal.record_click({"type": "Button"})
    key = journal.record_key("enter")
    text = journal.record_text()

    assert click.to_dict() == {
        "seq": click.seq,
        "timestamp": click.timestamp,
        "kind": "click",
        "target": {"type": "Button"},
    }
    assert key.to_dict() == {"seq": key.seq, "timestamp": key.timestamp, "kind": "key", "key": "enter"}
    assert text.to_dict() == {"seq": text.seq, "timestamp": text.timestamp, "kind": "text"}


# --- journal-level coalescing (independent of the widget tree) -------------


def test_record_scroll_replaces_only_the_tail() -> None:
    journal = InteractionJournal()
    journal.record_click({"type": "Button"})
    journal.record_scroll({"key": "feed"}, direction="down", dy=1.0)
    journal.record_scroll({"key": "feed"}, direction="down", dy=1.0)

    events = journal.recent()
    assert len(events) == 2
    assert events[0].kind == "click"
    assert events[1].dy == 2.0


def test_record_scroll_ignores_unknown_metric_keys() -> None:
    journal = InteractionJournal()
    event = journal.record_scroll(
        {"key": "feed"}, direction="down", dy=1.0, metrics={"axis": "vertical", "bogus": 1}
    )
    assert event.axis == "vertical"
    assert "bogus" not in event.to_dict()


def test_record_scroll_respects_capacity() -> None:
    journal = InteractionJournal(capacity=2)
    journal.record_text()
    journal.record_text()
    journal.record_scroll({"key": "feed"}, direction="down", dy=1.0)
    journal.record_scroll({"key": "feed"}, direction="down", dy=1.0)

    events = journal.recent()
    assert [e.kind for e in events] == ["text", "scroll"]
    assert events[-1].dy == 2.0
