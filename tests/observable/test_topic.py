"""``Topic``: every publish delivered, in one order, to subscribers it does not keep alive."""

from __future__ import annotations

import gc
import logging
import threading
import weakref
from typing import Callable, Iterator, List, Tuple

import pytest

import nuiitivet.material as nv
from nuiitivet.common.logging_once import _clear_log_once_keys_for_tests
from nuiitivet.layout.column import Column
from nuiitivet.observable import protocols
from nuiitivet.observable.topic import Topic
from nuiitivet.observable.value import State
from nuiitivet.testing import HarnessClock, SubscriptionLeakError, mount
from nuiitivet.widgeting.widget import Widget


_TOPIC_LOGGER = "nuiitivet.observable.topic"


class _Recorder:
    """A subscriber with an owner: what a ViewModel is to a Model's Topic."""

    def __init__(self) -> None:
        self.seen: List[int] = []
        self.threads: List[int] = []

    def record(self, value: int) -> None:
        self.seen.append(value)
        self.threads.append(threading.get_ident())


def _on_worker(fn: Callable[[], None]) -> int:
    """Run ``fn`` on a thread of its own and return that thread's ident."""
    idents: List[int] = []

    def run() -> None:
        idents.append(threading.get_ident())
        fn()

    worker = threading.Thread(target=run)
    worker.start()
    worker.join()
    return idents[0]


@pytest.fixture
def untracked() -> Iterator[None]:
    """Run without the leak registry, which holds every ``Disposable`` it sees.

    A test of a ``Disposable`` nobody holds needs it to be collected.
    """
    tracker = protocols._subscription_tracker
    protocols._set_subscription_tracker(None)
    try:
        yield
    finally:
        protocols._set_subscription_tracker(tracker)


def test_topic_is_on_the_public_root() -> None:
    assert nv.Topic is Topic


# -- delivery ---------------------------------------------------------------


def test_a_publish_on_the_ui_thread_is_delivered_before_it_returns() -> None:
    topic: Topic[int] = Topic()
    recorder = _Recorder()
    topic.subscribe(recorder.record)

    topic.publish(1)

    assert recorder.seen == [1]


def test_an_equal_value_is_delivered_again() -> None:
    topic: Topic[int] = Topic()
    recorder = _Recorder()
    topic.subscribe(recorder.record)

    topic.publish(7)
    topic.publish(7)

    assert recorder.seen == [7, 7]


def test_every_publish_from_a_worker_within_one_tick_is_delivered(nuiitivet_clock: HarnessClock) -> None:
    topic: Topic[int] = Topic()
    recorder = _Recorder()
    topic.subscribe(recorder.record)

    def burst() -> None:
        for value in range(5):
            topic.publish(value)

    _on_worker(burst)
    assert recorder.seen == []

    nuiitivet_clock.pump()

    assert recorder.seen == [0, 1, 2, 3, 4]
    assert set(recorder.threads) == {threading.get_ident()}


def test_a_ui_thread_publish_follows_what_a_worker_queued_before_it(nuiitivet_clock: HarnessClock) -> None:
    topic: Topic[int] = Topic()
    recorder = _Recorder()
    topic.subscribe(recorder.record)

    _on_worker(lambda: topic.publish(1))
    topic.publish(2)

    assert recorder.seen == [1, 2]

    nuiitivet_clock.pump()

    assert recorder.seen == [1, 2]


def test_a_queued_value_goes_to_whoever_is_subscribed_at_delivery(nuiitivet_clock: HarnessClock) -> None:
    topic: Topic[int] = Topic()
    early = _Recorder()
    late = _Recorder()
    subscription = topic.subscribe(early.record)

    _on_worker(lambda: topic.publish(1))
    subscription.dispose()
    topic.subscribe(late.record)
    nuiitivet_clock.pump()

    assert early.seen == []
    assert late.seen == [1]


def test_a_value_published_to_nobody_never_reaches_a_later_subscriber(nuiitivet_clock: HarnessClock) -> None:
    topic: Topic[int] = Topic()
    late = _Recorder()

    _on_worker(lambda: topic.publish(1))
    topic.subscribe(late.record)
    nuiitivet_clock.pump()

    assert late.seen == []


def test_a_publish_from_a_subscriber_reaches_every_subscriber_in_the_same_order() -> None:
    topic: Topic[int] = Topic()
    first = _Recorder()
    second = _Recorder()

    def echo(value: int) -> None:
        first.record(value)
        if value == 1:
            topic.publish(2)

    echoing = topic.subscribe(echo)
    topic.subscribe(second.record)

    topic.publish(1)

    assert first.seen == [1, 2]
    assert second.seen == [1, 2]
    assert not echoing.is_disposed


def test_a_subscriber_that_raises_does_not_stop_the_others(caplog: pytest.LogCaptureFixture) -> None:
    _clear_log_once_keys_for_tests()
    topic: Topic[int] = Topic()
    recorder = _Recorder()

    def broken(value: int) -> None:
        raise ValueError("subscriber is broken")

    subscription = topic.subscribe(broken)
    topic.subscribe(recorder.record)

    with caplog.at_level(logging.ERROR, logger=_TOPIC_LOGGER):
        topic.publish(1)
        topic.publish(2)

    assert recorder.seen == [1, 2]
    assert [r.name for r in caplog.records] == [_TOPIC_LOGGER]
    assert not subscription.is_disposed
    _clear_log_once_keys_for_tests()


def test_a_batch_does_not_defer_a_publish() -> None:
    topic: Topic[int] = Topic()
    recorder = _Recorder()
    topic.subscribe(recorder.record)

    with nv.batch():
        topic.publish(1)
        assert recorder.seen == [1]


# -- dispatch=False ---------------------------------------------------------


def test_a_dispatch_false_subscriber_runs_on_the_publishing_thread(nuiitivet_clock: HarnessClock) -> None:
    topic: Topic[int] = Topic()
    on_ui = _Recorder()
    on_worker = _Recorder()
    topic.subscribe(on_ui.record)
    topic.subscribe(on_worker.record, dispatch=False)
    seen_before_return: List[Tuple[int, ...]] = []

    def publish_two() -> None:
        topic.publish(1)
        topic.publish(2)
        seen_before_return.append(tuple(on_worker.seen))

    worker_ident = _on_worker(publish_two)

    assert seen_before_return == [(1, 2)]
    assert set(on_worker.threads) == {worker_ident}
    assert on_ui.seen == []

    nuiitivet_clock.pump()

    assert on_ui.seen == [1, 2]
    assert on_worker.seen == [1, 2]


def test_nothing_is_queued_when_no_subscriber_dispatches(nuiitivet_clock: HarnessClock) -> None:
    topic: Topic[int] = Topic()
    recorder = _Recorder()
    topic.subscribe(recorder.record, dispatch=False)

    _on_worker(lambda: topic.publish(1))

    assert recorder.seen == [1]
    assert nuiitivet_clock.pending() == []


# -- lifetime ---------------------------------------------------------------


def test_a_collected_owner_receives_nothing_and_is_not_kept_alive() -> None:
    topic: Topic[int] = Topic()
    recorder = _Recorder()
    seen = recorder.seen
    alive = weakref.ref(recorder)
    topic.subscribe(recorder.record)

    del recorder
    gc.collect()
    topic.publish(1)

    assert alive() is None
    assert seen == []


def test_holding_the_disposable_does_not_keep_the_owner_alive() -> None:
    topic: Topic[int] = Topic()
    recorder = _Recorder()
    alive = weakref.ref(recorder)
    subscription = topic.subscribe(recorder.record)

    del recorder
    gc.collect()

    assert alive() is None
    assert not subscription.is_disposed


def test_a_lambda_lives_as_long_as_its_disposable(untracked: None) -> None:
    topic: Topic[int] = Topic()
    held: List[int] = []
    dropped: List[int] = []

    subscription = topic.subscribe(lambda value: held.append(value))
    topic.subscribe(lambda value: dropped.append(value))
    gc.collect()

    topic.publish(1)

    assert held == [1]
    assert dropped == []
    assert not subscription.is_disposed


def test_a_built_in_method_is_held_until_disposed(untracked: None) -> None:
    topic: Topic[int] = Topic()
    seen: List[int] = []

    subscription = topic.subscribe(seen.append)
    topic.publish(1)
    subscription.dispose()
    topic.publish(2)

    assert seen == [1]


def test_dispose_ends_one_subscription() -> None:
    topic: Topic[int] = Topic()
    disposed = _Recorder()
    kept = _Recorder()
    subscription = topic.subscribe(disposed.record)
    topic.subscribe(kept.record)

    subscription.dispose()
    topic.publish(1)

    assert disposed.seen == []
    assert kept.seen == [1]


def test_a_topic_declared_on_a_class_is_per_instance() -> None:
    class Model:
        saved = Topic[int]()

    first = Model()
    second = Model()
    recorder = _Recorder()
    first.saved.subscribe(recorder.record)

    second.saved.publish(1)
    first.saved.publish(2)

    assert first.saved is first.saved
    assert first.saved is not second.saved
    assert recorder.seen == [2]


# -- in a widget ------------------------------------------------------------


class _Probe(Widget):
    def __init__(self) -> None:
        super().__init__()
        self.seen: List[int] = []

    def _record(self, value: int) -> None:
        self.seen.append(value)


class _Screen(_Probe):
    """Subscribes its own method in ``__init__``, as a screen does."""

    def __init__(self, topic: Topic[int], *, dispatch: bool = True) -> None:
        super().__init__()
        topic.subscribe(self._record, dispatch=dispatch)


class _Remover:
    """A subscriber that takes ``child`` out of the tree when called."""

    def __init__(self, parent: Column, child: Widget) -> None:
        self._parent = parent
        self._child = child

    def remove(self, value: int) -> None:
        self._parent.remove_child(self._child)


def test_a_widget_method_is_not_called_before_the_mount() -> None:
    topic: Topic[int] = Topic()
    screen = _Screen(topic)

    topic.publish(1)

    assert screen.seen == []


def test_a_widget_method_is_called_while_the_widget_is_mounted() -> None:
    topic: Topic[int] = Topic()
    screen = _Screen(topic)

    with mount(screen) as host:
        host.layout(100, 100)
        topic.publish(1)

    assert screen.seen == [1]


def test_a_widget_method_is_not_called_after_the_unmount() -> None:
    topic: Topic[int] = Topic()
    screen = _Screen(topic)

    with mount(screen) as host:
        host.layout(100, 100)
    topic.publish(1)

    assert screen.seen == []


def test_a_widget_method_is_called_again_after_a_remount() -> None:
    topic: Topic[int] = Topic()
    screen = _Screen(topic)

    with mount(screen) as host:
        host.layout(100, 100)
        topic.publish(1)
    topic.publish(2)
    with mount(screen) as host:
        host.layout(100, 100)
        topic.publish(3)

    assert screen.seen == [1, 3]


def test_a_value_still_queued_at_the_unmount_is_not_delivered(nuiitivet_clock: HarnessClock) -> None:
    topic: Topic[int] = Topic()
    screen = _Screen(topic)

    with mount(screen) as host:
        host.layout(100, 100)
        _on_worker(lambda: topic.publish(1))
    nuiitivet_clock.pump()

    assert screen.seen == []


def test_a_widget_unmounted_by_an_earlier_subscriber_is_not_called() -> None:
    topic: Topic[int] = Topic()
    parent = Column(children=[])
    screen = _Probe()
    remover = _Remover(parent, screen)
    topic.subscribe(remover.remove)
    topic.subscribe(screen._record)

    with mount(parent) as host:
        host.layout(100, 100)
        parent.add_child(screen)
        topic.publish(1)

    assert screen.seen == []


def test_the_rule_holds_for_a_dispatch_false_subscriber() -> None:
    topic: Topic[int] = Topic()
    screen = _Screen(topic, dispatch=False)

    topic.publish(1)
    with mount(screen) as host:
        host.layout(100, 100)
        topic.publish(2)
    topic.publish(3)

    assert screen.seen == [2]


def test_a_widget_that_subscribed_above_super_init_is_asked_without_error() -> None:
    class Early(Widget):
        def __init__(self, topic: Topic[int]) -> None:
            self.seen: List[int] = []
            topic.subscribe(self._record)
            topic.publish(0)
            super().__init__()

        def _record(self, value: int) -> None:
            self.seen.append(value)

    topic: Topic[int] = Topic()

    screen = Early(topic)

    assert screen.seen == []


def test_a_lambda_over_a_widget_is_called_whatever_its_mount_state() -> None:
    topic: Topic[int] = Topic()
    probe = _Probe()
    subscription = topic.subscribe(lambda value: probe.seen.append(value))

    topic.publish(1)
    subscription.dispose()

    assert probe.seen == [1]


def test_a_state_calls_a_widget_method_whatever_its_mount_state() -> None:
    state: State[int] = State(0)
    probe = _Probe()
    subscription = state.subscribe(probe._record)

    state.value = 1
    subscription.dispose()

    assert probe.seen == [1]


# -- the leak check ---------------------------------------------------------


class _LambdaScreen(_Probe):
    """Subscribes a lambda at mount; ``bound`` hands it to ``bind()``."""

    def __init__(self, topic: Topic[int], *, bound: bool) -> None:
        super().__init__()
        self._topic = topic
        self._bound = bound

    def on_mount(self) -> None:
        super().on_mount()
        self._subscription = self._topic.subscribe(lambda value: self.seen.append(value))
        if self._bound:
            self.bind(self._subscription)


def test_the_leak_check_passes_a_method_subscribed_without_bind() -> None:
    topic: Topic[int] = Topic()
    screen = _Screen(topic)

    with mount(screen, leak_check="error") as host:
        host.layout(100, 100)


def test_the_leak_check_reports_a_lambda_subscribed_without_bind() -> None:
    topic: Topic[int] = Topic()
    screen = _LambdaScreen(topic, bound=False)

    with pytest.raises(SubscriptionLeakError) as excinfo:
        with mount(screen, leak_check="error") as host:
            host.layout(100, 100)

    assert "_LambdaScreen" in str(excinfo.value)


def test_bind_ends_a_lambda_subscription_at_unmount() -> None:
    topic: Topic[int] = Topic()
    screen = _LambdaScreen(topic, bound=True)

    with mount(screen, leak_check="error") as host:
        host.layout(100, 100)
        topic.publish(1)
    topic.publish(2)

    assert screen.seen == [1]
