"""Control-character handling in EditableText (issue #307).

Enter delivered as ``on_text('\\r')`` (macOS Cocoa's ``insertNewline_`` path)
used to bypass the backend control-character filter and land a stray carriage
return in the value. The widget now strips control characters itself, on both
the ``on_text`` and IME composition paths.
"""

from nuiitivet.widgets.editable_text import EditableText


def test_handle_text_inserts_printable_character():
    w = EditableText()
    assert w._handle_text("a") is True
    assert w._state_internal.value.text == "a"


def test_handle_text_rejects_carriage_return():
    w = EditableText()
    for ch in "ab":
        w._handle_text(ch)

    # Enter delivers '\r' on the macOS backend; it must not modify the value.
    assert w._handle_text("\r") is False
    assert w._state_internal.value.text == "ab"


def test_handle_text_rejects_tab():
    w = EditableText()
    w._handle_text("a")
    assert w._handle_text("\t") is False
    assert w._state_internal.value.text == "a"


def test_handle_text_strips_control_chars_from_mixed_string():
    w = EditableText()
    # A backend could deliver a multi-character payload containing controls.
    assert w._handle_text("a\rb") is True
    assert w._state_internal.value.text == "ab"


def test_handle_ime_composition_strips_control_chars():
    w = EditableText()
    w._handle_ime_composition("a\rb", 2, 0)
    assert w._state_internal.value.text == "ab"
