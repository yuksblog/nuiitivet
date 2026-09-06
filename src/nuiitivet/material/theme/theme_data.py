"""Material Design theme data."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Mapping, TYPE_CHECKING, Any, TypeVar

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ThemeExtension

if TYPE_CHECKING:
    from nuiitivet.material.styles.button_group_style import (
        ConnectedButtonGroupStyle,
        StandardButtonGroupStyle,
    )
    from nuiitivet.material.styles.button_style import ButtonStyle, IconToggleButtonStyle
    from nuiitivet.material.styles.fab_style import FabStyle
    from nuiitivet.material.styles.card_style import CardStyle
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle
    from nuiitivet.material.styles.chip_style import ChipStyle
    from nuiitivet.material.styles.dialog_style import DialogStyle
    from nuiitivet.material.styles.icon_style import IconStyle
    from nuiitivet.material.styles.loading_indicator_style import LoadingIndicatorStyle
    from nuiitivet.material.styles.menu_style import MenuStyle
    from nuiitivet.material.styles.progress_indicator_style import (
        CircularProgressIndicatorStyle,
        LinearProgressIndicatorStyle,
    )
    from nuiitivet.material.styles.radio_button_style import RadioButtonStyle
    from nuiitivet.material.styles.search_bar_style import SearchBarStyle
    from nuiitivet.material.styles.slider_style import SliderStyle
    from nuiitivet.material.styles.switch_style import SwitchStyle
    from nuiitivet.material.styles.text_style import TextStyle
    from nuiitivet.material.styles.text_field_style import TextFieldStyle
    from nuiitivet.material.styles.toggle_button_style import ToggleButtonStyle
    from nuiitivet.material.styles.toolbar_style import ToolbarStyle

ColorValue = str

_S = TypeVar("_S")

_shared_defaults: dict[Any, Any] = {}


def _shared_default(make: Callable[..., _S], *args: Any) -> _S:
    """Return the one default style ``make(*args)`` builds, constructing it on first use.

    A style property falls through to its default whenever the theme does not
    override it, which is the common case and runs on every paint; styles are
    frozen, so every theme can hand out the same object.
    """
    key = (make, args)
    style: _S | None = _shared_defaults.get(key)
    if style is None:
        style = _shared_defaults[key] = make(*args)
    return style


@dataclass(frozen=True)
class MaterialThemeData(ThemeExtension):
    """Material Design specific theme data."""

    roles: Mapping[ColorRole, ColorValue]

    # Widget styles (lazy-loaded to avoid circular imports)
    # Button variants
    _filled_button_style: "ButtonStyle | None" = None
    _outlined_button_style: "ButtonStyle | None" = None
    _text_button_style: "ButtonStyle | None" = None
    _elevated_button_style: "ButtonStyle | None" = None
    _tonal_button_style: "ButtonStyle | None" = None
    _fab_style: "FabStyle | None" = None

    # Toggle button variants
    _toggle_button_style: "ToggleButtonStyle | None" = None
    _icon_toggle_button_style: "IconToggleButtonStyle | None" = None

    # Button group variants
    _standard_button_group_style: "StandardButtonGroupStyle | None" = None
    _connected_button_group_style: "ConnectedButtonGroupStyle | None" = None

    # Card variants
    _filled_card_style: "CardStyle | None" = None
    _outlined_card_style: "CardStyle | None" = None
    _elevated_card_style: "CardStyle | None" = None

    # TextField variants
    _filled_text_field_style: "TextFieldStyle | None" = None
    _outlined_text_field_style: "TextFieldStyle | None" = None

    # Other styles
    _checkbox_style: "CheckboxStyle | None" = None
    _assist_chip_style: "ChipStyle | None" = None
    _filter_chip_style: "ChipStyle | None" = None
    _input_chip_style: "ChipStyle | None" = None
    _suggestion_chip_style: "ChipStyle | None" = None
    _radio_button_style: "RadioButtonStyle | None" = None
    _switch_style: "SwitchStyle | None" = None
    _slider_style: "SliderStyle | None" = None
    _basic_dialog_style: "DialogStyle | None" = None
    _icon_style: "IconStyle | None" = None
    _text_style: "TextStyle | None" = None
    _menu_style: "MenuStyle | None" = None
    _toolbar_style: "ToolbarStyle | None" = None
    _search_bar_style: "SearchBarStyle | None" = None

    # Loading indicator variants
    _loading_indicator_style: "LoadingIndicatorStyle | None" = None
    _contained_loading_indicator_style: "LoadingIndicatorStyle | None" = None

    # Progress indicator variants
    _linear_progress_indicator_style: "LinearProgressIndicatorStyle | None" = None
    _circular_progress_indicator_style: "CircularProgressIndicatorStyle | None" = None

    @property
    def filled_button_style(self) -> "ButtonStyle":
        """Get filled ButtonStyle for this theme."""
        if self._filled_button_style is not None:
            return self._filled_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return _shared_default(ButtonStyle.filled)

    @property
    def outlined_button_style(self) -> "ButtonStyle":
        """Get outlined ButtonStyle for this theme."""
        if self._outlined_button_style is not None:
            return self._outlined_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return _shared_default(ButtonStyle.outlined)

    @property
    def text_button_style(self) -> "ButtonStyle":
        """Get text ButtonStyle for this theme."""
        if self._text_button_style is not None:
            return self._text_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return _shared_default(ButtonStyle.text)

    @property
    def elevated_button_style(self) -> "ButtonStyle":
        """Get elevated ButtonStyle for this theme."""
        if self._elevated_button_style is not None:
            return self._elevated_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return _shared_default(ButtonStyle.elevated)

    @property
    def tonal_button_style(self) -> "ButtonStyle":
        """Get tonal ButtonStyle for this theme."""
        if self._tonal_button_style is not None:
            return self._tonal_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return _shared_default(ButtonStyle.tonal)

    @property
    def fab_style(self) -> "FabStyle":
        """Get FAB style for this theme."""
        if self._fab_style is not None:
            return self._fab_style
        from nuiitivet.material.styles.fab_style import FabStyle

        return _shared_default(FabStyle.primary)

    @property
    def toggle_button_style(self) -> "ToggleButtonStyle":
        """Get toggle button style for this theme."""
        if self._toggle_button_style is not None:
            return self._toggle_button_style
        from nuiitivet.material.styles.toggle_button_style import ToggleButtonStyle

        return _shared_default(ToggleButtonStyle.filled, "s")

    @property
    def icon_toggle_button_style(self) -> "IconToggleButtonStyle":
        """Get icon toggle button style for this theme."""
        if self._icon_toggle_button_style is not None:
            return self._icon_toggle_button_style
        from nuiitivet.material.styles.button_style import IconToggleButtonStyle

        return _shared_default(IconToggleButtonStyle.standard)

    @property
    def standard_button_group_style(self) -> "StandardButtonGroupStyle":
        """Get standard button group style for this theme."""
        if self._standard_button_group_style is not None:
            return self._standard_button_group_style
        from nuiitivet.material.styles.button_group_style import StandardButtonGroupStyle

        return _shared_default(StandardButtonGroupStyle.filled)

    @property
    def connected_button_group_style(self) -> "ConnectedButtonGroupStyle":
        """Get connected button group style for this theme."""
        if self._connected_button_group_style is not None:
            return self._connected_button_group_style
        from nuiitivet.material.styles.button_group_style import ConnectedButtonGroupStyle

        return _shared_default(ConnectedButtonGroupStyle.filled)

    @property
    def menu_style(self) -> "MenuStyle":
        """Get menu style for this theme."""
        if self._menu_style is not None:
            return self._menu_style
        from nuiitivet.material.styles.menu_style import MenuStyle

        return _shared_default(MenuStyle.standard)

    @property
    def toolbar_style(self) -> "ToolbarStyle":
        """Get toolbar style for this theme."""
        if self._toolbar_style is not None:
            return self._toolbar_style
        from nuiitivet.material.styles.toolbar_style import ToolbarStyle

        return _shared_default(ToolbarStyle.standard)

    @property
    def filled_card_style(self) -> "CardStyle":
        """Get filled CardStyle for this theme."""
        if self._filled_card_style is not None:
            return self._filled_card_style
        from nuiitivet.material.styles.card_style import CardStyle

        return _shared_default(CardStyle.filled)

    @property
    def outlined_card_style(self) -> "CardStyle":
        """Get outlined CardStyle for this theme."""
        if self._outlined_card_style is not None:
            return self._outlined_card_style
        from nuiitivet.material.styles.card_style import CardStyle

        return _shared_default(CardStyle.outlined)

    @property
    def elevated_card_style(self) -> "CardStyle":
        """Get elevated CardStyle for this theme."""
        if self._elevated_card_style is not None:
            return self._elevated_card_style
        from nuiitivet.material.styles.card_style import CardStyle

        return _shared_default(CardStyle.elevated)

    @property
    def filled_text_field_style(self) -> "TextFieldStyle":
        """Get filled TextFieldStyle for this theme."""
        if self._filled_text_field_style is not None:
            return self._filled_text_field_style
        from nuiitivet.material.styles.text_field_style import TextFieldStyle

        return _shared_default(TextFieldStyle.filled)

    @property
    def search_bar_style(self) -> "SearchBarStyle":
        """Get SearchBarStyle for this theme."""
        if self._search_bar_style is not None:
            return self._search_bar_style
        from nuiitivet.material.styles.search_bar_style import SearchBarStyle

        return _shared_default(SearchBarStyle)

    @property
    def outlined_text_field_style(self) -> "TextFieldStyle":
        """Get outlined TextFieldStyle for this theme."""
        if self._outlined_text_field_style is not None:
            return self._outlined_text_field_style
        from nuiitivet.material.styles.text_field_style import TextFieldStyle

        return _shared_default(TextFieldStyle.outlined)

    @property
    def checkbox_style(self) -> "CheckboxStyle":
        """Get CheckboxStyle for this theme."""
        if self._checkbox_style is not None:
            return self._checkbox_style
        from nuiitivet.material.styles.checkbox_style import CheckboxStyle

        return _shared_default(CheckboxStyle)

    @property
    def assist_chip_style(self) -> "ChipStyle":
        """Get Assist ChipStyle for this theme."""
        if self._assist_chip_style is not None:
            return self._assist_chip_style
        from nuiitivet.material.styles.chip_style import ChipStyle

        return _shared_default(ChipStyle.assist)

    @property
    def filter_chip_style(self) -> "ChipStyle":
        """Get Filter ChipStyle for this theme."""
        if self._filter_chip_style is not None:
            return self._filter_chip_style
        from nuiitivet.material.styles.chip_style import ChipStyle

        return _shared_default(ChipStyle.filter)

    @property
    def input_chip_style(self) -> "ChipStyle":
        """Get Input ChipStyle for this theme."""
        if self._input_chip_style is not None:
            return self._input_chip_style
        from nuiitivet.material.styles.chip_style import ChipStyle

        return _shared_default(ChipStyle.input)

    @property
    def suggestion_chip_style(self) -> "ChipStyle":
        """Get Suggestion ChipStyle for this theme."""
        if self._suggestion_chip_style is not None:
            return self._suggestion_chip_style
        from nuiitivet.material.styles.chip_style import ChipStyle

        return _shared_default(ChipStyle.suggestion)

    @property
    def radio_button_style(self) -> "RadioButtonStyle":
        """Get RadioButtonStyle for this theme."""
        if self._radio_button_style is not None:
            return self._radio_button_style
        from nuiitivet.material.styles.radio_button_style import RadioButtonStyle

        return _shared_default(RadioButtonStyle)

    @property
    def switch_style(self) -> "SwitchStyle":
        """Get SwitchStyle for this theme."""
        if self._switch_style is not None:
            return self._switch_style
        from nuiitivet.material.styles.switch_style import SwitchStyle

        return _shared_default(SwitchStyle)

    @property
    def slider_style(self) -> "SliderStyle":
        """Get SliderStyle for this theme."""
        if self._slider_style is not None:
            return self._slider_style
        from nuiitivet.material.styles.slider_style import SliderStyle

        return _shared_default(SliderStyle.xs)

    @property
    def basic_dialog_style(self) -> "DialogStyle":
        """Get DialogStyle for this theme."""
        if self._basic_dialog_style is not None:
            return self._basic_dialog_style
        from nuiitivet.material.styles.dialog_style import DialogStyle

        return _shared_default(DialogStyle.basic)

    @property
    def icon_style(self) -> "IconStyle":
        """Get IconStyle for this theme."""
        if self._icon_style is not None:
            return self._icon_style
        from nuiitivet.material.styles.icon_style import IconStyle

        return _shared_default(IconStyle)

    @property
    def text_style(self) -> "TextStyle":
        """Get TextStyle for this theme."""
        if self._text_style is not None:
            return self._text_style
        from nuiitivet.material.styles.text_style import TextStyle

        return _shared_default(TextStyle)

    @property
    def loading_indicator_style(self) -> "LoadingIndicatorStyle":
        """Get LoadingIndicatorStyle for this theme."""
        if self._loading_indicator_style is not None:
            return self._loading_indicator_style
        from nuiitivet.material.styles.loading_indicator_style import LoadingIndicatorStyle

        return _shared_default(LoadingIndicatorStyle.default)

    @property
    def contained_loading_indicator_style(self) -> "LoadingIndicatorStyle":
        """Get contained LoadingIndicatorStyle for this theme."""
        if self._contained_loading_indicator_style is not None:
            return self._contained_loading_indicator_style
        from nuiitivet.material.styles.loading_indicator_style import LoadingIndicatorStyle

        return _shared_default(LoadingIndicatorStyle.contained)

    @property
    def linear_progress_indicator_style(self) -> "LinearProgressIndicatorStyle":
        """Get LinearProgressIndicatorStyle for this theme."""
        if self._linear_progress_indicator_style is not None:
            return self._linear_progress_indicator_style
        from nuiitivet.material.styles.progress_indicator_style import LinearProgressIndicatorStyle

        return _shared_default(LinearProgressIndicatorStyle.default)

    @property
    def circular_progress_indicator_style(self) -> "CircularProgressIndicatorStyle":
        """Get CircularProgressIndicatorStyle for this theme."""
        if self._circular_progress_indicator_style is not None:
            return self._circular_progress_indicator_style
        from nuiitivet.material.styles.progress_indicator_style import CircularProgressIndicatorStyle

        return _shared_default(CircularProgressIndicatorStyle.default)

    def copy_with(self, **kwargs: Any) -> "MaterialThemeData":
        """Create a copy of this theme data with the given fields replaced."""
        return replace(self, **kwargs)
