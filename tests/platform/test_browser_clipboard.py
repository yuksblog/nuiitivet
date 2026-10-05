"""Tests for the clipboard an app sees in a browser."""

import pytest

from nuiitivet.platform.clipboard import BrowserClipboard, get_system_clipboard
from nuiitivet.platform.ime import IMEManager


def test_copy_reaches_the_backend_and_stays_readable() -> None:
    clipboard = BrowserClipboard()
    copied: list[str] = []
    clipboard.on_copy = copied.append

    clipboard.set_text("abc")

    assert copied == ["abc"]
    assert clipboard.get_text() == "abc"


def test_pasted_text_is_read_without_being_copied_back() -> None:
    clipboard = BrowserClipboard()
    copied: list[str] = []
    clipboard.on_copy = copied.append

    clipboard.receive("from the browser")

    assert clipboard.get_text() == "from the browser"
    assert copied == []


def test_a_browser_app_keeps_one_clipboard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "emscripten")

    first = get_system_clipboard()
    first.set_text("kept")

    assert isinstance(first, BrowserClipboard)
    assert get_system_clipboard().get_text() == "kept"


def test_ime_reports_whether_a_field_registered_its_caret() -> None:
    ime = IMEManager()

    def source() -> tuple[float, float, float, float]:
        return (1.0, 2.0, 3.0, 4.0)

    assert not ime.has_cursor_source
    ime.set_cursor_source(source)
    assert ime.has_cursor_source
    ime.clear_cursor_source(source)
    assert not ime.has_cursor_source
