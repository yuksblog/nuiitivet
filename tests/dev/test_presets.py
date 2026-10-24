"""Tests for the reader of what a widget declares editable.

A widget names the keyword and the class in ``editable_parameters()``; everything else
-- the choices, their parameters, the default -- is read from the class.
"""

from __future__ import annotations

from typing import Any

from nuiitivet.dev.presets import Parameter, choices_of, families_of, family_of, value_of
from nuiitivet.layout.column import Column
from nuiitivet.material.buttons import Button, Fab, IconButton, ToggleButton
from nuiitivet.material.card import Card
from nuiitivet.material.chip import AssistChip
from nuiitivet.material.styles.button_style import ButtonStyle, IconButtonStyle
from nuiitivet.material.text import Text
from nuiitivet.testing import mount
from nuiitivet.theme.type_scale import TypeScale
from nuiitivet.widgeting.widget import Widget


def _family(widget: Any, keyword: str = "style"):
    """The family ``widget`` declares for ``keyword``, read with the widget mounted as the mode sees it."""
    with mount(Column(children=[widget])) as host:
        host.layout(300, 200)
        family = family_of(widget, keyword)
    assert family is not None, f"{type(widget).__name__} declares nothing for {keyword}"
    return family


def test_a_button_picks_its_style_from_the_button_style_presets_in_definition_order() -> None:
    family = _family(Button("a"))

    assert family.companion is ButtonStyle and family.called
    assert family.names == ("filled", "outlined", "text", "elevated", "tonal")


def test_a_parameter_is_read_from_the_preset_signature() -> None:
    (size,) = _family(Button("a")).choices[0].parameters

    assert size == Parameter("size", ("xs", "s", "m", "l", "xl"), "s")
    assert _family(Fab("add")).choices[0].parameters[0].choices == ("s", "m", "l")
    assert _family(Card(Text("a"))).choices[0].parameters == ()
    assert size.parse("m") == "m" and size.parse("huge") == "huge"


def test_default_and_from_theme_are_not_choices() -> None:
    assert _family(ToggleButton("a")).names == ("filled", "outlined", "elevated", "tonal")
    assert _family(AssistChip(label="a")).names == ("assist", "filter", "input", "suggestion")


def test_the_companion_is_the_declared_class_not_the_annotation() -> None:
    family = _family(IconButton("add"))

    assert family.companion is IconButtonStyle and family.names[0] == "standard"
    assert value_of(family, "tonal_vibrant", {"size": "l"}) == IconButtonStyle.tonal_vibrant("l")


def test_text_picks_a_type_scale_role_which_is_an_attribute_not_a_call() -> None:
    family = _family(Text("a"), "type_scale")

    assert (family.companion, family.called) == (TypeScale, False)
    assert family.names[:3] == ("DISPLAY_LARGE", "DISPLAY_MEDIUM", "DISPLAY_SMALL") and len(family.names) == 15
    assert value_of(family, "TITLE_LARGE") is TypeScale.TITLE_LARGE


def test_the_default_is_the_companions_default_else_what_the_live_widget_holds() -> None:
    assert _family(ToggleButton("a")).default == "filled", "ToggleButtonStyle.default() is filled('s')"
    assert _family(Fab("add")).default == "primary"
    assert _family(Button("a")).default == "filled", "no default(): the theme's filled style is measured"
    assert _family(Card(Text("a"))).default == "filled"
    assert _family(AssistChip(label="a")).default == "assist"
    assert _family(Text("a"), "type_scale").default == "BODY_MEDIUM"


def test_a_widget_that_declares_nothing_has_no_family() -> None:
    assert families_of(Column(children=[])) == ()


def test_a_widget_may_declare_several_keywords_and_a_class_without_choices_is_dropped() -> None:
    class Twice(Widget):
        @classmethod
        def editable_parameters(cls) -> dict[str, type]:
            return {"style": ButtonStyle, "scale": TypeScale, "nothing": Column}

    assert [family.keyword for family in families_of(Twice())] == ["style", "scale"]


def test_the_choices_of_a_class_are_read_once() -> None:
    assert choices_of(ButtonStyle) is choices_of(ButtonStyle)
