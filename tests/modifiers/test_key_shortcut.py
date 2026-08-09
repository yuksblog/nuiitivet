"""Tests for the ``key_shortcut()`` modifier and its dispatch tiers (issue #327).

Covers the node wiring (attach, compose, re-apply) and the scope rules:
FOREGROUND (the default) fires without focus but not when the subtree is hidden,
covered by a route, or behind a blocking overlay; FOCUS fires only inside the
focused subtree; MOUNT fires even when occluded. Ambiguous FOREGROUND/MOUNT
matches fire nothing.
"""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.input.codes import MOD_ACCEL, MOD_SHIFT, accel_mask
from nuiitivet.input.shortcut import Shortcut, ShortcutScope
from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.layout.column import Column
from nuiitivet.layout.deck import Deck
from nuiitivet.modifiers.key_shortcut import key_shortcut
from nuiitivet.navigation import Route
from nuiitivet.observable import Observable
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.app import App
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.widgets.interaction import FocusNode, InteractionRegion, PointerInputNode, ShortcutNode


def _box() -> Box:
    return Box(width=Sizing.fixed(100), height=Sizing.fixed(50))


def _focusable_box(**kwargs) -> InteractionRegion:
    box = _box().modifier(nv.focusable(**kwargs))
    assert isinstance(box, InteractionRegion)
    return box


def _focus(app: App, region: InteractionRegion) -> None:
    node = region.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    app.request_focus(node)


def _press_accel_s(app: App) -> bool:
    return app._dispatch_key_press("s", accel_mask())


def test_exported_from_modifiers_and_root() -> None:
    from nuiitivet.modifiers import key_shortcut as from_modifiers

    assert nv.key_shortcut is from_modifiers
    assert nv.ShortcutScope is ShortcutScope


def test_attaches_shortcut_node_and_accepts_a_spec_string() -> None:
    wrapped = _box().modifier(key_shortcut("Accel+D", on_trigger=lambda: None))
    assert isinstance(wrapped, InteractionRegion)

    node = wrapped.get_node(ShortcutNode)
    assert isinstance(node, ShortcutNode)
    assert [b.shortcut for b in node.bindings] == [Shortcut("d", MOD_ACCEL)]
    assert node.bindings[0].scope is ShortcutScope.FOREGROUND


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

    # Both gestures live on the one node, and the click/focus wiring survived.
    assert {b.shortcut for b in node.bindings} == {
        Shortcut("d", MOD_ACCEL),
        Shortcut("d", MOD_ACCEL | MOD_SHIFT),
    }
    assert isinstance(wrapped.get_node(PointerInputNode), PointerInputNode)
    assert isinstance(wrapped.get_node(FocusNode), FocusNode)


def test_reapplying_the_same_gesture_replaces_rather_than_stacks() -> None:
    fired: list[str] = []
    box = _box()
    box.modifier(key_shortcut("Accel+D", on_trigger=lambda: fired.append("old")))
    wrapped = box.modifier(key_shortcut("Accel+D", on_trigger=lambda: fired.append("new")))
    assert isinstance(wrapped, InteractionRegion)

    node = wrapped.get_node(ShortcutNode)
    assert isinstance(node, ShortcutNode)
    assert len(node.bindings) == 1

    node.trigger(node.bindings[0])
    assert fired == ["new"]


# --- FOREGROUND (the default) -------------------------------------------------


def test_foreground_fires_with_nothing_focused() -> None:
    # The paint-canvas case: no focus anywhere, the shortcut still fires.
    saved: list[str] = []
    canvas = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: saved.append("save")))
    app = App(Column([canvas]))

    assert app._focused_node is None
    assert _press_accel_s(app) is True
    assert saved == ["save"]


def test_foreground_fires_while_focus_is_elsewhere() -> None:
    saved: list[str] = []
    canvas = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: saved.append("save")))
    toolbar_field = _focusable_box()
    app = App(Column([canvas, toolbar_field]))

    _focus(app, toolbar_field)
    assert _press_accel_s(app) is True
    assert saved == ["save"]


def test_focused_widget_gets_first_refusal() -> None:
    fired: list[str] = []

    # A focused text-field-like widget that consumes every unmodified key.
    def on_key(key: str, modifier_keys: int) -> bool:
        return modifier_keys == 0

    field = _focusable_box(on_key=on_key)
    canvas = _box().modifier(key_shortcut("s", on_trigger=lambda: fired.append("brush")))
    app = App(Column([canvas, field]))
    _focus(app, field)

    # A bare "s" is eaten by the field; the shortcut tier is never reached.
    assert app._dispatch_key_press("s", 0) is True
    assert fired == []

    # With nothing focused, the same bare "s" reaches the shortcut.
    app.request_focus(None)
    assert app._dispatch_key_press("s", 0) is True
    assert fired == ["brush"]


def test_foreground_does_not_fire_when_hidden() -> None:
    saved: list[str] = []
    shown = Observable(True)
    panel = _box().modifier(
        key_shortcut("Accel+S", on_trigger=lambda: saved.append("save")) | nv.visible(shown)
    )
    app = App(Column([panel]))
    app.root.mount(app)  # the visibility condition is observed on mount

    assert _press_accel_s(app) is True
    assert saved == ["save"]

    shown.value = False
    assert _press_accel_s(app) is False
    assert saved == ["save"]


def test_foreground_does_not_fire_on_a_covered_route() -> None:
    # A covered route stays mounted, so without the displayed check the previous
    # screen's shortcuts would keep firing on the current one.
    saved: list[str] = []
    home = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: saved.append("home")))
    app = App(home)
    app.root.mount(app)

    assert _press_accel_s(app) is True
    assert saved == ["home"]

    app.navigator.push(Route(builder=_box))
    assert _press_accel_s(app) is False
    assert saved == ["home"]


def test_foreground_does_not_fire_behind_a_blocking_overlay() -> None:
    saved: list[str] = []
    home = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: saved.append("home")))
    app = App(home)
    app.root.mount(app)

    assert _press_accel_s(app) is True

    app.overlay.show(_box(), backdrop=True)
    assert _press_accel_s(app) is False
    assert saved == ["home"]


def test_a_shortcut_inside_the_modal_still_fires() -> None:
    fired: list[str] = []
    home = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("home")))
    app = App(home)
    app.root.mount(app)

    dialog = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("dialog")))
    app.overlay.show(dialog, backdrop=True)

    assert _press_accel_s(app) is True
    assert fired == ["dialog"]


def test_foreground_does_not_fire_on_a_hidden_deck_page() -> None:
    # A Deck keeps every page mounted; only the selected one is on screen, so only
    # its shortcuts are live. Same boundary Tab stops at (issue #491).
    fired: list[str] = []
    page0 = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("page0")))
    page1 = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("page1")))
    index = Observable(0)
    app = App(Column([Deck(children=[page0, page1], index=index)]))
    app.root.mount(app)

    assert _press_accel_s(app) is True
    assert fired == ["page0"]

    index.value = 1
    assert _press_accel_s(app) is True
    assert fired == ["page0", "page1"]


def test_foreground_does_not_fire_inside_a_closed_collapsible() -> None:
    fired: list[str] = []
    opened = Observable(True)
    panel = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("panel")))
    app = App(Column([Collapsible(panel, opened=opened)]))
    app.root.mount(app)

    assert _press_accel_s(app) is True
    assert fired == ["panel"]

    opened.value = False
    assert _press_accel_s(app) is False
    assert fired == ["panel"]


def test_foreground_does_not_fire_inside_a_disabled_clickable() -> None:
    fired: list[str] = []
    disabled = Observable(False)
    label = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("button")))
    app = App(Column([Clickable(label, disabled=disabled)]))
    app.root.mount(app)

    assert _press_accel_s(app) is True
    assert fired == ["button"]

    disabled.value = True
    assert _press_accel_s(app) is False
    assert fired == ["button"]


def test_ambiguous_foreground_match_fires_nothing() -> None:
    fired: list[str] = []
    a = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("a")))
    b = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("b")))
    app = App(Column([a, b]))

    assert _press_accel_s(app) is False
    assert fired == []


# --- FOCUS (opt-in) -----------------------------------------------------------


def _pane(child: InteractionRegion, on_trigger) -> InteractionRegion:
    pane = Column([child]).modifier(
        key_shortcut("Accel+S", on_trigger=on_trigger, scope=ShortcutScope.FOCUS)
    )
    assert isinstance(pane, InteractionRegion)
    return pane


def test_focus_scope_routes_to_the_focused_pane_only() -> None:
    # Two panes displayed at once, both binding the same gesture: only focus can
    # decide, and FOREGROUND would (rightly) call it ambiguous.
    saved: list[str] = []
    editor_a = _focusable_box()
    editor_b = _focusable_box()
    app = App(Column([_pane(editor_a, lambda: saved.append("a")), _pane(editor_b, lambda: saved.append("b"))]))

    _focus(app, editor_a)
    assert _press_accel_s(app) is True
    assert saved == ["a"]

    _focus(app, editor_b)
    assert _press_accel_s(app) is True
    assert saved == ["a", "b"]


def test_focus_scope_does_not_fire_when_focus_is_outside_or_absent() -> None:
    saved: list[str] = []
    inside = _focusable_box()
    outside = _focusable_box()
    app = App(Column([_pane(inside, lambda: saved.append("pane")), outside]))

    assert _press_accel_s(app) is False

    _focus(app, outside)
    assert _press_accel_s(app) is False

    _focus(app, inside)
    assert _press_accel_s(app) is True
    assert saved == ["pane"]


def test_focus_scope_innermost_wins() -> None:
    fired: list[str] = []
    leaf = _focusable_box()
    inner = _pane(leaf, lambda: fired.append("inner"))
    outer = Column([inner]).modifier(
        key_shortcut("Accel+S", on_trigger=lambda: fired.append("outer"), scope=ShortcutScope.FOCUS)
    )
    app = App(outer)

    _focus(app, leaf)
    assert _press_accel_s(app) is True
    assert fired == ["inner"]


def test_focus_scope_wins_over_foreground() -> None:
    # Narrowest scope first: whatever is closest to the user's attention.
    fired: list[str] = []
    leaf = _focusable_box()
    pane = _pane(leaf, lambda: fired.append("focus"))
    background = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("foreground")))
    app = App(Column([pane, background]))

    _focus(app, leaf)
    assert _press_accel_s(app) is True
    assert fired == ["focus"]


# --- MOUNT --------------------------------------------------------------------


def test_mount_scope_survives_navigation() -> None:
    # How an app-wide command is expressed: bound on the content root, which
    # stays mounted when a route covers it.
    quit_calls: list[str] = []
    home = _box().modifier(
        key_shortcut("Accel+Q", on_trigger=lambda: quit_calls.append("quit"), scope=ShortcutScope.MOUNT)
    )
    app = App(home)
    app.root.mount(app)

    assert app._dispatch_key_press("q", accel_mask()) is True

    app.navigator.push(Route(builder=_box))
    assert app._dispatch_key_press("q", accel_mask()) is True
    assert quit_calls == ["quit", "quit"]


def test_foreground_wins_over_mount() -> None:
    fired: list[str] = []
    app_wide = _box().modifier(
        key_shortcut("Accel+S", on_trigger=lambda: fired.append("mount"), scope=ShortcutScope.MOUNT)
    )
    panel = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: fired.append("foreground")))
    app = App(Column([app_wide, panel]))

    assert _press_accel_s(app) is True
    assert fired == ["foreground"]


def test_handler_exception_is_contained() -> None:
    def boom() -> None:
        raise RuntimeError("shortcut handler blew up")

    app = App(Column([_box().modifier(key_shortcut("Accel+S", on_trigger=boom))]))

    # Consumed (a binding matched) and the exception does not escape dispatch.
    assert _press_accel_s(app) is True
