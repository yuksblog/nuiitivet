"""Observable binding on EditableText (issue #565).

An observable passed as ``value`` is the field's value cell, not a source it
mirrors: edits are written back to it, the same as for every other input
widget. A read-only observable has nowhere to write, so it displays only.
"""

from unittest.mock import MagicMock

from nuiitivet.observable import Observable
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.input_filter import digits_only
from nuiitivet.widgets.text_editing import TextRange


def _mounted(**kwargs) -> EditableText:
    w = EditableText(**kwargs)
    w.mount(MagicMock())
    return w


def test_typing_is_written_back_to_the_observable():
    obs = Observable("ab")
    w = _mounted(value=obs)

    w._handle_text("c")

    assert obs.value == "abc"


def test_a_programmatic_assignment_is_written_back_too():
    obs = Observable("ab")
    w = _mounted(value=obs)

    w.value = "xyz"

    assert obs.value == "xyz"


def test_a_read_only_source_is_never_written_to():
    source = Observable("ab")
    w = _mounted(value=source.map(lambda s: s.upper()))

    w._handle_text("!")

    assert w.value == "AB!"
    assert source.value == "ab"


def test_an_external_write_still_reaches_the_widget():
    obs = Observable("ab")
    w = _mounted(value=obs)

    obs.value = "xy"

    assert w.value == "xy"


def test_the_write_back_loop_terminates():
    obs = Observable("")
    seen: list[str] = []
    obs.subscribe(seen.append)
    w = _mounted(value=obs)

    w._handle_text("a")

    # One write out, one delivery back, and the delivery is a no-op because the
    # text it carries already matches.
    assert seen == ["a"]
    assert w.value == "a"


def test_an_external_write_keeps_the_caret_instead_of_moving_it_to_the_end():
    """Normalizing on write-back must not send the caret to the end."""
    obs = Observable("")
    # Upper-case whatever the field writes, as an app-side normalization would.
    obs.subscribe(lambda text: setattr(obs, "value", text.upper()))
    w = _mounted(value=obs)

    w._handle_text("a")
    w._handle_text("b")
    # Move into the middle of the text, then type there.
    w._state_internal.value = w._state_internal.value.copy_with(selection=TextRange(1, 1))
    w._handle_text("c")

    assert obs.value == "ACB"
    assert w.value == "ACB"
    assert w._state_internal.value.selection == TextRange(2, 2)


def test_a_caret_past_the_end_of_a_shorter_text_is_clamped():
    obs = Observable("abcdef")
    w = _mounted(value=obs)
    w._state_internal.value = w._state_internal.value.copy_with(selection=TextRange(6, 6))

    obs.value = "ab"

    assert w._state_internal.value.selection == TextRange(2, 2)


def test_nothing_is_written_back_while_an_ime_composition_is_active():
    """A half-converted composition is not a value the application should see."""
    obs = Observable("")
    w = _mounted(value=obs)

    w._handle_ime_composition("にほんご", 4, 0)

    assert w.value == "にほんご"
    assert obs.value == ""


def test_the_committed_composition_is_written_back():
    obs = Observable("")
    w = _mounted(value=obs)

    w._handle_ime_composition("にほんご", 4, 0)
    w._handle_ime_composition("日本語", 3, 0)
    w._handle_text("日本語")  # commit

    assert obs.value == "日本語"


def test_an_input_filter_runs_before_the_write_back():
    obs = Observable("")
    w = _mounted(value=obs, input_filter=digits_only())

    w._handle_text("1")
    w._handle_text("a")
    w._handle_text("2")

    # The observable never sees the rejected character, not even transiently.
    assert obs.value == "12"
    assert w.value == "12"


def test_a_failing_write_back_does_not_break_the_field():
    class _Hostile(Observable[str]):
        @property  # type: ignore[misc]
        def value(self) -> str:
            return ""

        @value.setter
        def value(self, _v: str) -> None:
            raise RuntimeError("nope")

    w = _mounted(value=_Hostile(""))

    w._handle_text("a")

    assert w.value == "a"


def test_an_unbound_field_still_edits():
    w = _mounted(value="ab")

    w._handle_text("c")

    assert w.value == "abc"
