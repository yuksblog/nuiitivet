"""Tests for the preset table layout edit mode picks from."""

from __future__ import annotations

from nuiitivet.dev.presets import family_of, value_of
from nuiitivet.material.buttons import Button, IconButton
from nuiitivet.material.card import Card
from nuiitivet.material.styles.button_style import ButtonStyle, IconButtonStyle
from nuiitivet.material.text import Text
from nuiitivet.theme.type_scale import TypeScale
from nuiitivet.widgets.text import TextBase


def test_a_button_picks_from_the_button_style_presets() -> None:
    family = family_of(Button("a"))

    assert family is not None
    assert (family.keyword, family.companion) == ("style", "ButtonStyle")
    assert family.names == ("filled", "tonal", "outlined", "elevated", "text")
    assert family.sizes == ("xs", "s", "m", "l", "xl")
    assert family.default == ("filled", "s")


def test_text_picks_a_type_scale_role_which_is_an_attribute_not_a_call() -> None:
    family = family_of(Text("a"))

    assert family is not None and family is family_of(TextBase("a"))
    assert (family.keyword, family.companion, family.called) == ("type_scale", "TypeScale", False)
    assert family.names[:3] == ("DISPLAY_LARGE", "DISPLAY_MEDIUM", "DISPLAY_SMALL")
    assert len(family.names) == 15 and family.sizes == ()


def test_a_card_takes_no_size() -> None:
    family = family_of(Card(Text("a")))

    assert family is not None
    assert family.sizes == () and family.default == ("filled", None)


def test_a_widget_without_presets_has_no_family() -> None:
    from nuiitivet.layout.column import Column

    assert family_of(Column(children=[])) is None


def test_the_value_is_what_the_widget_holds() -> None:
    button, icon, text = family_of(Button("a")), family_of(IconButton("add")), family_of(Text("a"))
    assert button is not None and icon is not None and text is not None

    assert value_of(button, "outlined", "m") == ButtonStyle.outlined("m")
    assert value_of(button, "filled", None) == ButtonStyle.filled()
    assert value_of(icon, "tonal_vibrant", "l") == IconButtonStyle.tonal_vibrant("l")
    assert value_of(text, "TITLE_LARGE", None) is TypeScale.TITLE_LARGE
