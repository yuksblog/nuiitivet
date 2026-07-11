"""``on_submit`` callback on EditableText (issue #318).

Pressing Enter in a single-line field confirms the text and fires ``on_submit``
with the current value. It must not modify the value (see #307) and must not
fire while an IME composition is in progress.
"""

from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.text_editing import TextRange


def test_enter_fires_on_submit_with_current_value():
    seen: list[str] = []
    w = EditableText(on_submit=seen.append)
    for ch in "hello":
        w._handle_text(ch)

    handled = w._handle_key("enter", 0)

    assert handled is True
    assert seen == ["hello"]


def test_enter_does_not_modify_value():
    w = EditableText(on_submit=lambda _: None)
    for ch in "ab":
        w._handle_text(ch)

    w._handle_key("enter", 0)

    # Enter confirms the text; it must never alter the value (issue #307).
    assert w._state_internal.value.text == "ab"


def test_enter_without_callback_is_not_consumed():
    w = EditableText()
    for ch in "ab":
        w._handle_text(ch)

    # No on_submit configured: Enter changes nothing and is left unhandled.
    assert w._handle_key("enter", 0) is False
    assert w._state_internal.value.text == "ab"


def test_on_submit_not_fired_during_ime_composition():
    seen: list[str] = []
    w = EditableText(on_submit=seen.append)
    w._handle_text("a")
    # Begin an IME composition so the value is marked as composing.
    w._handle_ime_composition("b", 0, 1)
    assert w._state_internal.value.is_composing is True

    handled = w._handle_key("enter", 0)

    assert handled is False
    assert seen == []


def test_on_submit_not_fired_when_enter_confirms_ime_composition():
    """The Enter that commits an IME composition must not submit.

    On macOS the commit is delivered as ``on_text`` (``insertText:``) *before*
    the confirming Enter's ``on_key_press`` arrives, so by the time
    ``_handle_key('enter')`` runs the composition is already cleared. The
    widget remembers the just-committed composition to tell this Enter apart
    from a genuine submit.
    """
    seen: list[str] = []
    w = EditableText(on_submit=seen.append)

    # Compose "にほんご" then convert to "日本語" (still composing).
    w._handle_ime_composition("にほんご", 4, 0)
    w._handle_ime_composition("日本語", 3, 0)
    assert w._state_internal.value.is_composing is True

    # Pressing Enter commits the candidate: the backend delivers the committed
    # text first, clearing the composition, and only then the Enter key event.
    w._handle_text("日本語")
    assert w._state_internal.value.is_composing is False
    handled = w._handle_key("enter", 0)

    assert handled is False
    assert seen == []
    assert w._state_internal.value.text == "日本語"


def test_submit_still_fires_on_enter_after_confirmed_ime_text():
    """A second, standalone Enter after a commit is a real submit."""
    seen: list[str] = []
    w = EditableText(on_submit=seen.append)

    w._handle_ime_composition("あ", 1, 0)
    w._handle_text("あ")  # commit
    w._handle_key("enter", 0)  # confirming Enter — suppressed
    assert seen == []

    # A subsequent Enter is not tied to any commit and should submit.
    handled = w._handle_key("enter", 0)
    assert handled is True
    assert seen == ["あ"]


def test_commit_marker_cleared_by_cursor_motion():
    """A commit not confirmed by Enter must not suppress a later Enter."""
    from nuiitivet.input.codes import TEXT_MOTION_LEFT

    seen: list[str] = []
    w = EditableText(on_submit=seen.append)

    w._handle_ime_composition("あ", 1, 0)
    w._handle_text("あ")  # composition committed by some non-Enter action

    # Moving the cursor ends the input burst; a later Enter is a real submit.
    w._handle_text_motion(TEXT_MOTION_LEFT)
    handled = w._handle_key("enter", 0)

    assert handled is True
    assert seen == ["あ"]


def test_commit_marker_cleared_by_focus_change():
    from nuiitivet.widgets.interaction import FocusSource

    seen: list[str] = []
    w = EditableText(on_submit=seen.append)

    w._handle_ime_composition("あ", 1, 0)
    w._handle_text("あ")  # committed e.g. by clicking away

    w._handle_focus_change(False, FocusSource.POINTER)
    w._handle_focus_change(True, FocusSource.POINTER)
    handled = w._handle_key("enter", 0)

    assert handled is True
    assert seen == ["あ"]


def test_plain_typing_does_not_set_commit_marker():
    seen: list[str] = []
    w = EditableText(on_submit=seen.append)

    # Ordinary (non-IME) typing never marks a pending commit.
    for ch in "abc":
        w._handle_text(ch)
    handled = w._handle_key("enter", 0)

    assert handled is True
    assert seen == ["abc"]


def test_on_submit_reports_latest_value():
    seen: list[str] = []
    w = EditableText(on_submit=seen.append)
    w._handle_text("x")
    w._handle_key("enter", 0)
    w._handle_text("y")
    w._handle_key("enter", 0)

    assert seen == ["x", "xy"]


def test_on_submit_exception_is_swallowed():
    def boom(_value: str) -> None:
        raise RuntimeError("nope")

    w = EditableText(on_submit=boom)
    w._handle_text("a")

    # A raising callback must not propagate out of the key handler.
    assert w._handle_key("enter", 0) is True
    assert w._state_internal.value.text == "a"


def test_selection_unchanged_after_submit():
    w = EditableText(on_submit=lambda _: None)
    for ch in "abc":
        w._handle_text(ch)
    w._state_internal.value = w._state_internal.value.copy_with(selection=TextRange(1, 1))

    w._handle_key("enter", 0)

    assert w._state_internal.value.selection == TextRange(1, 1)
