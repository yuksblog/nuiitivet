"""``idle()`` and ``wait_for()``: awaiting async work from a test.

The two regression tests at the top pin the design decision the rest depends on
-- ``idle()`` returns when the loop is **quiescent**, not when every task it
started has finished. Both cases below hang under the completion-based version,
and both are ordinary apps.
"""

from __future__ import annotations

import asyncio
import warnings

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.material.buttons import Button
from nuiitivet.material.text import Text
from nuiitivet.modifiers.keyed import keyed
from nuiitivet.observable import Observable
from nuiitivet.observable import runtime
from nuiitivet.testing import (
    AppHarness,
    IdleTimeoutError,
    UnschedulableAsyncWork,
    WaitTimeoutError,
)
from nuiitivet.testing.plugin import NuiitivetPendingWorkWarning
from nuiitivet.widgeting.widget import ComposableWidget, Widget


SIZE = (400, 300)


def _text(value: object, key: str) -> Widget:
    return Text(value).modifier(keyed(key))  # type: ignore[arg-type]


class _Loader(ComposableWidget):
    """A screen whose button runs an async handler."""

    def __init__(self, work: object) -> None:
        super().__init__()
        self.status = Observable("idle")
        self._work = work

    def build(self) -> Widget:
        return Column(
            children=[
                _text(self.status, "status"),
                Button("load", on_click=self._load).modifier(keyed("load")),
            ]
        )

    async def _load(self) -> None:
        self.status.value = "loading"
        await self._work()  # type: ignore[operator]
        self.status.value = "loaded"


# -- the two quiescence regressions ----------------------------------------


async def test_idle_returns_while_a_handler_is_parked(nuiitivet_app) -> None:
    """A handler awaiting an answer is an app at rest, not work in progress.

    Regression: terminating ``idle()`` on "every registered task finished"
    raises here instead, because the handler cannot finish until the test
    answers -- which makes every dialog test unwritable.
    """
    answered: "asyncio.Future[str]" = asyncio.get_running_loop().create_future()

    screen = _Loader(lambda: answered)
    app = nuiitivet_app(screen, size=SIZE)

    app.click(key="load")
    await app.idle()  # must return, with the handler still parked

    assert screen.status.value == "loading"
    assert app.get(key="status").text == "loading"

    answered.set_result("ok")
    await app.idle()
    assert screen.status.value == "loaded"


async def test_idle_returns_while_an_animation_runs(nuiitivet_app) -> None:
    """A repeating timer is a timer that never converges, so it is not progress.

    Regression: counting clock firings as progress makes ``idle()`` run to its
    timeout whenever anything on screen animates. The zero-period interval is
    the deterministic half -- ``HarnessClock`` fires those once per pump, so a
    firing-based ``idle()`` never sees a quiet round at all.
    """
    ticks = 0

    def _tick(_dt: float) -> None:
        nonlocal ticks
        ticks += 1

    runtime.get_clock().schedule_interval(_tick, 0.0)
    try:
        app = nuiitivet_app(_Loader(_never), size=SIZE)
        await app.idle(timeout=0.5)
        await app.idle(timeout=0.5)
    finally:
        runtime.get_clock().unschedule(_tick)

    assert ticks > 0, "the interval should have been pumped, just not counted"


async def _never() -> None:  # pragma: no cover - awaited but never resolved
    await asyncio.Event().wait()


# -- idle() ----------------------------------------------------------------


async def test_idle_runs_an_async_handler_to_completion(nuiitivet_app) -> None:
    async def _work() -> None:
        await asyncio.sleep(0)

    screen = _Loader(_work)
    app = nuiitivet_app(screen, size=SIZE)

    app.click(key="load")
    await app.idle()

    assert screen.status.value == "loaded"
    assert app.get(key="status").text == "loaded"


async def test_idle_reraises_a_handler_exception(nuiitivet_app) -> None:
    """Framework containment must not make a broken handler read as a good one."""

    async def _work() -> None:
        raise ValueError("handler blew up")

    app = nuiitivet_app(_Loader(_work), size=SIZE)
    app.click(key="load")

    with pytest.raises(ValueError, match="handler blew up"):
        await app.idle()


async def test_close_reraises_a_handler_exception_nobody_waited_for() -> None:
    """The last chance to notice: a failure after the test's final wait."""

    async def _work() -> None:
        raise ValueError("late failure")

    app = AppHarness(_Loader(_work), size=SIZE)
    app.click(key="load")
    # Run the handler to completion *without* going through idle(), so the
    # failure is recorded and nothing has surfaced it yet.
    await asyncio.gather(*app._tasks.in_flight(), return_exceptions=True)

    with pytest.raises(ValueError, match="late failure"):
        app.close()


@pytest.mark.filterwarnings("ignore::nuiitivet.testing.plugin.NuiitivetPendingWorkWarning")
async def test_idle_times_out_on_work_that_never_stops(nuiitivet_app) -> None:
    app = nuiitivet_app(_Loader(_never), size=SIZE)

    async def _spawn_forever() -> None:
        from nuiitivet.widgeting.callbacks import spawn_task

        spawn_task(_spawn_forever(), owner_name="test.spawn_forever")

    from nuiitivet.widgeting.callbacks import spawn_task

    spawn_task(_spawn_forever(), owner_name="test.spawn_forever")

    with pytest.raises(IdleTimeoutError) as excinfo:
        await app.idle(timeout=0.05)
    assert "asyncio" in str(excinfo.value)


async def test_idle_awaits_a_navigator_pop(nuiitivet_app) -> None:
    """``Navigator.pop()`` spawns its own task; ``idle()`` covers it."""
    from nuiitivet.navigation.navigator import Navigator
    from nuiitivet.navigation.route import Route

    nav = Navigator(Route(builder=lambda: _text("first", "first")))
    app = nuiitivet_app(nav, size=SIZE)
    nav.push(_text("second", "second"))
    await app.idle()
    assert app.query(key="second") is not None

    nav.pop()
    await app.idle()

    assert nav.can_pop() is False


# -- wait_for --------------------------------------------------------------


async def test_wait_for_a_tree_condition(nuiitivet_app) -> None:
    async def _work() -> None:
        await asyncio.sleep(0.02)

    screen = _Loader(_work)
    app = nuiitivet_app(screen, size=SIZE)

    app.click(key="load")
    await app.wait_for(key="status", text="loaded")

    assert screen.status.value == "loaded"


async def test_wait_for_absence(nuiitivet_app) -> None:
    """Waiting a spinner *out* is at least as common as waiting a result in."""
    from nuiitivet.layout.for_each import ForEach

    rows = Observable(["spinner"])
    app = nuiitivet_app(
        lambda: Column(children=[ForEach(rows, lambda item, _i: _text(item, item))]),
        size=SIZE,
    )
    assert app.query(key="spinner") is not None

    runtime.get_clock().schedule_once(lambda _dt: rows.set([]), 0.02)
    await app.wait_for(key="spinner", present=False)

    assert app.query(key="spinner") is None


async def test_wait_for_a_predicate(nuiitivet_app) -> None:
    """The tree vocabulary cannot say "this Observable changed"; a callable can."""

    async def _work() -> None:
        await asyncio.sleep(0.02)

    screen = _Loader(_work)
    app = nuiitivet_app(screen, size=SIZE)

    app.click(key="load")
    await app.wait_for(lambda: screen.status.value == "loaded")


async def test_wait_for_fires_a_debounce(nuiitivet_app) -> None:
    """The poll pumps the clock, so a delayed callback actually comes due."""
    fired = Observable(False)
    runtime.get_clock().schedule_once(lambda _dt: fired.set(True), 0.02)

    app = nuiitivet_app(_text("x", "x"), size=SIZE)
    await app.wait_for(lambda: fired.value)

    assert fired.value is True


async def test_wait_for_timeout_names_both_queues(nuiitivet_app) -> None:
    app = nuiitivet_app(_Loader(_never), size=SIZE)
    app.click(key="load")

    with pytest.raises(WaitTimeoutError) as excinfo:
        await app.wait_for(key="nothing-like-this", timeout=0.05)

    message = str(excinfo.value)
    assert "runtime.clock" in message
    assert "asyncio" in message
    assert "key='nothing-like-this'" in message


async def test_wait_for_refuses_a_predicate_and_a_target(nuiitivet_app) -> None:
    app = nuiitivet_app(_text("x", "x"), size=SIZE)
    with pytest.raises(TypeError, match="not both"):
        await app.wait_for(lambda: True, key="x")


async def test_wait_for_refuses_nothing_to_wait_for(nuiitivet_app) -> None:
    app = nuiitivet_app(_text("x", "x"), size=SIZE)
    with pytest.raises(TypeError, match="needs something to wait for"):
        await app.wait_for()


async def test_wait_for_honours_the_suite_default(nuiitivet_app) -> None:
    from nuiitivet.testing import _support

    _support._set_wait_timeout(0.05)
    try:
        app = nuiitivet_app(_text("x", "x"), size=SIZE)
        with pytest.raises(WaitTimeoutError, match="after 0.05s"):
            await app.wait_for(key="absent")
    finally:
        _support._set_wait_timeout(None)


# -- the no-loop path ------------------------------------------------------


def test_async_handler_without_a_loop_raises_under_the_harness(nuiitivet_app) -> None:
    """A synchronous test must not silently skip an async handler."""

    async def _work() -> None:  # pragma: no cover - never scheduled
        raise AssertionError("must not run")

    app = nuiitivet_app(_Loader(_work), size=SIZE)

    with pytest.raises(UnschedulableAsyncWork, match="async def"):
        app.click(key="load")


def test_unschedulable_handler_leaves_no_unawaited_coroutine(recwarn) -> None:
    """The dropped coroutine is closed, so Python blames nobody."""
    from nuiitivet.widgeting.callbacks import invoke_event_handler

    ran = False

    async def _handler() -> None:  # pragma: no cover - never scheduled
        nonlocal ran
        ran = True

    warnings.simplefilter("always")
    assert (
        invoke_event_handler(
            _handler, error_key="test", error_msg="test handler", owner_name="test"
        )
        is None
    )

    assert ran is False
    assert not [w for w in recwarn.list if issubclass(w.category, RuntimeWarning)]


def test_navigator_pop_without_a_loop_does_not_crash() -> None:
    """It used to raise RuntimeError from asyncio.create_task."""
    from nuiitivet.navigation.navigator import Navigator
    from nuiitivet.navigation.route import Route

    nav = Navigator(Route(builder=lambda: _text("first", "first")))
    nav.push(_text("second", "second"))

    nav.pop()  # no loop, no harness observing: logged and dropped

    assert nav.can_pop() is True


# -- the unobserved-task report --------------------------------------------


@pytest.mark.filterwarnings("ignore::nuiitivet.testing.plugin.NuiitivetPendingWorkWarning")
async def test_forgetting_to_await_warns(nuiitivet_app) -> None:
    app = nuiitivet_app(_Loader(_never), size=SIZE)
    app.click(key="load")
    # deliberately no `await app.idle()`

    from nuiitivet.testing import plugin

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        plugin._warn_unobserved_tasks()

    assert [w for w in caught if issubclass(w.category, NuiitivetPendingWorkWarning)]


async def test_a_watched_parked_task_is_not_reported(nuiitivet_app) -> None:
    """A test that asserts a dialog is open must not be scolded for it."""
    app = nuiitivet_app(_Loader(_never), size=SIZE)
    app.click(key="load")
    await app.idle()

    from nuiitivet.testing import plugin

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        plugin._warn_unobserved_tasks()

    assert not [w for w in caught if issubclass(w.category, NuiitivetPendingWorkWarning)]


# -- two harnesses in one test ---------------------------------------------


async def test_two_harnesses_each_observe(nuiitivet_app) -> None:
    """`nuiitivet_app` is a factory; a second harness must not be refused."""

    async def _work() -> None:
        await asyncio.sleep(0)

    first_screen = _Loader(_work)
    second_screen = _Loader(_work)
    first = nuiitivet_app(first_screen, size=SIZE)
    second = nuiitivet_app(second_screen, size=SIZE)

    first.click(key="load")
    second.click(key="load")
    await first.idle()

    assert first_screen.status.value == "loaded"
    assert second_screen.status.value == "loaded"


# -- close() ---------------------------------------------------------------


async def test_close_stops_observing(nuiitivet_app) -> None:
    from nuiitivet.widgeting import callbacks

    app = nuiitivet_app(_text("x", "x"), size=SIZE)
    assert callbacks._task_observers

    app.close()
    assert not callbacks._task_observers


def test_idle_on_a_closed_harness_raises() -> None:
    app = AppHarness(_text("x", "x"), size=SIZE)
    app.close()

    with pytest.raises(RuntimeError, match="is closed"):
        asyncio.run(app.idle())
