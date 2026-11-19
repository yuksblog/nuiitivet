"""A subtree nobody holds is freed by reference counting: no cycle waits for the collector."""

import gc
import weakref

import pytest

from typing import Callable

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.scrollable import VerticalScrollable
from nuiitivet.material.buttons import Button
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.selection_controls import Checkbox
from nuiitivet.material.text import Text
from nuiitivet.observable.value import State
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.testing import mount
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgeting.widget_builder import ScopeHandle, flush_scope_recompositions
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

    scroller._controller.scroll_to(400)  # a whole screen away: nothing of the old range is kept
    scroller.layout(200, 100)

    assert all(rows[item]() is None for item in (0, 1, 2, 3, 4)), "the rows that left the window are gone"
    assert all(rows[item]() is not None for item in (20, 21, 22, 23, 24)), "the rows in the window live"


class _Screen(ComposableWidget):
    def __init__(self, content: Callable[["_Screen"], Widget]) -> None:
        super().__init__()
        self.count = State(0)
        self._content = content

    def clicked(self) -> None:
        self.count.value += 1

    def build(self) -> Widget:
        return self._content(self)


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(lambda screen: Text("import"), id="text"),
        pytest.param(lambda screen: Button("Go", on_click=screen.clicked), id="button-method-handler"),
        pytest.param(lambda screen: Button("Go", on_click=lambda: screen.clicked()), id="button-lambda-handler"),
        pytest.param(lambda screen: Text(screen.count.map(lambda n: f"{n}")), id="text-derived-state"),
    ],
)
def test_a_removed_composable_is_freed_after_the_next_layout(
    collector_off, content: Callable[[_Screen], Widget]
) -> None:
    parent = Column(children=[])
    with mount(parent, leak_check="off") as host:
        host.layout(400, 300)
        screen = _Screen(content)
        parent.add_child(screen)
        host.settle()
        assert screen.built_child is not None
        ref = weakref.ref(screen)

        parent.remove_child(screen)
        host.layout(400, 301)  # the frame that follows drops the laid-out list's hold
        del screen
        assert ref() is None, "the scope callbacks bound to the composable left no cycle behind"


class _ScopedScreen(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.body_builds = 0
        self.handle: ScopeHandle | None = None

    def build(self) -> Widget:
        with self.scope("body") as handle:
            self.handle = handle
            return self.render_scope_with_handle(handle, self._build_body)

    def _build_body(self) -> Widget:
        self.body_builds += 1
        return Text(f"body {self.body_builds}")


def test_a_remounted_composable_still_recomposes_its_scope(collector_off) -> None:
    parent = Column(children=[])
    with mount(parent, leak_check="off") as host:
        host.layout(400, 300)
        screen = _ScopedScreen()
        parent.add_child(screen)
        host.settle()
        parent.remove_child(screen)
        host.layout(400, 301)

        parent.add_child(screen)
        host.settle()
        builds = screen.body_builds
        assert screen.handle is not None
        screen.handle.invalidate()
        flush_scope_recompositions()
        assert screen.body_builds == builds + 1
