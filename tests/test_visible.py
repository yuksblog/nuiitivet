"""Tests for visible() modifier (composition of opacity + ignore_pointer)."""

from __future__ import annotations

from typing import Callable

from nuiitivet.animation import LinearMotion
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import FadePattern
from nuiitivet.modifiers.ignore_pointer import IgnorePointerBox
from nuiitivet.modifiers.transform import TransformBox
from nuiitivet.modifiers.visible import _AnimatedVisibleBox, visible
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


# ---------------------------------------------------------------------------
# Static (non-animated) composition
# ---------------------------------------------------------------------------


def test_visible_static_true_composes_opacity_and_ignore_pointer() -> None:
    child = _make_child()
    wrapped = child.modifier(visible(True))

    # Outer wrapper is IgnorePointerBox; inside is a TransformBox (opacity).
    assert isinstance(wrapped, IgnorePointerBox)
    assert wrapped._active is False
    inner = wrapped.children[0]
    assert isinstance(inner, TransformBox)
    assert inner._opacity == 1.0


def test_visible_static_false_keeps_layout_and_blocks_input() -> None:
    child = _make_child()
    wrapped = child.modifier(visible(False))

    assert isinstance(wrapped, IgnorePointerBox)
    assert wrapped._active is True
    inner = wrapped.children[0]
    assert isinstance(inner, TransformBox)
    assert inner._opacity == 0.0

    # Layout space is preserved (no zero collapse).
    assert wrapped.preferred_size() == (100, 50)

    # Hit-test is blocked while hidden.
    wrapped.layout(100, 50)
    assert wrapped.hit_test(50, 25) is None


def test_visible_observable_toggles_input_blocking_and_opacity() -> None:
    cond = _ObservableValue(True)
    child = _make_child()
    wrapped = child.modifier(visible(cond))
    assert isinstance(wrapped, IgnorePointerBox)
    inner = wrapped.children[0]
    assert isinstance(inner, TransformBox)

    app = _DummyApp()
    wrapped.mount(app)

    assert wrapped._active is False
    assert inner._opacity == 1.0

    cond.value = False
    assert wrapped._active is True
    assert inner._opacity == 0.0

    cond.value = True
    assert wrapped._active is False
    assert inner._opacity == 1.0


def test_visible_observable_layout_space_preserved_when_hidden() -> None:
    cond = _ObservableValue(False)
    child = _make_child()
    wrapped = child.modifier(visible(cond))

    app = _DummyApp()
    wrapped.mount(app)

    # Layout space stays at child's natural size in both states.
    assert wrapped.preferred_size() == (100, 50)
    cond.value = True
    assert wrapped.preferred_size() == (100, 50)
    cond.value = False
    assert wrapped.preferred_size() == (100, 50)


def test_visible_child_stays_mounted_across_hide_show_cycles() -> None:
    cond = _ObservableValue(True)
    child = _make_child()
    wrapped = child.modifier(visible(cond))

    app = _DummyApp()
    wrapped.mount(app)

    inner = wrapped.children[0]
    assert isinstance(inner, TransformBox)
    # The original child is the inner-most descendant.
    assert child in inner.children

    cond.value = False
    cond.value = True

    # Same child instance is still mounted (state preserved).
    assert child in inner.children


# ---------------------------------------------------------------------------
# Animated path
# ---------------------------------------------------------------------------


def test_visible_with_transition_initial_visible_animates_exit() -> None:
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
        wrapped = child.modifier(visible(cond, transition=transition))

        # Outer wrapper is IgnorePointerBox; inside is _AnimatedVisibleBox.
        assert isinstance(wrapped, IgnorePointerBox)
        paint_box = wrapped.children[0]
        assert isinstance(paint_box, _AnimatedVisibleBox)

        app = _DummyApp()
        wrapped.mount(app)

        assert paint_box._progress == 1.0
        assert wrapped._active is False

        # Trigger hide. Hit-test is blocked immediately (ignore_pointer toggles).
        cond.value = False
        assert wrapped._active is True
        wrapped.layout(100, 50)
        assert wrapped.hit_test(50, 25) is None

        # Halfway through exit: progress ~0.5, child still mounted.
        fake_clock.advance(0.5)
        assert 0.4 <= paint_box._progress <= 0.6
        assert child in paint_box.children

        # Animation completes: progress reaches 0.0; child remains mounted.
        fake_clock.advance(0.5)
        assert paint_box._progress == 0.0
        assert child in paint_box.children
    finally:
        observable_runtime.set_clock(prev_clock)


def test_visible_with_transition_enter_animates_progress_up() -> None:
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
        wrapped = child.modifier(visible(cond, transition=transition))
        assert isinstance(wrapped, IgnorePointerBox)
        paint_box = wrapped.children[0]
        assert isinstance(paint_box, _AnimatedVisibleBox)

        app = _DummyApp()
        wrapped.mount(app)

        assert paint_box._progress == 0.0
        assert wrapped._active is True

        cond.value = True
        assert wrapped._active is False

        fake_clock.advance(0.5)
        assert 0.4 <= paint_box._progress <= 0.6

        fake_clock.advance(0.5)
        assert paint_box._progress == 1.0
    finally:
        observable_runtime.set_clock(prev_clock)


def test_visible_chains_with_other_modifiers() -> None:
    from nuiitivet.modifiers import opacity

    cond = _ObservableValue(True)
    child = _make_child()
    # Apply opacity first, then visible. visible() expands to opacity|ignore_pointer
    # so the outer-most wrapper is IgnorePointerBox.
    wrapped = child.modifier(opacity(0.5) | visible(cond))
    assert isinstance(wrapped, IgnorePointerBox)
    assert wrapped._active is False
