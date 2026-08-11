"""Subscription-leak detection: what it catches, and what it must not."""

from __future__ import annotations

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.testing import SubscriptionLeakError, SubscriptionLeakWarning, mount
from nuiitivet.testing._leaks import attribute, track_subscriptions
from nuiitivet.widgeting.widget import Widget


class _Leaky(Widget):
    """Subscribes on mount and never disposes -- the bug this check exists for."""

    def __init__(self, source) -> None:
        super().__init__()
        self._source = source
        self.seen: list = []

    def on_mount(self) -> None:
        super().on_mount()
        self._source.subscribe(self._record)

    def _record(self, value) -> None:
        self.seen.append(value)


class _LeakyLambda(Widget):
    """The same leak with a lambda, so attribution goes through a closure."""

    def __init__(self, source) -> None:
        super().__init__()
        self._source = source
        self.seen: list = []

    def on_mount(self) -> None:
        super().on_mount()
        self._source.subscribe(lambda value: self.seen.append(value))


class _Bound(Widget):
    """The same subscription, done correctly."""

    def __init__(self, source) -> None:
        super().__init__()
        self._source = source
        self.seen: list = []

    def on_mount(self) -> None:
        super().on_mount()
        self.bind(self._source.subscribe(self.seen.append))


class _LeakyInConstructor(Widget):
    """Subscribes before ``mount()`` can see it -- Toggleable's old shape."""

    def __init__(self, source) -> None:
        super().__init__()
        self.seen: list = []
        source.subscribe(self._record)

    def _record(self, value) -> None:
        self.seen.append(value)


# -- what it catches --------------------------------------------------------


def test_a_widget_that_forgets_to_dispose_fails_its_own_test():
    source = _ObservableValue(0)
    with pytest.raises(SubscriptionLeakError) as excinfo:
        with mount(_Leaky(source)) as host:
            host.layout(100, 100)
    assert "_Leaky" in str(excinfo.value)


def test_the_message_names_the_creation_site():
    source = _ObservableValue(0)
    with pytest.raises(SubscriptionLeakError) as excinfo:
        with mount(_Leaky(source)) as host:
            host.layout(100, 100)
    # The line inside _Leaky.on_mount, not the observable's own subscribe(): a
    # report that points into value.py names the plumbing and not the bug.
    assert "test_leaks.py:" in str(excinfo.value)
    assert "observable/value.py" not in str(excinfo.value)


def test_a_lambda_subscription_is_attributed_to_its_widget():
    source = _ObservableValue(0)
    with pytest.raises(SubscriptionLeakError) as excinfo:
        with mount(_LeakyLambda(source)) as host:
            host.layout(100, 100)
    assert "_LeakyLambda" in str(excinfo.value)


def test_a_subscription_taken_in_the_constructor_is_caught():
    """The flag is armed by the plugin, so it is already on at construction.

    A harness-armed flag would miss this entirely, and this is the shape the
    framework's own widgets had.
    """
    source = _ObservableValue(0)
    widget = _LeakyInConstructor(source)
    with pytest.raises(SubscriptionLeakError):
        with mount(widget) as host:
            host.layout(100, 100)


# -- what it must not catch -------------------------------------------------


def test_a_bound_subscription_passes():
    source = _ObservableValue(0)
    with mount(_Bound(source)) as host:
        host.layout(100, 100)
        source.value = 1
    assert source._subs == []


def test_a_widget_that_was_never_mounted_is_not_a_leak():
    """It never entered a tree, so nothing outlived anything."""
    source = _ObservableValue(0)
    _LeakyInConstructor(source)  # constructed, never mounted
    with mount(_Bound(_ObservableValue(0))) as host:
        host.layout(100, 100)


def test_a_still_mounted_widget_is_not_reported_by_another_harness():
    """Two harnesses: closing the second must not blame the first's live tree."""
    source = _ObservableValue(0)
    first = mount(_Bound(source))
    first.layout(100, 100)
    try:
        with mount(_Bound(_ObservableValue(0))) as second:
            second.layout(100, 100)
    finally:
        first.close()


def test_a_leak_survives_an_earlier_harness_passing_it_by():
    """The other half of that rule: the first harness must not silence it.

    A subscription belonging to a still-mounted widget is left unclaimed, so the
    harness that eventually unmounts it still reports it.
    """
    source = _ObservableValue(0)
    leaky = _Leaky(source)
    outer = mount(leaky)
    outer.layout(100, 100)
    with mount(_Bound(_ObservableValue(0))) as inner:  # closes first, sees nothing
        inner.layout(100, 100)
    with pytest.raises(SubscriptionLeakError):
        outer.close()


def test_an_observable_graph_edge_is_not_a_widget_leak():
    """``Computed``'s subscription to its dependencies is not anyone's bug."""
    source = _ObservableValue(1)
    doubled = source.map(lambda v: v * 2)
    with mount(_Bound(doubled)) as host:
        host.layout(100, 100)
        source.value = 2


# -- levels -----------------------------------------------------------------


def test_warn_reports_without_failing():
    source = _ObservableValue(0)
    with pytest.warns(SubscriptionLeakWarning, match="_Leaky"):
        with mount(_Leaky(source), leak_check="warn") as host:
            host.layout(100, 100)


def test_off_reports_nothing():
    source = _ObservableValue(0)
    with mount(_Leaky(source), leak_check="off") as host:
        host.layout(100, 100)


@pytest.mark.nuiitivet(leak_check="off")
def test_the_marker_sets_the_default_for_the_test():
    source = _ObservableValue(0)
    with mount(_Leaky(source)) as host:
        host.layout(100, 100)


@pytest.mark.nuiitivet(leak_check="off")
def test_the_kwarg_overrides_the_marker():
    source = _ObservableValue(0)
    with pytest.raises(SubscriptionLeakError):
        with mount(_Leaky(source), leak_check="error") as host:
            host.layout(100, 100)


def test_an_invalid_level_is_refused():
    with pytest.raises(ValueError, match="leak_check"):
        mount(Column(children=[]), leak_check="loud")


# -- attribution ------------------------------------------------------------


def test_attribute_recovers_observable_callback_and_owner():
    source = _ObservableValue(0)
    widget = _LeakyInConstructor(source)
    with track_subscriptions() as registry:
        disposable = source.subscribe(widget._record)
    observable, callback, owner = attribute(disposable)
    assert observable is source
    assert callback == widget._record
    assert owner is widget
    assert registry.records


def test_a_callback_owned_by_something_that_is_not_a_widget_is_not_blamed():
    """The limit of attribution, pinned rather than left to be discovered.

    ``obs.subscribe(self._items.append)`` is a bound method of a list, so there
    is no widget behind it to hold the subscription against. It is counted in the
    report's tail, never as a failure of its own -- app code may legitimately own
    a subscription whose lifetime the harness knows nothing about.
    """
    source = _ObservableValue(0)
    widget = _Bound(source)
    with mount(widget) as host:
        host.layout(100, 100)
        source.subscribe(widget.seen.append)  # never disposed, never blamed
