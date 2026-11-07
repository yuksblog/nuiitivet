"""A subtree nobody holds is freed by reference counting: no cycle waits for the collector."""

import gc
import weakref

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.scrollable import VerticalScrollable
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.selection_controls import Checkbox
from nuiitivet.material.text import Text
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.widgets.interaction import FocusNode, FocusSource, PointerInputNode


class _App:
    def __init__(self) -> None:
        self._pointer_capture_manager = PointerCaptureManager()

    def invalidate(self, immediate: bool = False) -> None:
        del immediate


@pytest.fixture
def collector_off():
    """Only reference counting frees anything during the test."""
    gc.collect()
    gc.disable()
    yield
    gc.enable()
    gc.collect()


def test_a_child_does_not_keep_its_parent_alive(collector_off):
    child = Text("leaf")
    parent = Container(child)
    ref = weakref.ref(parent)
    assert child.parent is parent

    del parent
    assert ref() is None
    assert child.parent is None


def test_a_dropped_subtree_is_freed_at_once(collector_off):
    row = Container(Column([Text("a"), Text("b")]))
    holder = Column([row])
    ref = weakref.ref(row)

    holder.remove_child(row)
    del row
    assert ref() is None, "parent links and store owners left no cycle behind"


def test_a_dropped_interactive_widget_is_freed_at_once(collector_off):
    box = Checkbox()
    holder = Column([box])
    holder.mount(_App())
    holder.layout(200, 100)
    ref = weakref.ref(box)

    holder.remove_child(box)
    holder.layout(200, 100)  # the frame that follows drops the laid-out list's hold
    del box
    assert ref() is None, "the nodes' callbacks bound to the widget left no cycle behind"


def test_a_node_callback_still_runs_while_its_widget_lives(collector_off):
    calls = []

    class _Widget(InteractiveWidget):
        def __init__(self) -> None:
            super().__init__()
            self.pointer = PointerInputNode(owner=self)
            self.pointer.enable_click(on_click=self._clicked)
            self.focus = FocusNode(on_focus_change=self._focus_changed)
            self.focus.attach(self)

        def _clicked(self) -> None:
            calls.append("click")

        def _focus_changed(self, focused: bool, source: FocusSource) -> None:
            calls.append(("focus", focused, source))

    widget = _Widget()
    widget.pointer._click_callbacks[0]()
    assert widget.focus._on_focus_change is not None
    widget.focus._on_focus_change(True, FocusSource.KEYBOARD)
    assert calls == ["click", ("focus", True, FocusSource.KEYBOARD)]

    ref = weakref.ref(widget)
    del widget
    assert ref() is None


def test_rows_a_lazy_column_dropped_are_freed_at_once(collector_off):
    rows = {}

    def builder(item, index):
        row = Container(Column([Checkbox(), Text(str(item))]), height=20)
        rows[item] = weakref.ref(row)
        return row

    column = Column.lazy(list(range(200)), builder, item_height=20)
    scroller = VerticalScrollable(column, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)
    assert sorted(rows) == [0, 1, 2, 3, 4]

    scroller._controller.scroll_to(100)
    scroller.layout(200, 100)

    assert all(rows[item]() is None for item in (0, 1, 2, 3, 4)), "the rows that left the window are gone"
    assert all(rows[item]() is not None for item in (5, 6, 7, 8, 9)), "the rows in the window live"
