"""Tests for the message handling of the Windows IME hook.

The hook is an IMM32 application that draws the composition itself: while a
text input is the window's caret source it keeps the composition messages from
the OS and places the IME's windows at the caret. ``process_message`` holds
that decision apart from the window procedure, so it runs here against a fake
IMM32 on any platform. A live IME needs a manual pass on Windows.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

import pytest

from nuiitivet.backends.pyglet.ime import windows as ime_windows
from nuiitivet.backends.pyglet.ime.windows import (
    CFS_EXCLUDE,
    CFS_FORCE_POSITION,
    CFS_POINT,
    GCS_COMPSTR,
    GCS_CURSORPOS,
    GCS_RESULTSTR,
    ISC_SHOWUICOMPOSITIONWINDOW,
    WM_IME_COMPOSITION,
    WM_IME_ENDCOMPOSITION,
    WM_IME_SETCONTEXT,
    WM_IME_STARTCOMPOSITION,
    process_message,
)
from nuiitivet.platform.ime import IMEManager
from nuiitivet.widgets.editable_text import EditableText

HWND = 0x1234
HIMC = 0x55
CARET = (100.0, 300.0, 2.0, 20.0)


class _FakeImm:
    """An IMM32 stand-in holding one composition and recording where the IME's windows were put."""

    def __init__(self, composition: str = "", result: str = "", cursor: int = 0, himc: int = HIMC) -> None:
        self._strings = {GCS_COMPSTR: composition, GCS_RESULTSTR: result}
        self._cursor = cursor
        self._himc = himc
        self.released: list[tuple[int, int]] = []
        self.composition_window: Optional[tuple[int, tuple[int, int]]] = None
        self.candidate_window: Optional[tuple[int, int, tuple[int, int], tuple[int, int, int, int]]] = None

    def ImmGetContext(self, hwnd: int) -> int:
        return self._himc

    def ImmReleaseContext(self, hwnd: int, himc: int) -> int:
        self.released.append((hwnd, himc))
        return 1

    def ImmGetCompositionStringW(self, himc: int, flag: int, buf: Any, size: int) -> int:
        if flag == GCS_CURSORPOS:
            return self._cursor
        text = self._strings[flag]
        if buf is not None:
            buf.value = text
        return len(text.encode("utf-16-le"))

    def ImmSetCompositionWindow(self, himc: int, form: Any) -> int:
        f = form._obj
        self.composition_window = (f.dwStyle, (f.ptCurrentPos.x, f.ptCurrentPos.y))
        return 1

    def ImmSetCandidateWindow(self, himc: int, form: Any) -> int:
        f = form._obj
        area = (f.rcArea.left, f.rcArea.top, f.rcArea.right, f.rcArea.bottom)
        self.candidate_window = (f.dwIndex, f.dwStyle, (f.ptCurrentPos.x, f.ptCurrentPos.y), area)
        return 1


class _PygletWindow:
    def __init__(self) -> None:
        self.events: list[tuple[Any, ...]] = []

    def dispatch_event(self, *event: Any) -> None:
        self.events.append(event)


def _win(*, focused: bool, pixel_ratio: float = 1.0) -> Any:
    ime = IMEManager()
    if focused:
        ime.set_cursor_source(lambda: CARET)
    return SimpleNamespace(ime=ime, pixel_ratio=pixel_ratio)


def _send(imm: _FakeImm, window: Any, win: Any, msg: int, lparam: int = 0) -> tuple[bool, int]:
    return process_message(imm, HWND, window, win, msg, lparam)


def test_the_os_is_told_not_to_show_its_composition_box() -> None:
    candidates = 0x0000000F
    window = _PygletWindow()

    forward, lparam = _send(
        _FakeImm(), window, _win(focused=True), WM_IME_SETCONTEXT, ISC_SHOWUICOMPOSITIONWINDOW | candidates
    )

    assert forward is True
    assert lparam == candidates, "the candidate window flags stay"


def test_a_composition_in_a_focused_field_is_kept_from_the_os() -> None:
    imm = _FakeImm(composition="にほん", cursor=3)
    window = _PygletWindow()
    win = _win(focused=True)

    started, _ = _send(imm, window, win, WM_IME_STARTCOMPOSITION)
    composed, _ = _send(imm, window, win, WM_IME_COMPOSITION, GCS_COMPSTR | GCS_CURSORPOS)

    assert (started, composed) == (False, False), "forwarded, the OS would draw its floating box"
    assert window.events == [("on_ime_composition", "にほん", 3, 0)]


@pytest.mark.parametrize("msg", [WM_IME_STARTCOMPOSITION, WM_IME_COMPOSITION])
@pytest.mark.parametrize(
    ("pixel_ratio", "left", "top", "right", "bottom"),
    [(1.0, 100, 300, 102, 320), (1.5, 150, 450, 153, 480)],
)
def test_the_ime_windows_sit_at_the_caret_in_client_pixels(
    msg: int, pixel_ratio: float, left: int, top: int, right: int, bottom: int
) -> None:
    imm = _FakeImm(composition="に")

    _send(imm, _PygletWindow(), _win(focused=True, pixel_ratio=pixel_ratio), msg, GCS_COMPSTR)

    assert imm.composition_window == (CFS_POINT | CFS_FORCE_POSITION, (left, top))
    assert imm.candidate_window == (0, CFS_EXCLUDE, (left, top), (left, top, right, bottom))


def test_a_commit_arrives_once_as_text() -> None:
    imm = _FakeImm(result="日本語")
    window = _PygletWindow()

    forward, _ = _send(imm, window, _win(focused=True), WM_IME_COMPOSITION, GCS_RESULTSTR)

    assert window.events == [("on_ime_composition", "", 0, 0), ("on_text", "日本語")]
    assert forward is False, "forwarded, the OS would deliver the same text again as WM_CHAR"


def test_a_commit_outside_the_basic_plane_arrives_whole() -> None:
    imm = _FakeImm(result="𠮷野家")
    window = _PygletWindow()

    _send(imm, window, _win(focused=True), WM_IME_COMPOSITION, GCS_RESULTSTR)

    assert window.events[-1] == ("on_text", "𠮷野家")


def test_a_commit_that_leaves_a_clause_composing_inserts_the_text_first() -> None:
    imm = _FakeImm(composition="ご", result="日本", cursor=1)
    window = _PygletWindow()

    _send(imm, window, _win(focused=True), WM_IME_COMPOSITION, GCS_RESULTSTR | GCS_COMPSTR | GCS_CURSORPOS)

    assert window.events[-2:] == [("on_text", "日本"), ("on_ime_composition", "ご", 1, 0)]


class _FieldWindow:
    """A pyglet window stand-in that hands the text events to one field, as the runner does."""

    def __init__(self, field: EditableText) -> None:
        self._field = field

    def dispatch_event(self, event: str, *args: Any) -> None:
        if event == "on_text":
            self._field._handle_text(*args)
        else:
            self._field._handle_ime_composition(*args)


def test_the_enter_after_a_commit_submits() -> None:
    """Windows sends the key that confirms before the commit, so the next Enter is the user's own."""
    submitted: list[str] = []
    changed: list[str] = []
    field = EditableText(on_submit=submitted.append, on_change=changed.append)
    window, win = _FieldWindow(field), _win(focused=True)

    _send(_FakeImm(composition="にほん", cursor=3), window, win, WM_IME_COMPOSITION, GCS_COMPSTR | GCS_CURSORPOS)
    _send(_FakeImm(result="日本"), window, win, WM_IME_COMPOSITION, GCS_RESULTSTR)
    _send(_FakeImm(), window, win, WM_IME_ENDCOMPOSITION)

    assert field._handle_key("enter", 0) is True
    assert submitted == ["日本"] and changed == ["日本"]


def test_the_end_of_a_composition_clears_what_the_field_shows() -> None:
    window = _PygletWindow()

    forward, _ = _send(_FakeImm(), window, _win(focused=True), WM_IME_ENDCOMPOSITION)

    assert window.events == [("on_ime_composition", "", 0, 0)], "a cancelled composition must not stay underlined"
    assert forward is True


def test_without_a_focused_field_the_os_handles_the_composition() -> None:
    imm = _FakeImm(composition="に", result="日本語")
    window = _PygletWindow()
    win = _win(focused=False)

    forwards = [
        _send(imm, window, win, WM_IME_STARTCOMPOSITION)[0],
        _send(imm, window, win, WM_IME_COMPOSITION, GCS_COMPSTR)[0],
        _send(imm, window, win, WM_IME_COMPOSITION, GCS_RESULTSTR)[0],
        _send(imm, window, win, WM_IME_ENDCOMPOSITION)[0],
    ]

    assert forwards == [True, True, True, True]
    assert ("on_text", "日本語") not in window.events, "the OS delivers the commit as WM_CHAR"
    assert imm.composition_window is None and imm.candidate_window is None


def test_the_input_context_is_released_after_each_message() -> None:
    imm = _FakeImm(composition="に")
    win = _win(focused=True)

    _send(imm, _PygletWindow(), win, WM_IME_STARTCOMPOSITION)
    _send(imm, _PygletWindow(), win, WM_IME_COMPOSITION, GCS_COMPSTR)

    assert imm.released == [(HWND, HIMC), (HWND, HIMC)]


def test_a_window_without_an_input_context_leaves_the_message_to_the_os() -> None:
    imm = _FakeImm(result="日本語", himc=0)
    window = _PygletWindow()

    forward, _ = _send(imm, window, _win(focused=True), WM_IME_COMPOSITION, GCS_RESULTSTR)

    assert forward is True, "kept, the commit would reach nobody"
    assert window.events == [] and imm.released == []


def test_a_caret_that_cannot_be_read_does_not_deliver_the_commit_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_caret() -> tuple[float, float, float, float]:
        raise RuntimeError("boom")

    monkeypatch.setattr(ime_windows, "exception_once", lambda *args, **kwargs: None)
    imm = _FakeImm(result="日本語")
    window = _PygletWindow()
    win = _win(focused=True)
    win.ime.set_cursor_source(no_caret)

    forward, _ = _send(imm, window, win, WM_IME_COMPOSITION, GCS_RESULTSTR)

    assert window.events[-1] == ("on_text", "日本語")
    assert forward is False, "forwarded, the OS would deliver the same text again as WM_CHAR"


def test_a_handler_that_raises_does_not_break_the_message(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Raising(_PygletWindow):
        def dispatch_event(self, *event: Any) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(ime_windows, "exception_once", lambda *args, **kwargs: None)
    imm = _FakeImm(composition="に")

    forward, _ = _send(imm, _Raising(), _win(focused=True), WM_IME_COMPOSITION, GCS_COMPSTR)

    assert forward is False and imm.released == [(HWND, HIMC)]
