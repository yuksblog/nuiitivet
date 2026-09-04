"""Tests for the pointer-participation modifier family.

``defer_pointer`` / ``block_pointer`` / ``absorb_pointer`` each pick one posture
on the internal S (self surface) x C (children) hit model, and
``passthrough_pointer`` is the both-off corner. The matrix is exercised with a
transparent aligner child (which defers under ``auto``) holding one small painted
Box, so an "inner" point lands on a descending child while an "empty" point only
resolves via the wrapper's own surface.
"""

from __future__ import annotations

from nuiitivet.modifiers.absorb_pointer import (
    AbsorbPointerBox,
    absorb_pointer,
)
from nuiitivet.modifiers.block_pointer import BlockPointerBox, block_pointer
from nuiitivet.modifiers.defer_pointer import DeferPointerBox, defer_pointer
from nuiitivet.modifiers.passthrough_pointer import passthrough_pointer
from nuiitivet.observable import ObservableBase
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.layout.container import Container
from nuiitivet.layout.stack import Stack
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box


class _DummyApp:
    def __init__(self) -> None:
        self.invalidated = 0

    def invalidate(self, immediate: bool = False) -> None:
        del immediate
        self.invalidated += 1


# An "inner" child that catches (painted), pinned top-left inside a transparent
# aligner that defers. Points over ``inner`` reach a descending child; points in
# the empty area only resolve via the wrapper's own surface (S).
_INNER = "inner"
_EMPTY = "empty"
_INNER_POINT = (10, 10)
_EMPTY_POINT = (80, 40)


def _make_child() -> Container:
    inner = Box(
        width=Sizing.fixed(40),
        height=Sizing.fixed(20),
        background_color=(255, 0, 0, 255),
    )
    return Container(inner, width="wt", height="wt", alignment="top-left")


def _inner_of(child: Container) -> Box:
    box = child.children[0]
    assert isinstance(box, Box)
    return box


def test_defer_pointer_self_defers_children_catch() -> None:
    child = _make_child()
    inner = _inner_of(child)
    wrapped = child.modifier(defer_pointer())
    assert isinstance(wrapped, DeferPointerBox)
    assert wrapped._active is True

    wrapped.layout(100, 50)
    # C: descends -> inner catches.
    assert wrapped.hit_test(*_INNER_POINT) is inner
    # S = none: empty area is not caught by the wrapper.
    assert wrapped.hit_test(*_EMPTY_POINT) is None


def test_block_pointer_self_catches_children_catch() -> None:
    child = _make_child()
    inner = _inner_of(child)
    wrapped = child.modifier(block_pointer())
    assert isinstance(wrapped, BlockPointerBox)

    wrapped.layout(100, 50)
    # C: descends -> inner still catches.
    assert wrapped.hit_test(*_INNER_POINT) is inner
    # S = all: empty area is caught by the wrapper itself (blocks what's behind).
    assert wrapped.hit_test(*_EMPTY_POINT) is wrapped


def test_absorb_pointer_self_catches_children_absorbed() -> None:
    child = _make_child()
    wrapped = child.modifier(absorb_pointer())
    assert isinstance(wrapped, AbsorbPointerBox)

    wrapped.layout(100, 50)
    # C = none: the child is not descended into; the wrapper absorbs the click.
    assert wrapped.hit_test(*_INNER_POINT) is wrapped
    # S = all: empty area is caught too.
    assert wrapped.hit_test(*_EMPTY_POINT) is wrapped


def test_passthrough_pointer_whole_subtree_click_through() -> None:
    child = _make_child()
    wrapped = child.modifier(passthrough_pointer())

    wrapped.layout(100, 50)
    # Both axes off: nothing in the subtree catches.
    assert wrapped.hit_test(*_INNER_POINT) is None
    assert wrapped.hit_test(*_EMPTY_POINT) is None


def test_inactive_condition_falls_back_to_auto() -> None:
    """A falsy condition disables the override -> the ``auto`` default applies."""
    child = _make_child()
    inner = _inner_of(child)
    # block_pointer(False): the transparent aligner reverts to deferring.
    wrapped = child.modifier(block_pointer(False))
    assert isinstance(wrapped, BlockPointerBox)
    assert wrapped._active is False

    wrapped.layout(100, 50)
    assert wrapped.hit_test(*_INNER_POINT) is inner
    # auto: transparent aligner does not catch the empty area.
    assert wrapped.hit_test(*_EMPTY_POINT) is None


def test_defer_pointer_suppresses_painted_self_surface() -> None:
    """The distinguishing case: a painted leaf that would catch under ``auto``.

    ``defer_pointer`` turns off the wrapped widget's own surface (S = none);
    with no children to catch, the painted box now lets clicks pass through.
    """
    painted = Box(width=Sizing.fixed(100), height=Sizing.fixed(50), background_color=(1, 2, 3, 255))
    assert painted.modifier(defer_pointer()).__class__ is DeferPointerBox

    deferred = painted.modifier(defer_pointer())
    deferred.layout(100, 50)
    assert deferred.hit_test(50, 25) is None

    # Sanity: the same painted box catches under auto (no modifier).
    bare = Box(width=Sizing.fixed(100), height=Sizing.fixed(50), background_color=(1, 2, 3, 255))
    bare.layout(100, 50)
    assert bare.hit_test(50, 25) is bare


def test_reported_bug_repro_with_explicit_defer_pointer() -> None:
    """Stack([canvas, full-size Container(toolbar)]) with explicit defer_pointer().

    The bug that motivated hit participation, spelled out explicitly: the full-size alignment
    Container hands empty-area clicks to the canvas behind it, while the toolbar
    strip still catches.
    """
    canvas = Box(width="wt", height="wt", background_color=(10, 20, 30, 255))
    toolbar = Box(width=Sizing.fixed(200), height=Sizing.fixed(40), background_color=(200, 200, 200, 255))
    overlay = Container(
        toolbar,
        width="wt",
        height="wt",
        alignment="bottom-center",
    ).modifier(defer_pointer())
    stack = Stack(children=[canvas, overlay])

    stack.layout(400, 300)

    # Empty area: the overlay defers, so the canvas behind receives the hit.
    assert stack.hit_test(200, 50) is canvas
    # Over the toolbar strip (bottom-center, 200x40 at x=100, y=260): it catches.
    assert stack.hit_test(200, 280) is toolbar


def test_observable_condition_read_at_construction() -> None:
    """The condition is resolved at construction, not deferred to first click."""
    cond = _ObservableValue(True)
    child = _make_child()
    wrapped = child.modifier(block_pointer(cond))
    assert isinstance(wrapped, BlockPointerBox)
    # Active state reflects the observable immediately, before any hit_test.
    assert wrapped._active is True


class _RaisingObservable(ObservableBase[bool]):
    """Observable whose value read raises -- to prove construction is defensive."""

    @property
    def value(self) -> bool:  # type: ignore[override]
        raise RuntimeError("boom")

    def subscribe(self, callback):  # pragma: no cover - not exercised here
        raise NotImplementedError


def test_invalid_observable_condition_caught_at_construction() -> None:
    child = _make_child()
    # Construction must not raise; the bad read is swallowed and defaults active.
    wrapped = child.modifier(defer_pointer(_RaisingObservable()))
    assert isinstance(wrapped, DeferPointerBox)
    assert wrapped._active is True
    wrapped.layout(100, 50)
    # And a click does not surface the error either.
    wrapped.hit_test(*_EMPTY_POINT)


def test_reactive_toggle_switches_posture() -> None:
    cond = _ObservableValue(False)
    child = _make_child()
    inner = _inner_of(child)
    wrapped = child.modifier(block_pointer(cond))
    assert isinstance(wrapped, BlockPointerBox)

    app = _DummyApp()
    wrapped.mount(app)
    wrapped.layout(100, 50)

    # Inactive -> auto: empty area defers (transparent aligner).
    assert wrapped._active is False
    assert wrapped.hit_test(*_EMPTY_POINT) is None

    cond.value = True
    assert wrapped._active is True
    # Active -> block_pointer: empty area now caught by the wrapper.
    assert wrapped.hit_test(*_EMPTY_POINT) is wrapped
    # Children keep working across the toggle.
    assert wrapped.hit_test(*_INNER_POINT) is inner

    cond.value = False
    assert wrapped._active is False
    assert wrapped.hit_test(*_EMPTY_POINT) is None


def test_stacking_outermost_governs_contested_self_surface() -> None:
    """When two postures are stacked, the outermost (last-applied) box wins.

    ``defer_pointer() | block_pointer()`` nests block_pointer outside defer.
    block_pointer descends into the defer box (which yields nothing on the empty
    area) and then catches on its own surface -> the outer posture governs S.
    """
    child = _make_child()
    inner = _inner_of(child)
    wrapped = child.modifier(defer_pointer() | block_pointer())
    assert isinstance(wrapped, BlockPointerBox)

    wrapped.layout(100, 50)
    # Descent still reaches the inner child through both boxes.
    assert wrapped.hit_test(*_INNER_POINT) is inner
    # Empty area: the outermost block_pointer catches.
    assert wrapped.hit_test(*_EMPTY_POINT) is wrapped


def test_stacking_passthrough_pointer_dominates_whole_subtree() -> None:
    """An outer passthrough_pointer opens the whole subtree regardless of inner posture."""
    child = _make_child()
    wrapped = child.modifier(block_pointer() | passthrough_pointer())

    wrapped.layout(100, 50)
    assert wrapped.hit_test(*_INNER_POINT) is None
    assert wrapped.hit_test(*_EMPTY_POINT) is None
