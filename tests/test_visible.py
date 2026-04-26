"""Tests for visible() modifier."""

from __future__ import annotations

from typing import Callable

from nuiitivet.animation import LinearMotion
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import FadePattern
from nuiitivet.modifiers.visible import VisibleBox, visible
from nuiitivet.observable import runtime as observable_runtime
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box


class _FakeClock:
    def __init__(self) -> None:
        self._intervals: list[Callable[[float], None]] = []

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        del fn, delay

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        del interval
        if fn not in self._intervals:
            self._intervals.append(fn)

    def unschedule(self, fn: Callable[[float], None]) -> None:
        self._intervals = [cb for cb in self._intervals if cb is not fn]

    def advance(self, dt: float) -> None:
        for cb in list(self._intervals):
            cb(dt)


class _DummyApp:
    def __init__(self) -> None:
        self.invalidated = 0

    def invalidate(self, immediate: bool = False) -> None:
        del immediate
        self.invalidated += 1


def _make_child() -> Box:
    return Box(width=Sizing.fixed(100), height=Sizing.fixed(50))


def test_visible_static_true_mounts_child() -> None:
    child = _make_child()
    box = child.modifier(visible(True))

    assert isinstance(box, VisibleBox)
    assert box._physical_present is True
    assert box._logical_visible is True
    assert box.preferred_size() == (100, 50)


def test_visible_static_false_does_not_mount_child() -> None:
    child = _make_child()
    box = child.modifier(visible(False))

    assert isinstance(box, VisibleBox)
    assert box._physical_present is False
    assert box._logical_visible is False
    assert box.preferred_size() == (0, 0)
    # Sizing collapses to 0 so parents allocate no space.
    assert box.width_sizing.kind == "fixed"
    assert box.width_sizing.value == 0
    assert box.height_sizing.kind == "fixed"
    assert box.height_sizing.value == 0


def test_visible_observable_show_then_hide_no_transition() -> None:
    cond = _ObservableValue(False)
    child = _make_child()
    box = child.modifier(visible(cond))
    assert isinstance(box, VisibleBox)

    app = _DummyApp()
    box.mount(app)

    assert box._physical_present is False
    assert box.preferred_size() == (0, 0)

    cond.value = True
    assert box._physical_present is True
    assert box._logical_visible is True
    assert box.preferred_size() == (100, 50)

    cond.value = False
    assert box._physical_present is False
    assert box._logical_visible is False
    assert box.preferred_size() == (0, 0)


def test_visible_initial_true_observable_is_mounted() -> None:
    cond = _ObservableValue(True)
    child = _make_child()
    box = child.modifier(visible(cond))
    assert isinstance(box, VisibleBox)

    assert box._physical_present is True
    assert box.preferred_size() == (100, 50)


def test_visible_hidden_blocks_hit_test() -> None:
    cond = _ObservableValue(False)
    child = _make_child()
    box = child.modifier(visible(cond))
    assert isinstance(box, VisibleBox)

    box.layout(0, 0)
    assert box.hit_test(0, 0) is None


def test_visible_with_transition_keeps_mounted_during_exit() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        cond = _ObservableValue(True)
        child = _make_child()
        transition = TransitionDefinition(
            motion=LinearMotion(1.0),
            pattern=FadePattern(start_alpha=0.0, end_alpha=1.0),
        )
        box = child.modifier(visible(cond, transition=transition))
        assert isinstance(box, VisibleBox)

        app = _DummyApp()
        box.mount(app)

        # Initially visible: progress=1.0, child mounted.
        assert box._physical_present is True
        assert box._progress == 1.0

        # Trigger hide.
        cond.value = False

        # Logical visibility flipped immediately, but child remains mounted
        # while exit animation runs.
        assert box._logical_visible is False
        assert box._physical_present is True

        # Hit-testing is blocked even before animation completes.
        box.layout(100, 50)
        assert box.hit_test(50, 25) is None

        # Halfway through: progress should be ~0.5, still mounted.
        fake_clock.advance(0.5)
        assert 0.4 <= box._progress <= 0.6
        assert box._physical_present is True

        # Animation completes: progress hits 0.0 -> child unmounted.
        fake_clock.advance(0.5)
        assert box._progress == 0.0
        assert box._physical_present is False
    finally:
        observable_runtime.set_clock(prev_clock)


def test_visible_with_transition_enter_animates_progress() -> None:
    prev_clock = observable_runtime.clock
    fake_clock = _FakeClock()
    observable_runtime.set_clock(fake_clock)
    try:
        cond = _ObservableValue(False)
        child = _make_child()
        transition = TransitionDefinition(
            motion=LinearMotion(1.0),
            pattern=FadePattern(start_alpha=0.0, end_alpha=1.0),
        )
        box = child.modifier(visible(cond, transition=transition))
        assert isinstance(box, VisibleBox)

        app = _DummyApp()
        box.mount(app)

        # Trigger show.
        cond.value = True

        # Mounted immediately; progress starts at 0 and animates up.
        assert box._physical_present is True
        assert box._logical_visible is True

        fake_clock.advance(0.5)
        assert 0.4 <= box._progress <= 0.6

        fake_clock.advance(0.5)
        assert box._progress == 1.0
        assert box._physical_present is True
    finally:
        observable_runtime.set_clock(prev_clock)


def test_visible_show_after_hide_remounts_child() -> None:
    cond = _ObservableValue(True)
    child = _make_child()
    box = child.modifier(visible(cond))
    assert isinstance(box, VisibleBox)

    app = _DummyApp()
    box.mount(app)

    cond.value = False
    assert box._physical_present is False

    cond.value = True
    assert box._physical_present is True
    assert box.preferred_size() == (100, 50)


def test_visible_modifier_chains_with_other_modifiers() -> None:
    from nuiitivet.modifiers import opacity

    cond = _ObservableValue(True)
    child = _make_child()
    # Apply visible after opacity. Result should be a VisibleBox at the top.
    wrapped = child.modifier(opacity(0.5) | visible(cond))
    assert isinstance(wrapped, VisibleBox)
    assert wrapped._physical_present is True
