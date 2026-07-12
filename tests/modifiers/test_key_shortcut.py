"""Tests for the ``key_shortcut()`` modifier and its dispatch tier (issue #327).

Covers the node wiring (attach, compose, re-apply) and the focus-scoped dispatch
rules: a binding fires only while its subtree contains the focused node, the
innermost enclosing subtree wins, and the focused widget gets first refusal on
every key.
"""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.input.codes import MOD_ACCEL, MOD_SHIFT, accel_mask
from nuiitivet.input.shortcut import Shortcut
from nuiitivet.layout.column import Column
from nuiitivet.modifiers.key_shortcut import key_shortcut
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.app import App
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import FocusNode, InteractionRegion, PointerInputNode, ShortcutNode


def _focusable_box(**kwargs) -> InteractionRegion:
    box = Box(width=Sizing.fixed(100), height=Sizing.fixed(50)).modifier(nv.focusable(**kwargs))
    assert isinstance(box, InteractionRegion)
    return box


def _focus(app: App, region: InteractionRegion) -> None:
    node = region.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    app.request_focus(node)


def test_exported_from_modifiers_and_root() -> None:
    from nuiitivet.modifiers import key_shortcut as from_modifiers

    assert nv.key_shortcut is from_modifiers


def test_attaches_shortcut_node_and_accepts_a_spec_string() -> None:
    wrapped = _focusable_box().modifier(key_shortcut("Accel+D", on_trigger=lambda: None))
    assert isinstance(wrapped, InteractionRegion)

    node = wrapped.get_node(ShortcutNode)
    assert isinstance(node, ShortcutNode)
    assert [b.shortcut for b in node.bindings] == [Shortcut("d", MOD_ACCEL)]


def test_composes_without_clobbering_neighbouring_modifiers() -> None:
    clicks: list[int] = []
    wrapped = (
        _focusable_box()
        .modifier(nv.clickable(on_click=lambda: clicks.append(1)))
        .modifier(key_shortcut("Accel+D", on_trigger=lambda: None))
        .modifier(key_shortcut("Accel+Shift+D", on_trigger=lambda: None))
    )
    assert isinstance(wrapped, InteractionRegion)

    node = wrapped.get_node(ShortcutNode)
    assert isinstance(node, ShortcutNode)

    # Both gestures live on the one node, and the click wiring survived.
    assert {b.shortcut for b in node.bindings} == {
        Shortcut("d", MOD_ACCEL),
        Shortcut("d", MOD_ACCEL | MOD_SHIFT),
    }
    assert isinstance(wrapped.get_node(PointerInputNode), PointerInputNode)
    assert isinstance(wrapped.get_node(FocusNode), FocusNode)


def test_reapplying_the_same_gesture_replaces_rather_than_stacks() -> None:
    fired: list[str] = []
    box = _focusable_box()
    box.modifier(key_shortcut("Accel+D", on_trigger=lambda: fired.append("old")))
    wrapped = box.modifier(key_shortcut("Accel+D", on_trigger=lambda: fired.append("new")))
    assert isinstance(wrapped, InteractionRegion)

    node = wrapped.get_node(ShortcutNode)
    assert isinstance(node, ShortcutNode)
    assert len(node.bindings) == 1

    node.handle_shortcut("d", accel_mask())
    assert fired == ["new"]


def test_fires_only_while_the_subtree_contains_focus() -> None:
    saved: list[str] = []
    inside = _focusable_box()
    outside = _focusable_box()
    pane = Column([inside]).modifier(key_shortcut("Accel+S", on_trigger=lambda: saved.append("pane")))
    app = App(Column([pane, outside]))

    # Nothing focused yet: the binding is unreachable.
    assert app._dispatch_key_press("s", accel_mask()) is False
    assert saved == []

    _focus(app, inside)
    assert app._dispatch_key_press("s", accel_mask()) is True
    assert saved == ["pane"]

    # Focus moved out of the subtree: the binding no longer fires.
    _focus(app, outside)
    assert app._dispatch_key_press("s", accel_mask()) is False
    assert saved == ["pane"]


def test_multi_document_routing_saves_only_the_focused_pane() -> None:
    saved: list[str] = []
    editor_a = _focusable_box()
    editor_b = _focusable_box()
    pane_a = Column([editor_a]).modifier(key_shortcut("Accel+S", on_trigger=lambda: saved.append("a")))
    pane_b = Column([editor_b]).modifier(key_shortcut("Accel+S", on_trigger=lambda: saved.append("b")))
    app = App(Column([pane_a, pane_b]))

    _focus(app, editor_a)
    app._dispatch_key_press("s", accel_mask())
    assert saved == ["a"]

    _focus(app, editor_b)
    app._dispatch_key_press("s", accel_mask())
    assert saved == ["a", "b"]


def test_innermost_binding_wins_and_outer_does_not_also_fire() -> None:
    fired: list[str] = []
    leaf = _focusable_box()
    inner = Column([leaf]).modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("inner")))
    outer = Column([inner]).modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("outer")))
    app = App(outer)

    _focus(app, leaf)
    assert app._dispatch_key_press("s", accel_mask()) is True
    assert fired == ["inner"]


def test_focused_widget_gets_first_refusal() -> None:
    fired: list[str] = []
    keys: list[str] = []

    # A focused text-field-like widget that consumes every bare key.
    def on_key(key: str, modifier_keys: int) -> bool:
        keys.append(key)
        return modifier_keys == 0

    field = _focusable_box(on_key=on_key)
    pane = Column([field]).modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("save")))
    app = App(pane)
    _focus(app, field)

    # A bare "s" is eaten by the field; the shortcut tier is never reached.
    assert app._dispatch_key_press("s", 0) is True
    assert fired == []

    # Accel+S is declined by the field and falls through to the shortcut.
    assert app._dispatch_key_press("s", accel_mask()) is True
    assert fired == ["save"]


def test_handler_exception_is_contained() -> None:
    def boom() -> None:
        raise RuntimeError("shortcut handler blew up")

    leaf = _focusable_box()
    pane = Column([leaf]).modifier(key_shortcut("Accel+S", on_trigger=boom))
    app = App(pane)
    _focus(app, leaf)

    # Consumed (a binding matched) and the exception does not escape dispatch.
    assert app._dispatch_key_press("s", accel_mask()) is True
