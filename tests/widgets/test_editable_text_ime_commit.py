"""Committing and cancelling IME compositions on EditableText (issue #625).

``_commit_composition`` is reached through the focus node when the window
loses the OS focus: the provisional text is kept as committed text, matching
what native fields do. An empty composition update ends the composition
instead of leaving an empty-but-active composing range behind.
"""

from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.text_editing import TextRange


def test_commit_keeps_text_and_ends_composition():
    seen: list[str] = []
    w = EditableText(on_change=seen.append)
    w._handle_ime_composition("にほん", 3, 0)
    assert w._state_internal.value.is_composing is True
    assert seen == []  # held back while composing

    assert w._commit_composition() is True

    value = w._state_internal.value
    assert value.text == "にほん"
    assert value.is_composing is False
    # Ending the composition is the moment the application first sees the text.
    assert seen == ["にほん"]


def test_commit_without_composition_is_a_no_op():
    seen: list[str] = []
    w = EditableText(on_change=seen.append)
    w._handle_text("a")

    assert w._commit_composition() is False
    assert w._state_internal.value.text == "a"


def test_enter_after_commit_is_a_genuine_submit():
    """A focus-loss commit must not leave a marker that eats the next Enter."""
    seen: list[str] = []
    w = EditableText(on_submit=seen.append)
    w._handle_ime_composition("あ", 1, 0)
    w._commit_composition()

    assert w._handle_key("enter", 0) is True
    assert seen == ["あ"]


def test_empty_composition_update_cancels():
    w = EditableText()
    w._handle_text("x")
    w._handle_ime_composition("あい", 2, 0)

    handled = w._handle_ime_composition("", 0, 0)

    assert handled is True
    value = w._state_internal.value
    assert value.text == "x"
    assert value.is_composing is False
    assert value.selection == TextRange(1, 1)


def test_empty_composition_update_without_composition_is_ignored():
    """A stray end-of-composition echo must not open an empty composing range."""
    w = EditableText()
    w._handle_text("x")

    handled = w._handle_ime_composition("", 0, 0)

    assert handled is False
    value = w._state_internal.value
    assert value.text == "x"
    assert value.is_composing is False
