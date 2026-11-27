"""EditableText's ``A`` / ``C`` / ``X`` / ``V`` under each platform's accelerator.

On macOS Ctrl with a letter is a caret move the backend sends as a text
motion, so the key press of the same stroke must leave the field alone.
"""

from __future__ import annotations

import pytest

from nuiitivet.input.codes import MOD_CTRL, MOD_META
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.text_editing import TextEditingValue, TextRange


class _Clipboard:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text


def _field(monkeypatch: pytest.MonkeyPatch, platform: str, clipboard: _Clipboard) -> EditableText:
    """A field holding ``hello`` with ``ell`` selected, on *platform*."""
    monkeypatch.setattr("nuiitivet.widgets.editable_text.get_system_clipboard", lambda: clipboard)
    field = EditableText(value="hello")
    field._state_internal.value = TextEditingValue("hello", TextRange(1, 4))
    monkeypatch.setattr("sys.platform", platform)
    return field


@pytest.mark.parametrize("key", ["a", "c", "x", "v"])
def test_ctrl_with_a_shortcut_letter_leaves_the_field_alone_on_macos(monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    clipboard = _Clipboard("kept")
    field = _field(monkeypatch, "darwin", clipboard)

    assert field._handle_key(key, MOD_CTRL) is False

    assert field._state_internal.value == TextEditingValue("hello", TextRange(1, 4))
    assert clipboard.text == "kept"


@pytest.mark.parametrize(
    "platform, accel",
    [
        ("darwin", MOD_META),
        ("win32", MOD_CTRL),
        ("linux", MOD_CTRL),
        ("emscripten", MOD_CTRL),
        ("emscripten", MOD_META),
    ],
)
def test_the_accelerator_selects_all_copies_cuts_and_pastes(
    monkeypatch: pytest.MonkeyPatch, platform: str, accel: int
) -> None:
    clipboard = _Clipboard()
    field = _field(monkeypatch, platform, clipboard)

    assert field._handle_key("c", accel) is True
    assert clipboard.text == "ell"

    assert field._handle_key("a", accel) is True
    assert field._state_internal.value.selection == TextRange(0, 5)

    assert field._handle_key("x", accel) is True
    assert field.value == "" and clipboard.text == "hello"

    assert field._handle_key("v", accel) is True
    assert field.value == "hello"
