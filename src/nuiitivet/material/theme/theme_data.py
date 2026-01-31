"""Material Design theme data."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, TYPE_CHECKING, Any

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ThemeExtension

if TYPE_CHECKING:
    from nuiitivet.material.styles.button_style import ButtonStyle
    from nuiitivet.material.styles.card_style import CardStyle
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle
    from nuiitivet.material.styles.dialog_style import DialogStyle
    from nuiitivet.material.styles.icon_style import IconStyle
    from nuiitivet.material.styles.loading_indicator_style import LoadingIndicatorStyle
    from nuiitivet.material.styles.text_style import TextStyle
    from nuiitivet.material.styles.text_field_style import TextFieldStyle

ColorValue = str


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
    _fab_style: "ButtonStyle | None" = None

    # Card variants
    _filled_card_style: "CardStyle | None" = None
    _outlined_card_style: "CardStyle | None" = None
    _elevated_card_style: "CardStyle | None" = None

    # TextField variants
    _filled_text_field_style: "TextFieldStyle | None" = None
    _outlined_text_field_style: "TextFieldStyle | None" = None

    # Other styles
    _checkbox_style: "CheckboxStyle | None" = None
    _alert_dialog_style: "DialogStyle | None" = None
    _icon_style: "IconStyle | None" = None
    _text_style: "TextStyle | None" = None

    # Loading indicator variants
    _loading_indicator_style: "LoadingIndicatorStyle | None" = None
    _contained_loading_indicator_style: "LoadingIndicatorStyle | None" = None

    @property
    def filled_button_style(self) -> "ButtonStyle":
        """Get filled ButtonStyle for this theme."""
        if self._filled_button_style is not None:
            return self._filled_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return ButtonStyle.filled()

    @property
    def outlined_button_style(self) -> "ButtonStyle":
        """Get outlined ButtonStyle for this theme."""
        if self._outlined_button_style is not None:
            return self._outlined_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return ButtonStyle.outlined()

    @property
    def text_button_style(self) -> "ButtonStyle":
        """Get text ButtonStyle for this theme."""
        if self._text_button_style is not None:
            return self._text_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return ButtonStyle.text()

    @property
    def elevated_button_style(self) -> "ButtonStyle":
        """Get elevated ButtonStyle for this theme."""
        if self._elevated_button_style is not None:
            return self._elevated_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return ButtonStyle.elevated()

    @property
    def tonal_button_style(self) -> "ButtonStyle":
        """Get tonal ButtonStyle for this theme."""
        if self._tonal_button_style is not None:
            return self._tonal_button_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return ButtonStyle.tonal()

    @property
    def fab_style(self) -> "ButtonStyle":
        """Get FAB ButtonStyle for this theme."""
        if self._fab_style is not None:
            return self._fab_style
        from nuiitivet.material.styles.button_style import ButtonStyle

        return ButtonStyle.fab()

    @property
    def filled_card_style(self) -> "CardStyle":
        """Get filled CardStyle for this theme."""
        if self._filled_card_style is not None:
            return self._filled_card_style
        from nuiitivet.material.styles.card_style import CardStyle

        return CardStyle.filled()

    @property
    def outlined_card_style(self) -> "CardStyle":
        """Get outlined CardStyle for this theme."""
        if self._outlined_card_style is not None:
            return self._outlined_card_style
        from nuiitivet.material.styles.card_style import CardStyle

        return CardStyle.outlined()

    @property
    def elevated_card_style(self) -> "CardStyle":
        """Get elevated CardStyle for this theme."""
        if self._elevated_card_style is not None:
            return self._elevated_card_style
        from nuiitivet.material.styles.card_style import CardStyle

        return CardStyle.elevated()

    @property
    def filled_text_field_style(self) -> "TextFieldStyle":
        """Get filled TextFieldStyle for this theme."""
        if self._filled_text_field_style is not None:
            return self._filled_text_field_style
        from nuiitivet.material.styles.text_field_style import TextFieldStyle

        return TextFieldStyle.filled()

    @property
    def outlined_text_field_style(self) -> "TextFieldStyle":
        """Get outlined TextFieldStyle for this theme."""
        if self._outlined_text_field_style is not None:
            return self._outlined_text_field_style
        from nuiitivet.material.styles.text_field_style import TextFieldStyle

        return TextFieldStyle.outlined()

    @property
    def checkbox_style(self) -> "CheckboxStyle":
        """Get CheckboxStyle for this theme."""
        if self._checkbox_style is not None:
            return self._checkbox_style
        from nuiitivet.material.styles.checkbox_style import CheckboxStyle

        return CheckboxStyle()

    @property
    def alert_dialog_style(self) -> "DialogStyle":
        """Get DialogStyle for this theme."""
        if self._alert_dialog_style is not None:
            return self._alert_dialog_style
        from nuiitivet.material.styles.dialog_style import DialogStyle

        return DialogStyle.basic()

    @property
    def icon_style(self) -> "IconStyle":
        """Get IconStyle for this theme."""
        if self._icon_style is not None:
            return self._icon_style
        from nuiitivet.material.styles.icon_style import IconStyle

        return IconStyle()

    @property
    def text_style(self) -> "TextStyle":
        """Get TextStyle for this theme."""
        if self._text_style is not None:
            return self._text_style
        from nuiitivet.material.styles.text_style import TextStyle

        return TextStyle()

    @property
    def loading_indicator_style(self) -> "LoadingIndicatorStyle":
        """Get LoadingIndicatorStyle for this theme."""
        if self._loading_indicator_style is not None:
            return self._loading_indicator_style
        from nuiitivet.material.styles.loading_indicator_style import LoadingIndicatorStyle

        return LoadingIndicatorStyle.default()

    @property
    def contained_loading_indicator_style(self) -> "LoadingIndicatorStyle":
        """Get contained LoadingIndicatorStyle for this theme."""
        if self._contained_loading_indicator_style is not None:
            return self._contained_loading_indicator_style
        from nuiitivet.material.styles.loading_indicator_style import LoadingIndicatorStyle

        return LoadingIndicatorStyle.contained()

    def copy_with(self, **kwargs: Any) -> "MaterialThemeData":
        """Create a copy of this theme data with the given fields replaced."""
        return replace(self, **kwargs)
