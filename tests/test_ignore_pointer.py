"""Tests for ignore_pointer() modifier."""

from __future__ import annotations

from nuiitivet.modifiers.ignore_pointer import IgnorePointerBox, ignore_pointer
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box


class _DummyApp:
    def __init__(self) -> None:
        self.invalidated = 0

    def invalidate(self, immediate: bool = False) -> None:
        del immediate
        self.invalidated += 1


def _make_child() -> Box:
    return Box(width=Sizing.fixed(100), height=Sizing.fixed(50))


def test_ignore_pointer_default_blocks_hit_test() -> None:
    child = _make_child()
    wrapped = child.modifier(ignore_pointer())
    assert isinstance(wrapped, IgnorePointerBox)
    assert wrapped._active is True

    wrapped.layout(100, 50)
    assert wrapped.hit_test(50, 25) is None


def test_ignore_pointer_static_false_does_not_block() -> None:
    child = _make_child()
    wrapped = child.modifier(ignore_pointer(False))
    assert isinstance(wrapped, IgnorePointerBox)
    assert wrapped._active is False

    wrapped.layout(100, 50)
    # When inactive, hit testing reaches the child / box itself.
    assert wrapped.hit_test(50, 25) is not None


def test_ignore_pointer_observable_toggles_active() -> None:
    cond = _ObservableValue(False)
    child = _make_child()
    wrapped = child.modifier(ignore_pointer(cond))
    assert isinstance(wrapped, IgnorePointerBox)

    app = _DummyApp()
    wrapped.mount(app)
    wrapped.layout(100, 50)

    assert wrapped._active is False
    assert wrapped.hit_test(50, 25) is not None

    cond.value = True
    assert wrapped._active is True
    assert wrapped.hit_test(50, 25) is None

    cond.value = False
    assert wrapped._active is False
    assert wrapped.hit_test(50, 25) is not None


def test_ignore_pointer_preserves_layout_size() -> None:
    child = _make_child()
    wrapped = child.modifier(ignore_pointer())
    assert wrapped.preferred_size() == (100, 50)
