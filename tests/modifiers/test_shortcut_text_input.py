"""Text input withholds the keys it types from the shortcut tier (issue #331).

A text field consumes characters through the ``on_text`` route, not ``on_key``,
so it declines printable keys on the route the dispatcher watches. Taking that
"declined" at face value let a bare-letter ``key_shortcut`` fire while the user
was typing into a field — the letter was inserted *and* the command ran.

The dispatcher therefore asks two questions before offering a key to the
bindings: does the focused chain take text at all, and is this a key text input
may claim. Both must hold for the key to be withheld.
"""

from __future__ import annotations

import nuiitivet as nv
import nuiitivet.material as mv
from nuiitivet.input.codes import MOD_ALT, MOD_CTRL, MOD_SHIFT, accel_mask
from nuiitivet.layout.column import Column
from nuiitivet.modifiers.key_shortcut import key_shortcut
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.app import App
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.interaction import FocusNode, InteractionRegion


def _box() -> Box:
    return Box(width=Sizing.fixed(100), height=Sizing.fixed(50))


def _plain_focusable() -> InteractionRegion:
    box = _box().modifier(nv.focusable())
    assert isinstance(box, InteractionRegion)
    return box


def _focus(app: App, region: InteractionRegion) -> None:
    node = region.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    app.request_focus(node)


def _focus_widget(app: App, field: EditableText) -> None:
    node = field.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    app.request_focus(node)


def _focus_material_field(app: App, field: mv.TextField) -> None:
    # The focus subject of a Material TextField is the EditableText it hosts.
    node = field._editable.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    app.request_focus(node)


def _type(app: App, text: str, modifier_keys: int = 0) -> None:
    """Drive a keystroke the way a backend does: the key press, then the text."""
    for ch in text:
        app._dispatch_key_press(ch.lower(), modifier_keys)
        app._dispatch_text(ch)


def test_bare_letter_shortcut_is_withheld_while_a_field_has_focus() -> None:
    fired: list[str] = []
    canvas = _box().modifier(key_shortcut("b", on_trigger=lambda: fired.append("brush")))
    field = EditableText()
    app = App(Column([canvas, field]))

    _focus_widget(app, field)
    _type(app, "brush")

    assert field.value == "brush"
    assert fired == []


def test_shift_letter_shortcut_is_withheld_too() -> None:
    # Shift is not a "command" modifier: Shift+B still types the character "B".
    fired: list[str] = []
    canvas = _box().modifier(key_shortcut("Shift+B", on_trigger=lambda: fired.append("brush")))
    field = EditableText()
    app = App(Column([canvas, field]))

    _focus_widget(app, field)
    _type(app, "B", MOD_SHIFT)

    assert field.value == "B"
    assert fired == []


def test_bare_letter_shortcut_fires_with_nothing_focused() -> None:
    fired: list[str] = []
    canvas = _box().modifier(key_shortcut("b", on_trigger=lambda: fired.append("brush")))
    app = App(Column([canvas, EditableText()]))

    assert app._focused_node is None
    assert app._dispatch_key_press("b", 0) is True
    assert fired == ["brush"]


def test_bare_letter_shortcut_fires_while_a_non_text_widget_has_focus() -> None:
    # Focus alone must not suppress the shortcut — only focus on something that
    # actually takes text does.
    fired: list[str] = []
    canvas = _box().modifier(key_shortcut("b", on_trigger=lambda: fired.append("brush")))
    other = _plain_focusable()
    app = App(Column([canvas, other]))

    _focus(app, other)
    assert app._dispatch_key_press("b", 0) is True
    assert fired == ["brush"]


def test_accel_shortcut_still_reaches_the_tier_through_a_focused_field() -> None:
    # Ctrl/Cmd produce no text, so the field genuinely does not want the key.
    saved: list[str] = []
    canvas = _box().modifier(key_shortcut("Accel+S", on_trigger=lambda: saved.append("save")))
    field = EditableText()
    app = App(Column([canvas, field]))

    _focus_widget(app, field)

    assert app._dispatch_key_press("s", accel_mask()) is True
    assert saved == ["save"]
    assert field.value == ""


def test_function_key_shortcut_still_reaches_the_tier_through_a_focused_field() -> None:
    fired: list[str] = []
    canvas = _box().modifier(key_shortcut("F5", on_trigger=lambda: fired.append("refresh")))
    field = EditableText()
    app = App(Column([canvas, field]))

    _focus_widget(app, field)
    assert app._dispatch_key_press("f5", 0) is True
    assert fired == ["refresh"]


def test_field_keeps_owning_its_editing_combos() -> None:
    # Accel+A is the field's own "select all"; the shortcut tier must never see
    # it, and binding it elsewhere must not steal it from the field.
    fired: list[str] = []
    canvas = _box().modifier(key_shortcut("Accel+A", on_trigger=lambda: fired.append("all")))
    field = EditableText()
    app = App(Column([canvas, field]))

    _focus_widget(app, field)
    _type(app, "ab")

    assert app._dispatch_key_press("a", accel_mask()) is True
    assert fired == []  # tier 2 consumed it; the binding never ran


def test_alt_shortcut_is_withheld_while_a_field_has_focus() -> None:
    # The documented cost of the conservative rule: Alt cannot be ruled out as
    # non-text (macOS Option types characters; Windows/X11 spell AltGr as
    # Ctrl+Alt), so Alt gestures are unavailable while a field holds focus.
    fired: list[str] = []
    canvas = _box().modifier(key_shortcut("Alt+B", on_trigger=lambda: fired.append("brush")))
    field = EditableText()
    app = App(Column([canvas, field]))

    _focus_widget(app, field)
    app._dispatch_key_press("b", MOD_ALT)
    assert fired == []

    # With nothing focused it fires as usual.
    app.request_focus(None)
    app._dispatch_key_press("b", MOD_ALT)
    assert fired == ["brush"]


def test_altgr_spelling_is_withheld_while_a_field_has_focus() -> None:
    # Windows and X11 report AltGr as Ctrl+Alt, and a German layout turns
    # AltGr+Q into "@" — so even a Ctrl-bearing gesture can be text.
    fired: list[str] = []
    canvas = _box().modifier(key_shortcut("Ctrl+Alt+Q", on_trigger=lambda: fired.append("q")))
    field = EditableText()
    app = App(Column([canvas, field]))

    _focus_widget(app, field)
    app._dispatch_key_press("q", MOD_CTRL | MOD_ALT)
    assert fired == []


def test_text_field_without_on_submit_lets_enter_reach_a_shortcut() -> None:
    # Enter is not text, so it is not withheld — but a field that *uses* it still
    # claims it in tier 2. A Material TextField only uses it when it has an
    # on_submit, and must not claim (and silently drop) it otherwise.
    fired: list[str] = []
    canvas = _box().modifier(key_shortcut("Enter", on_trigger=lambda: fired.append("default action")))
    field = mv.TextField()
    app = App(Column([canvas, field]))

    _focus_material_field(app, field)
    app._dispatch_key_press("enter", 0)

    assert fired == ["default action"]


def test_text_field_with_on_submit_keeps_enter_for_itself() -> None:
    fired: list[str] = []
    submitted: list[str] = []
    canvas = _box().modifier(key_shortcut("Enter", on_trigger=lambda: fired.append("default action")))
    field = mv.TextField(on_submit=submitted.append)
    app = App(Column([canvas, field]))

    _focus_material_field(app, field)
    _type(app, "hi")
    app._dispatch_key_press("enter", 0)

    assert submitted == ["hi"]
    assert fired == []  # the field consumed it in tier 2


def test_accepts_text_input_bubbles_to_an_ancestor() -> None:
    # A focused node that takes no text itself is still protected when an
    # ancestor consumes text: handle_text_event walks the same chain.
    child = FocusNode()
    parent = FocusNode(on_text=lambda text: True)
    child._parent = parent

    assert parent.accepts_text_input is True
    assert child.accepts_text_input is True
    assert FocusNode().accepts_text_input is False
