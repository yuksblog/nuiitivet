"""A theme's form factor sets the component sizes; a style's density overrides it."""

from __future__ import annotations

from typing import Iterator, Tuple

import pytest

from nuiitivet.material.buttons import Button, ToggleButton
from nuiitivet.material.menu import Menu, MenuItem
from nuiitivet.material.search import SearchBar
from nuiitivet.material.selection_controls import Checkbox, RadioButton, Switch, _size_basis
from nuiitivet.material.styles.checkbox_style import CheckboxStyle
from nuiitivet.material.styles.menu_style import MenuStyle
from nuiitivet.material.styles.search_bar_style import SearchBarStyle
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.material.text_fields import TextField
from nuiitivet.material.theme.form_factor import FormFactor, FormFactorLike
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.observable import Observable
from nuiitivet.testing import WidgetHost, mount
from nuiitivet.widgeting.widget import Widget

_HOSTS: list[WidgetHost] = []


@pytest.fixture(autouse=True)
def _close_hosts() -> Iterator[None]:
    try:
        yield
    finally:
        while _HOSTS:
            _HOSTS.pop().close()


def _mounted(widget: Widget, form_factor: FormFactorLike) -> Widget:
    _HOSTS.append(mount(widget, theme=MaterialThemeFactory.light("#6750A4", form_factor=form_factor)))
    return widget


def _size(widget: Widget, form_factor: FormFactorLike) -> Tuple[int, int]:
    return _mounted(widget, form_factor).preferred_size()


# --- FormFactor --------------------------------------------------------------


def test_a_name_is_the_built_in_form_factor() -> None:
    assert FormFactor.of("desktop") == FormFactor.desktop()
    assert FormFactor.of("mobile") == FormFactor.mobile()
    custom = FormFactor.desktop().copy_with(text_field=-2)
    assert FormFactor.of(custom) is custom


def test_an_unknown_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        FormFactor.of("tablet")  # type: ignore[arg-type]


def test_mobile_is_the_md3_baseline() -> None:
    assert FormFactor.mobile() == FormFactor(touch_targets=True, text_field=0, search_bar=0, menu=0)


def test_a_positive_density_is_rejected() -> None:
    with pytest.raises(ValueError):
        FormFactor(text_field=1)
    with pytest.raises(ValueError):
        TextFieldStyle.outlined().copy_with(density=1)
    with pytest.raises(ValueError):
        SearchBarStyle(density=1)
    with pytest.raises(ValueError):
        MenuStyle(density=1)


@pytest.mark.parametrize("factory", [MaterialThemeFactory.light, MaterialThemeFactory.dark])
def test_a_theme_factory_stores_the_form_factor(factory) -> None:
    data = factory("#6750A4", form_factor="mobile").extension(MaterialThemeData)
    assert data is not None and data.form_factor == FormFactor.mobile()


def test_a_seed_pair_shares_the_form_factor() -> None:
    custom = FormFactor.desktop().copy_with(menu=-1)
    for theme in MaterialThemeFactory.from_seed_pair("#6750A4", form_factor=custom):
        data = theme.extension(MaterialThemeData)
        assert data is not None and data.form_factor is custom


# --- Sizes -------------------------------------------------------------------


def test_desktop_puts_a_row_of_controls_at_40() -> None:
    assert _size(TextField("x", label="Name"), "desktop")[1] == 40
    assert _size(TextField("x", style=TextFieldStyle.outlined()), "desktop")[1] == 40
    assert _size(SearchBar(Observable("")), "desktop")[1] == 40
    assert _size(Button("Save"), "desktop")[1] == 40
    assert _size(ToggleButton("A"), "desktop")[1] == 40
    assert _size(Checkbox(), "desktop") == (40, 40)
    assert _size(RadioButton("a"), "desktop") == (40, 40)


def test_a_desktop_switch_is_as_wide_as_its_track() -> None:
    assert _size(Switch(), "desktop") == (52, 40)


def test_mobile_keeps_the_md3_sizes() -> None:
    assert _size(TextField("x", label="Name"), "mobile")[1] == 56
    assert _size(SearchBar(Observable("")), "mobile")[1] == 56
    assert _size(Button("Save"), "mobile")[1] == 48
    assert _size(ToggleButton("A"), "mobile")[1] == 48
    assert _size(Checkbox(), "mobile") == (48, 48)
    assert _size(RadioButton("a"), "mobile") == (48, 48)
    assert _size(Switch(), "mobile") == (48, 48)


@pytest.mark.parametrize(("form_factor", "height"), [("desktop", 32), ("mobile", 44)])
def test_a_menu_item_follows_the_form_factor(form_factor: FormFactorLike, height: int) -> None:
    menu = Menu([MenuItem("Open")])
    _mounted(menu, form_factor)
    assert menu.style.item_height == height


def test_an_explicit_minimum_wins_over_the_form_factor() -> None:
    from nuiitivet.material.styles.button_style import ButtonStyle

    assert _size(Button("Save", style=ButtonStyle.filled().copy_with(min_height=48)), "desktop")[1] == 48
    assert _size(Button("Save", style=ButtonStyle.filled().copy_with(min_height=40)), "mobile")[1] == 40


def test_a_desktop_checkbox_keeps_the_md3_proportions() -> None:
    checkbox = _mounted(Checkbox(), "desktop")
    style = CheckboxStyle()
    sizes = style.compute_sizes(_size_basis(style, checkbox, 40))
    assert sizes["icon_size"] == 18
    assert sizes["state_layer_size"] == 40


# --- Style density -----------------------------------------------------------


def test_a_style_density_wins_over_the_form_factor() -> None:
    style = TextFieldStyle.outlined().copy_with(density=-2)
    assert _size(TextField("x", style=style), "desktop")[1] == 48
    assert _size(TextField("x", style=style), "mobile")[1] == 48
    assert _size(TextField("x", style=TextFieldStyle.outlined().copy_with(density=0)), "desktop")[1] == 56


def test_a_form_factor_step_applies_to_the_whole_theme() -> None:
    custom = FormFactor.desktop().copy_with(text_field=-1, search_bar=-2)
    assert _size(TextField("x"), custom)[1] == 52
    assert _size(SearchBar(Observable("")), custom)[1] == 48


def test_a_density_below_the_floor_stops_at_the_floor() -> None:
    assert _size(TextField("x", style=TextFieldStyle.outlined().copy_with(density=-9)), "mobile")[1] == 36
    assert _size(SearchBar(Observable(""), style=SearchBarStyle(density=-9)), "mobile")[1] == 40
    menu = Menu([MenuItem("Open")], style=MenuStyle(density=-9))
    _mounted(menu, "mobile")
    assert menu.style.item_height == 32


def test_dense_insets_keep_the_text_row() -> None:
    field = _mounted(TextField("x", style=TextFieldStyle.outlined()), "desktop")
    assert isinstance(field, TextField)
    assert field.style.content_insets == (16, 8, 16, 8)


# --- Filled label ------------------------------------------------------------


def test_a_short_filled_field_keeps_its_label_in_the_text_row() -> None:
    field = _mounted(TextField("", label="Name"), "desktop")
    assert isinstance(field, TextField)
    assert field._label_is_inline(field.style)
    field.layout(200, 40)
    assert field._label_band == 0


@pytest.mark.parametrize(
    "field",
    [
        lambda: TextField("", label="Name", style=TextFieldStyle.outlined()),
        lambda: TextField("", label="Name", style=TextFieldStyle.filled().copy_with(density=-1)),
        lambda: TextField(""),
    ],
)
def test_other_fields_keep_a_floating_label(field) -> None:
    widget = _mounted(field(), "desktop")
    assert isinstance(widget, TextField)
    assert not widget._label_is_inline(widget.style)
