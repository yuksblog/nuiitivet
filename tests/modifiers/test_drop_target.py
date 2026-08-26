"""Tests for the ``drop_target()`` modifier (issue #599).

Covers the modifier's node wiring: it attaches a ``FileDropNode``, delivers
:class:`FileDropEvent` with widget-local coordinates, composes with
``clickable`` without either clobbering the other, and reconfigures (rather
than stacking) a second node when re-applied during recomposition.
"""

from __future__ import annotations

from pathlib import Path

import nuiitivet as nv
from nuiitivet.input.events import FileDropEvent
from nuiitivet.modifiers.drop_target import DropTargetModifier, drop_target
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import FileDropNode, InteractionRegion, PointerInputNode


def _make_child() -> Box:
    return Box(width=Sizing.fixed(100), height=Sizing.fixed(50))


def _drop(region: InteractionRegion, x: float, y: float, paths: tuple[Path, ...]) -> bool:
    region.set_last_rect(10, 20, 100, 50)
    return region.dispatch_file_drop_event(FileDropEvent(paths=paths, x=x, y=y))


def test_exported_from_modifiers_and_root() -> None:
    from nuiitivet.modifiers import drop_target as from_modifiers

    assert nv.drop_target is from_modifiers


def test_drop_target_attaches_file_drop_node() -> None:
    events: list[FileDropEvent] = []
    wrapped = _make_child().modifier(drop_target(on_drop=events.append))
    assert isinstance(wrapped, InteractionRegion)
    node = wrapped.get_node(FileDropNode)
    assert isinstance(node, FileDropNode)

    consumed = _drop(wrapped, 40, 45, (Path("/tmp/a.txt"), Path("/tmp/b.txt")))
    assert consumed is True
    assert len(events) == 1
    event = events[0]
    assert event.paths == (Path("/tmp/a.txt"), Path("/tmp/b.txt"))
    # last_rect is (10, 20); local coordinates are relative to the widget.
    assert (event.local_x, event.local_y) == (30.0, 25.0)
    assert (event.x, event.y) == (40.0, 45.0)


def test_composes_with_clickable_without_clobbering() -> None:
    drops, clicks = [], []
    wrapped = (
        _make_child()
        .modifier(drop_target(on_drop=lambda e: drops.append(1)))
        .modifier(nv.clickable(on_click=lambda: clicks.append(1)))
    )
    region = wrapped
    assert isinstance(region, InteractionRegion)
    assert isinstance(region.get_node(FileDropNode), FileDropNode)
    assert isinstance(region.get_node(PointerInputNode), PointerInputNode)

    assert _drop(region, 30, 25, (Path("/tmp/a.txt"),)) is True
    assert drops == [1]
    assert clicks == []


def test_reapplying_reconfigures_single_node() -> None:
    region = InteractionRegion(_make_child())

    first_drops: list[FileDropEvent] = []
    second_drops: list[FileDropEvent] = []
    DropTargetModifier(on_drop=first_drops.append).apply(region)
    DropTargetModifier(on_drop=second_drops.append).apply(region)

    # Only one drop node exists; the second apply reconfigured it.
    nodes = [n for n in region._nodes if isinstance(n, FileDropNode)]
    assert len(nodes) == 1

    _drop(region, 30, 25, (Path("/tmp/a.txt"),))
    assert first_drops == []
    assert len(second_drops) == 1


def test_disabled_region_rejects_drop() -> None:
    events: list[FileDropEvent] = []
    wrapped = _make_child().modifier(drop_target(on_drop=events.append))
    assert isinstance(wrapped, InteractionRegion)
    wrapped.state.disabled = True

    assert _drop(wrapped, 30, 25, (Path("/tmp/a.txt"),)) is False
    assert events == []


def test_no_callback_does_not_consume() -> None:
    wrapped = _make_child().modifier(drop_target())
    assert isinstance(wrapped, InteractionRegion)
    assert _drop(wrapped, 30, 25, (Path("/tmp/a.txt"),)) is False
