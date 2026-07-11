"""Tests for the ``pointer_input()`` modifier (issue #308).

Covers the modifier's node wiring: it attaches a ``PointerListenerNode``,
composes with ``clickable`` without either clobbering the other, and reconfigures
(rather than stacking) a second node when re-applied during recomposition.
"""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.input.codes import BUTTON_LEFT
from nuiitivet.input.pointer import PointerEvent, PointerEventType as T
from nuiitivet.modifiers.pointer_input import PointerInputModifier, pointer_input
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import InteractionRegion, PointerInputNode, PointerListenerNode


def _make_child() -> Box:
    return Box(width=Sizing.fixed(100), height=Sizing.fixed(50))


def _press(region: InteractionRegion, x: float, y: float) -> None:
    region.set_last_rect(0, 0, 100, 50)
    region.on_pointer_event(PointerEvent.mouse_event(1, T.PRESS, x, y, button=BUTTON_LEFT))


def test_exported_from_modifiers_and_root() -> None:
    from nuiitivet.modifiers import pointer_input as from_modifiers

    assert nv.pointer_input is from_modifiers


def test_pointer_input_attaches_listener_node() -> None:
    presses = []
    wrapped = _make_child().modifier(
        pointer_input(on_press=lambda e: presses.append((e.local_x, e.local_y)), capture=False)
    )
    assert isinstance(wrapped, InteractionRegion)
    node = wrapped.get_node(PointerListenerNode)
    assert isinstance(node, PointerListenerNode)

    _press(wrapped, 30, 25)
    assert presses == [(30.0, 25.0)]


def test_composes_with_clickable_without_clobbering() -> None:
    presses, clicks = [], []
    wrapped = (
        _make_child()
        .modifier(pointer_input(on_press=lambda e: presses.append(1), capture=False))
        .modifier(nv.clickable(on_click=lambda: clicks.append(1)))
    )
    region = wrapped
    assert isinstance(region, InteractionRegion)
    # Both nodes live on the same region.
    assert isinstance(region.get_node(PointerListenerNode), PointerListenerNode)
    assert isinstance(region.get_node(PointerInputNode), PointerInputNode)

    region.set_last_rect(0, 0, 100, 50)
    region.on_pointer_event(PointerEvent.mouse_event(1, T.PRESS, 30, 25, button=BUTTON_LEFT))
    region.on_pointer_event(PointerEvent.mouse_event(1, T.RELEASE, 30, 25, button=BUTTON_LEFT))

    # pointer_input saw the press; clickable still emitted its click.
    assert presses == [1]
    assert clicks == [1]


def test_reapplying_reconfigures_single_node() -> None:
    region = InteractionRegion(_make_child())

    first = pointer_input(on_press=lambda e: None, capture=False)
    first.apply(region)
    second = pointer_input(on_press=lambda e: None, capture=True)
    second.apply(region)

    # Only one listener node exists; the second apply reconfigured it.
    nodes = [n for n in region._nodes if isinstance(n, PointerListenerNode)]
    assert len(nodes) == 1
    assert nodes[0]._capture is True


def test_factory_returns_modifier() -> None:
    assert isinstance(pointer_input(), PointerInputModifier)
