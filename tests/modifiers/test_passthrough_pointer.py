"""Tests for passthrough_pointer() modifier."""

from __future__ import annotations

from nuiitivet.modifiers.passthrough_pointer import PassthroughPointerBox, passthrough_pointer
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
    return Box(width=Sizing.fixed(100), height=Sizing.fixed(50), background_color=(255, 0, 0, 255))


def test_passthrough_pointer_default_blocks_hit_test() -> None:
    child = _make_child()
    wrapped = child.modifier(passthrough_pointer())
    assert isinstance(wrapped, PassthroughPointerBox)
    assert wrapped._active is True

    wrapped.layout(100, 50)
    assert wrapped.hit_test(50, 25) is None


def test_passthrough_pointer_static_false_does_not_block() -> None:
    child = _make_child()
    wrapped = child.modifier(passthrough_pointer(False))
    assert isinstance(wrapped, PassthroughPointerBox)
    assert wrapped._active is False

    wrapped.layout(100, 50)
    # When inactive, hit testing reaches the child / box itself.
    assert wrapped.hit_test(50, 25) is not None


def test_passthrough_pointer_observable_toggles_active() -> None:
    cond = _ObservableValue(False)
    child = _make_child()
    wrapped = child.modifier(passthrough_pointer(cond))
    assert isinstance(wrapped, PassthroughPointerBox)

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


def test_passthrough_pointer_preserves_layout_size() -> None:
    child = _make_child()
    wrapped = child.modifier(passthrough_pointer())
    assert wrapped.preferred_size() == (100, 50)
