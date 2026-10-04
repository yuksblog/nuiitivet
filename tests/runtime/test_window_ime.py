"""Per-window IME state and the focus-loss composition commit.

Each ``Window`` owns its own ``IMEManager`` — two windows never share
candidate-window geometry — and losing the OS focus commits a pending
composition on the focused field, so typing in the newly focused window
starts clean. Real-IME behavior (candidate window placement, mid-composition
window switches under a live input method) needs a manual pass on macOS;
what runs here is the model side.
"""

from __future__ import annotations

from nuiitivet.layout.container import Container
from nuiitivet.platform.ime import IMEManager
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.interaction import FocusNode, InteractionRegion
from nuiitivet.modifiers.focus import focusable
from nuiitivet.rendering.sizing import Sizing


def _focus(window: Window, field: EditableText) -> None:
    node = field.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    window.request_focus(node)


def test_each_window_owns_its_own_ime_state() -> None:
    a = Window(content=Container())
    b = Window(content=Container())

    assert isinstance(a.ime, IMEManager)
    assert a.ime is not b.ime

    a.ime.update_cursor_rect(10, 20, 2, 16)
    a.ime.update_window_info(100, 200, 640, 480)

    assert (b.ime.cursor_rect.x, b.ime.cursor_rect.y) == (0, 0)
    assert b.ime.window_location == (0, 0)
    assert a.ime.window_location == (100, 200)


def test_a_cursor_source_is_asked_on_every_read() -> None:
    ime = IMEManager()
    caret = [(10.0, 20.0, 2.0, 16.0)]
    ime.set_cursor_source(lambda: caret[0])

    assert (ime.cursor_rect.x, ime.cursor_rect.y) == (10.0, 20.0)
    caret[0] = (10.0, 5.0, 2.0, 16.0)
    assert ime.cursor_rect.y == 5.0


def test_a_published_rect_replaces_the_source() -> None:
    ime = IMEManager()
    ime.set_cursor_source(lambda: (10.0, 20.0, 2.0, 16.0))

    ime.update_cursor_rect(1, 2, 3, 4)

    assert (ime.cursor_rect.x, ime.cursor_rect.y) == (1, 2)


def test_the_focused_field_is_the_cursor_source_until_it_loses_focus() -> None:
    field = EditableText()
    other = EditableText()
    window = App(Window(content=field)).main_window

    _focus(window, field)
    assert window.ime._cursor_source == field._ime_caret_rect

    # A field that never held the source cannot take it away.
    window.ime.clear_cursor_source(other._ime_caret_rect)
    assert window.ime._cursor_source == field._ime_caret_rect

    window.request_focus(None)
    assert window.ime._cursor_source is None


def test_os_focus_loss_commits_pending_composition() -> None:
    field = EditableText()
    window = App(Window(content=field)).main_window
    _focus(window, field)
    window._set_os_active(True)

    window._dispatch_ime_composition("にほん", 3, 0)
    assert field._state_internal.value.is_composing is True

    window._set_os_active(False)

    value = field._state_internal.value
    assert value.text == "にほん"
    assert value.is_composing is False


def test_os_focus_loss_without_composition_changes_nothing() -> None:
    field = EditableText()
    window = App(Window(content=field)).main_window
    _focus(window, field)
    window._set_os_active(True)
    window._dispatch_text("a")

    window._set_os_active(False)

    assert field._state_internal.value.text == "a"


def test_os_focus_loss_is_safe_without_a_text_focus() -> None:
    # A focused node with no IME-commit handler, and no focused node at all:
    # neither may raise.
    box = Box(width=Sizing.fixed(50), height=Sizing.fixed(50)).modifier(focusable())
    assert isinstance(box, InteractionRegion)
    window = App(Window(content=box)).main_window
    node = box.get_node(FocusNode)
    assert isinstance(node, FocusNode)
    window.request_focus(node)
    window._set_os_active(True)
    window._set_os_active(False)

    window._set_os_active(True)
    window.request_focus(None)
    window._set_os_active(False)
