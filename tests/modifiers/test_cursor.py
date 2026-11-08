"""Tests for the ``cursor()`` modifier and the cursor each host answers from its role."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.input.cursor import MouseCursor
from nuiitivet.material.buttons import Button, IconButton
from nuiitivet.material.text_fields import TextField
from nuiitivet.modifiers.cursor import CursorModifier, cursor
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.interaction import InteractionRegion
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgets.text_field import TextFieldBase


def test_exported_from_modifiers_and_root() -> None:
    from nuiitivet.modifiers import cursor as from_modifiers

    assert nv.cursor is from_modifiers
    assert nv.MouseCursor is MouseCursor


def test_wraps_a_plain_widget_in_one_region() -> None:
    wrapped = Box(width=Sizing.fixed(100), height=Sizing.fixed(50)).modifier(cursor(MouseCursor.CROSSHAIR))
    assert isinstance(wrapped, InteractionRegion)
    assert wrapped.mouse_cursor is MouseCursor.CROSSHAIR

    again = wrapped.modifier(cursor(MouseCursor.TEXT))
    assert again is wrapped
    assert wrapped.mouse_cursor is MouseCursor.TEXT


def test_composes_with_clickable_on_the_same_region() -> None:
    wrapped = Box().modifier(nv.clickable(on_click=lambda: None) | cursor(MouseCursor.DEFAULT))
    assert isinstance(wrapped, InteractionRegion)
    assert wrapped.mouse_cursor is MouseCursor.DEFAULT


def test_modifier_is_a_dataclass_element() -> None:
    assert cursor(MouseCursor.TEXT) == CursorModifier(cursor=MouseCursor.TEXT)


def test_a_plain_widget_defers_to_its_parent() -> None:
    assert Text("label").mouse_cursor is None
    assert Box().mouse_cursor is None


def test_a_clickable_answers_from_its_handlers_and_disabled_state() -> None:
    assert Clickable(on_click=lambda: None).mouse_cursor is MouseCursor.POINTER
    assert Clickable(on_press=lambda e: None).mouse_cursor is MouseCursor.POINTER
    assert Clickable().mouse_cursor is None

    button = Clickable(on_click=lambda: None)
    button.disabled = True
    assert button.mouse_cursor is MouseCursor.DEFAULT
    button.disabled = False
    assert button.mouse_cursor is MouseCursor.POINTER


def test_an_explicit_cursor_wins_over_the_role_even_while_disabled() -> None:
    button = Clickable(on_click=lambda: None)
    button.mouse_cursor = MouseCursor.NOT_ALLOWED
    assert button.mouse_cursor is MouseCursor.NOT_ALLOWED
    button.disabled = True
    assert button.mouse_cursor is MouseCursor.NOT_ALLOWED

    button.mouse_cursor = None
    assert button.mouse_cursor is MouseCursor.DEFAULT


def test_material_buttons_show_the_pointer() -> None:
    assert Button("OK", on_click=lambda: None).mouse_cursor is MouseCursor.POINTER
    assert IconButton("search", on_click=lambda: None).mouse_cursor is MouseCursor.POINTER
    assert Button("OK", on_click=lambda: None, disabled=True).mouse_cursor is MouseCursor.DEFAULT


def test_editable_text_shows_the_i_beam() -> None:
    assert EditableText().mouse_cursor is MouseCursor.TEXT
    assert EditableText(disabled=True).mouse_cursor is MouseCursor.DEFAULT


def test_text_fields_show_the_i_beam_over_the_whole_field() -> None:
    assert TextFieldBase().mouse_cursor is MouseCursor.TEXT
    assert TextFieldBase(disabled=True).mouse_cursor is MouseCursor.DEFAULT

    field = TextField(label="Name")
    assert field.mouse_cursor is MouseCursor.TEXT
    field.disabled = True
    assert field.mouse_cursor is MouseCursor.DEFAULT


def test_a_tappable_text_field_icon_shows_the_pointer() -> None:
    field = TextField(label="Password", trailing_icon="visibility", on_tap_trailing_icon=lambda: None)
    assert isinstance(field.trailing_icon, IconButton)
    assert field.trailing_icon.mouse_cursor is MouseCursor.POINTER
    field.disabled = True
    assert field.trailing_icon.mouse_cursor is MouseCursor.DEFAULT
