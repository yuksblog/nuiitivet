"""``AppHarness``: a whole screen, driven in-process, with no window."""

from __future__ import annotations

import threading
import time
from typing import Optional

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.layout.for_each import ForEach
from nuiitivet.layout.scrollable import VerticalScrollable
from nuiitivet.material.text import Text
from nuiitivet.material.text_fields import TextField
from nuiitivet.modifiers.size_changed import on_size_changed
from nuiitivet.observable import Observable
from nuiitivet.observable.runtime import get_clock, set_clock
from nuiitivet.testing import (
    ActionNotHandledError,
    AppHarness,
    HarnessClock,
    StaleNodeError,
    TargetNotFoundError,
)
from nuiitivet.testing._support import _has_immediate_work
from nuiitivet.widgeting.widget import ComposableWidget, Widget


ROW_HEIGHT = 40
VIEWPORT = 100


def _text(value: object, key: str) -> Widget:
    """A keyed Text."""
    return Text(value, key=key)  # type: ignore[arg-type]


class _Counter(ComposableWidget):
    """A screen with state, a keyed readout and a keyed button."""

    def __init__(self) -> None:
        super().__init__()
        self.count = Observable(0)

    def build(self) -> Widget:
        from nuiitivet.material.buttons import Button

        return Column(
            children=[
                _text(self.count.map(lambda c: f"Count: {c}"), "count"),
                Button("increment", on_click=self._increment, key="increment"),
            ]
        )

    def _increment(self) -> None:
        self.count.value = self.count.value + 1


class _Cell(Widget):
    """A fixed-size hit-testable cell, so a region's content is reachable."""

    def __init__(self, key: str, *, height: int = ROW_HEIGHT) -> None:
        super().__init__(width=VIEWPORT, height=height, key=key)
        self._size = (VIEWPORT, height)

    def preferred_size(
        self, max_width: Optional[int] = None, max_height: Optional[int] = None
    ):
        return self._size


# -- the flagship ----------------------------------------------------------


def test_click_drives_state_and_tree(nuiitivet_app) -> None:
    screen = _Counter()
    app = nuiitivet_app(screen, size=(800, 600))

    app.click(key="increment")

    assert screen.count.value == 1
    assert app.get(key="count").text == "Count: 1"


def test_context_manager_closes_and_unmounts() -> None:
    screen = _Counter()
    with AppHarness(screen, size=(800, 600)) as app:
        assert app.get(key="count").text == "Count: 0"
    assert screen._unmounted is True


def test_size_is_required() -> None:
    with pytest.raises(TypeError):
        AppHarness(_Counter())  # type: ignore[call-arg]


def test_size_is_what_the_tree_is_laid_out_at() -> None:
    with AppHarness(_Counter(), size=(640, 480)) as app:
        assert app.size == (640, 480)


# -- queries ---------------------------------------------------------------


def test_get_lists_available_identities_on_a_miss() -> None:
    with AppHarness(_Counter(), size=(800, 600)) as app:
        with pytest.raises(TargetNotFoundError) as excinfo:
            app.get(key="nope")
        assert "key='count'" in str(excinfo.value)


def test_get_refuses_two_matches_and_names_the_divergence() -> None:
    def screen() -> Widget:
        return Column(children=[_text("Delete", "row-1"), _text("Delete", "row-2")])

    with AppHarness(screen, size=(800, 600)) as app:
        with pytest.raises(TargetNotFoundError) as excinfo:
            app.get(label="Delete")
        message = str(excinfo.value)
        assert "matched 2 widgets" in message
        assert "dev bridge would have taken the first" in message


# -- Node staleness --------------------------------------------------------


def _list_screen(rows: Observable) -> Widget:
    """A list whose rows are genuinely rebuilt when the source changes."""
    return Column(children=[ForEach(rows, lambda item, _index: _text(item, item))])


def test_node_from_before_a_rebuild_raises(nuiitivet_app) -> None:
    rows = Observable(["alpha", "beta"])
    app = nuiitivet_app(lambda: _list_screen(rows), size=(800, 600))
    node = app.get(key="alpha")
    assert node.text == "alpha"

    rows.value = ["beta"]
    app.settle()

    with pytest.raises(StaleNodeError, match="re-query"):
        _ = node.text
    # Re-querying is the habit the error is teaching.
    assert app.query(key="alpha") is None
    assert app.get(key="beta").text == "beta"


def test_stale_message_names_the_action_that_invalidated_it(nuiitivet_app) -> None:
    rows = Observable(["alpha", "beta"])
    app = nuiitivet_app(lambda: _list_screen(rows), size=(800, 600))
    node = app.get(key="alpha")

    rows.value = ["beta"]
    app.resize(400, 300)

    with pytest.raises(StaleNodeError, match=r"resize\(400, 300\)"):
        _ = node.text


# -- the verbs -------------------------------------------------------------


def test_type_with_nothing_focused_raises(nuiitivet_app) -> None:
    app = nuiitivet_app(_Counter(), size=(800, 600))

    with pytest.raises(ActionNotHandledError, match="click the field first"):
        app.type("hello")


def test_type_can_assert_the_negative_deliberately(nuiitivet_app) -> None:
    app = nuiitivet_app(_Counter(), size=(800, 600))

    result = app.type("hello", require_handled=False)

    assert result["handled"] is False


def test_type_focuses_its_target_first(nuiitivet_app) -> None:
    value = Observable("")

    def screen() -> Widget:
        return Column(children=[TextField(value, key="field")])

    app = nuiitivet_app(screen, size=(800, 600))
    app.type("hi", key="field")

    assert value.value == "hi"


def test_key_with_nothing_bound_raises(nuiitivet_app) -> None:
    app = nuiitivet_app(_Counter(), size=(800, 600))

    with pytest.raises(ActionNotHandledError):
        app.key("f7")


def test_resize_reflows_and_runs_size_callbacks(nuiitivet_app) -> None:
    seen: list[tuple[int, int]] = []

    def screen() -> Widget:
        return Column(
            children=[
                Column(width="wt", height="wt").modifier(
                    on_size_changed(lambda s: seen.append((s.width, s.height)))
                )
            ]
        )

    app = nuiitivet_app(screen, size=(800, 600))
    seen.clear()

    app.resize(400, 300)

    assert seen and seen[-1] == (400, 300)


# -- scrolling and reachability -------------------------------------------


def _scroll_screen() -> Widget:
    rows = [_Cell(f"row-{i}") for i in range(10)]
    return VerticalScrollable(
        Column(children=rows),
        height=VIEWPORT,
        key="list",
    )


def test_scroll_into_view_flips_is_reachable(nuiitivet_app) -> None:
    app = nuiitivet_app(_scroll_screen, size=(VIEWPORT, VIEWPORT))

    assert app.get(key="row-9").is_reachable is False

    app.scroll_into_view(key="row-9")

    assert app.get(key="row-9").is_reachable is True


def test_scroll_refuses_a_row_and_names_the_region(nuiitivet_app) -> None:
    app = nuiitivet_app(_scroll_screen, size=(VIEWPORT, VIEWPORT))

    with pytest.raises(ValueError, match="scroll_into_view"):
        app.scroll(key="row-1", dy=1)


def test_scroll_moves_the_region(nuiitivet_app) -> None:
    app = nuiitivet_app(_scroll_screen, size=(VIEWPORT, VIEWPORT))

    result = app.scroll(key="list", dy=2)

    assert result.get("offset", 0) > 0


# -- settle: what is pumped and what is not -------------------------------


def test_settle_applies_a_write_from_a_worker_thread(
    nuiitivet_app,
) -> None:
    label = Observable("before")

    def screen() -> Widget:
        return Column(children=[_text(label, "greeting")])

    app = nuiitivet_app(screen, size=(800, 600))

    worker = threading.Thread(target=lambda: setattr(label, "value", "after"))
    worker.start()
    worker.join()

    # The write is queued on the clock, not applied: without the pump the test
    # would read "before" and pass on it.
    assert app.get(key="greeting").text == "before"

    app.settle()

    assert app.get(key="greeting").text == "after"


def test_settle_converges_while_a_worker_thread_keeps_writing(nuiitivet_app) -> None:
    """A live background thread is not a tree that will not stop moving.

    Every cross-thread write arms a zero-delay callback, so a worker writing in
    a loop keeps zero-delay work pending for as long as it runs. Counting that
    towards the convergence bound would turn any test with a background thread
    into ``LayoutNotConvergedError``.
    """
    label = Observable("before")

    def screen() -> Widget:
        return Column(children=[_text(label, "greeting")])

    app = nuiitivet_app(screen, size=(800, 600))

    stop = threading.Event()

    def worker() -> None:
        i = 0
        while not stop.is_set():
            i += 1
            label.value = f"tick-{i}"

    thread = threading.Thread(target=worker)
    thread.start()
    try:
        for _ in range(5):
            app.settle()  # must not raise
    finally:
        stop.set()
        thread.join()

    app.settle()
    assert app.get(key="greeting").text.startswith("tick-")


def test_immediate_work_counts_only_what_this_thread_armed() -> None:
    """The convergence question is "has the tree stopped", not "is the app idle".

    Zero-delay work armed here still counts -- that is the self-rescheduling
    the settle bound exists to catch. Identical work armed by another thread
    does not.
    """
    clock = HarnessClock()

    clock.schedule_once(lambda dt: None, 0)
    assert _has_immediate_work(clock) is True

    clock.cancel_all()
    thread = threading.Thread(target=lambda: clock.schedule_once(lambda dt: None, 0))
    thread.start()
    thread.join()

    assert clock.pending(), "the worker's callback is still armed and will be pumped"
    assert _has_immediate_work(clock) is False


def test_settle_leaves_a_debounce_armed(nuiitivet_app) -> None:
    source = Observable("")
    debounced = source.debounce(0.3)
    seen: list[str] = []
    debounced.subscribe(seen.append)

    app = nuiitivet_app(_Counter(), size=(800, 600))

    source.value = "hel"
    app.settle()

    # Delayed work stays frozen: making it fire requires real time to pass,
    # which is what the clock's own pump() is for.
    assert seen == []
    assert any(p.delay > 0 for p in app.clock.pending())


def test_a_delayed_effect_fires_once_time_really_passes(nuiitivet_app) -> None:
    source = Observable("")
    debounced = source.debounce(0.01)
    seen: list[str] = []
    debounced.subscribe(seen.append)

    app = nuiitivet_app(_Counter(), size=(800, 600))
    source.value = "hel"
    time.sleep(0.02)
    app.clock.pump()

    assert seen == ["hel"]


# -- clock resolution ------------------------------------------------------


def test_harness_installs_its_own_clock_when_none_is_installed() -> None:
    """The `with AppHarness(...)` outside pytest case, in miniature."""

    class _NotAHarnessClock:
        def schedule_once(self, fn, delay):  # pragma: no cover - never pumped
            pass

        def schedule_interval(self, fn, interval):  # pragma: no cover
            pass

        def unschedule(self, fn):  # pragma: no cover
            pass

    outsider = _NotAHarnessClock()
    previous = get_clock()
    set_clock(outsider)
    try:
        with AppHarness(_Counter(), size=(800, 600)) as app:
            assert isinstance(get_clock(), HarnessClock)
            app.click(key="increment")
        # Restored, so the harness leaves the process as it found it.
        assert get_clock() is outsider
    finally:
        set_clock(previous)


@pytest.mark.nuiitivet(clock="real")
def test_harness_refuses_a_test_that_opted_out_of_the_harness_clock() -> None:
    from nuiitivet.testing import _support

    with pytest.raises(RuntimeError, match='clock="real"'):
        AppHarness(_Counter(), size=(800, 600))
    # Refused before anything was built, so nothing is left registered to warn
    # about at teardown.
    assert _support.open_harnesses() == []


# -- teardown --------------------------------------------------------------


def test_teardown_hooks_run_on_close() -> None:
    ran: list[str] = []
    with AppHarness(_Counter(), size=(800, 600)) as app:
        app.add_teardown_hook(lambda: ran.append("first"))
        app.add_teardown_hook(lambda: ran.append("second"))
    assert ran == ["first", "second"]


def test_teardown_hooks_run_when_the_test_body_raised() -> None:
    ran: list[str] = []
    with pytest.raises(ValueError):
        with AppHarness(_Counter(), size=(800, 600)) as app:
            app.add_teardown_hook(lambda: ran.append("ran"))
            raise ValueError("the test failed")
    assert ran == ["ran"]


def test_a_closed_harness_refuses_further_use() -> None:
    app = AppHarness(_Counter(), size=(800, 600))
    app.close()
    with pytest.raises(RuntimeError, match="is closed"):
        app.click(key="increment")


def test_a_construction_that_failed_leaves_nothing_registered() -> None:
    """A half-built harness must not be reported as one the test forgot."""
    from nuiitivet.testing import _support

    before = len(_support.open_harnesses())
    with pytest.raises(ValueError):
        AppHarness(_Counter(), size=("wide", "tall"))  # type: ignore[arg-type]
    assert len(_support.open_harnesses()) == before
