from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .badge import LargeBadge, SmallBadge
    from .app import MaterialApp
    from .app import MaterialApp as App
    from .divider import Divider
    from .buttons import (
        Button,
        Fab,
        IconButton,
        IconToggleButton,
        ToggleButton,
    )
    from .styles.button_style import ButtonStyle, IconButtonStyle, IconToggleButtonStyle
    from .styles.button_size import ButtonSize, FabSize
    from .styles.fab_style import FabStyle
    from .styles.toggle_button_style import ToggleButtonStyle
    from .card import Card
    from .styles.card_style import CardStyle
    from .chip import AssistChip, FilterChip, InputChip, SuggestionChip
    from .dialogs import AlertDialog
    from .loading_indicator import LoadingIndicator
    from .progress_indicators import (
        CircularProgressIndicator,
        IndeterminateCircularProgressIndicator,
        IndeterminateLinearProgressIndicator,
        LinearProgressIndicator,
    )
    from .menu import Menu, MenuDivider, MenuItem, SubMenuItem
    from .intents import LoadingIntent
    from .icon import Icon
    from .navigation_rail import NavigationRail, RailItem
    from .selection_controls import Checkbox, RadioButton, RadioGroup, Switch
    from .slider import CenteredSlider, Orientation, RangeSlider, Slider
    from .symbols import Symbol, Symbols
    from .text_fields import TextField
    from .styles.text_field_style import TextFieldStyle
    from .text import Text
    from .overlay import MaterialOverlay
    from .overlay import MaterialOverlay as Overlay
    from .theme.material_theme import MaterialTheme
    from .theme.material_theme import MaterialTheme as ThemeFactory
    from .toolbar import DockedToolbar, FloatingToolbar, ToolbarOrientation
    from .tooltip import Tooltip, RichTooltip
    from .styles.sheet_style import SideSheetStyle, BottomSheetStyle
    from .sheet import SideSheet, BottomSheet
    from .button_group import (
        GroupButton,
        ButtonGroupPosition,
        StandardButtonGroup,
        ConnectedButtonGroup,
    )
    from .styles.button_group_style import (
        StandardButtonGroupStyle,
        ConnectedButtonGroupStyle,
    )
    from .transition_spec import (
        MaterialSideSheetTransitionSpec,
        MaterialBottomSheetTransitionSpec,
    )

__all__ = [
    "MaterialApp",
    "App",
    "MaterialTheme",
    "ThemeFactory",
    "SmallBadge",
    "LargeBadge",
    "Divider",
    "Text",
    "Icon",
    "Symbols",
    "Symbol",
    "Checkbox",
    "RadioButton",
    "RadioGroup",
    "Switch",
    "Slider",
    "CenteredSlider",
    "RangeSlider",
    "Orientation",
    "Card",
    "CardStyle",
    "AssistChip",
    "FilterChip",
    "InputChip",
    "SuggestionChip",
    "Button",
    "ToggleButton",
    "Fab",
    "IconButton",
    "IconToggleButton",
    "ButtonStyle",
    "ToggleButtonStyle",
    "IconButtonStyle",
    "IconToggleButtonStyle",
    "ButtonSize",
    "FabStyle",
    "FabSize",
    "TextField",
    "TextFieldStyle",
    "NavigationRail",
    "RailItem",
    "MaterialOverlay",
    "Overlay",
    "AlertDialog",
    "LoadingIndicator",
    "LinearProgressIndicator",
    "IndeterminateLinearProgressIndicator",
    "CircularProgressIndicator",
    "IndeterminateCircularProgressIndicator",
    "Menu",
    "MenuDivider",
    "MenuItem",
    "SubMenuItem",
    "LoadingIntent",
    "DockedToolbar",
    "FloatingToolbar",
    "ToolbarOrientation",
    "Tooltip",
    "RichTooltip",
    "MaterialTransitions",
    "MaterialSideSheetTransitionSpec",
    "MaterialBottomSheetTransitionSpec",
    "SideSheetStyle",
    "BottomSheetStyle",
    "SideSheet",
    "BottomSheet",
    "GroupButton",
    "ButtonGroupPosition",
    "StandardButtonGroupStyle",
    "ConnectedButtonGroupStyle",
    "StandardButtonGroup",
    "ConnectedButtonGroup",
    "FadeIn",
    "FadeOut",
    "ScaleIn",
    "ScaleOut",
    "SlideInVertically",
    "SlideOutVertically",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "MaterialApp": ("app", "MaterialApp"),
    "App": ("app", "MaterialApp"),
    "MaterialTheme": ("theme", "MaterialTheme"),
    "ThemeFactory": ("theme", "MaterialTheme"),
    "SmallBadge": ("badge", "SmallBadge"),
    "LargeBadge": ("badge", "LargeBadge"),
    "Divider": ("divider", "Divider"),
    "Text": ("text", "Text"),
    "Icon": ("icon", "Icon"),
    "Symbols": ("symbols", "Symbols"),
    "Symbol": ("symbols", "Symbol"),
    "Checkbox": ("selection_controls", "Checkbox"),
    "RadioButton": ("selection_controls", "RadioButton"),
    "RadioGroup": ("selection_controls", "RadioGroup"),
    "Switch": ("selection_controls", "Switch"),
    "Slider": ("slider", "Slider"),
    "CenteredSlider": ("slider", "CenteredSlider"),
    "RangeSlider": ("slider", "RangeSlider"),
    "Orientation": ("slider", "Orientation"),
    "Card": ("card", "Card"),
    "CardStyle": ("styles.card_style", "CardStyle"),
    "AssistChip": ("chip", "AssistChip"),
    "FilterChip": ("chip", "FilterChip"),
    "InputChip": ("chip", "InputChip"),
    "SuggestionChip": ("chip", "SuggestionChip"),
    "Button": ("buttons", "Button"),
    "ToggleButton": ("buttons", "ToggleButton"),
    "Fab": ("buttons", "Fab"),
    "IconButton": ("buttons", "IconButton"),
    "IconToggleButton": ("buttons", "IconToggleButton"),
    "ButtonStyle": ("styles.button_style", "ButtonStyle"),
    "IconButtonStyle": ("styles.button_style", "IconButtonStyle"),
    "IconToggleButtonStyle": ("styles.button_style", "IconToggleButtonStyle"),
    "ToggleButtonStyle": ("styles.toggle_button_style", "ToggleButtonStyle"),
    "ButtonSize": ("styles.button_size", "ButtonSize"),
    "FabStyle": ("styles.fab_style", "FabStyle"),
    "FabSize": ("styles.button_size", "FabSize"),
    "TextField": ("text_fields", "TextField"),
    "TextFieldStyle": ("styles.text_field_style", "TextFieldStyle"),
    "NavigationRail": ("navigation_rail", "NavigationRail"),
    "RailItem": ("navigation_rail", "RailItem"),
    "MaterialOverlay": ("overlay", "MaterialOverlay"),
    "Overlay": ("overlay", "MaterialOverlay"),
    "AlertDialog": ("dialogs", "AlertDialog"),
    "LoadingIndicator": ("loading_indicator", "LoadingIndicator"),
    "LinearProgressIndicator": ("progress_indicators", "LinearProgressIndicator"),
    "IndeterminateLinearProgressIndicator": ("progress_indicators", "IndeterminateLinearProgressIndicator"),
    "CircularProgressIndicator": ("progress_indicators", "CircularProgressIndicator"),
    "IndeterminateCircularProgressIndicator": ("progress_indicators", "IndeterminateCircularProgressIndicator"),
    "Menu": ("menu", "Menu"),
    "MenuDivider": ("menu", "MenuDivider"),
    "MenuItem": ("menu", "MenuItem"),
    "SubMenuItem": ("menu", "SubMenuItem"),
    "LoadingIntent": ("intents", "LoadingIntent"),
    "DockedToolbar": ("toolbar", "DockedToolbar"),
    "FloatingToolbar": ("toolbar", "FloatingToolbar"),
    "ToolbarOrientation": ("toolbar", "ToolbarOrientation"),
    "Tooltip": ("tooltip", "Tooltip"),
    "RichTooltip": ("tooltip", "RichTooltip"),
    "MaterialLoadingIndicatorIntent": ("overlay_intents", "MaterialLoadingIndicatorIntent"),
    "MaterialTransitions": ("transition_spec", "MaterialTransitions"),
    "MaterialSideSheetTransitionSpec": ("transition_spec", "MaterialSideSheetTransitionSpec"),
    "MaterialBottomSheetTransitionSpec": ("transition_spec", "MaterialBottomSheetTransitionSpec"),
    "SideSheetStyle": ("styles.sheet_style", "SideSheetStyle"),
    "BottomSheetStyle": ("styles.sheet_style", "BottomSheetStyle"),
    "SideSheet": ("sheet", "SideSheet"),
    "BottomSheet": ("sheet", "BottomSheet"),
    "GroupButton": ("button_group", "GroupButton"),
    "ButtonGroupPosition": ("button_group", "ButtonGroupPosition"),
    "StandardButtonGroupStyle": ("styles.button_group_style", "StandardButtonGroupStyle"),
    "ConnectedButtonGroupStyle": ("styles.button_group_style", "ConnectedButtonGroupStyle"),
    "StandardButtonGroup": ("button_group", "StandardButtonGroup"),
    "ConnectedButtonGroup": ("button_group", "ConnectedButtonGroup"),
    "FadeIn": ("transitions", "FadeIn"),
    "FadeOut": ("transitions", "FadeOut"),
    "ScaleIn": ("transitions", "ScaleIn"),
    "ScaleOut": ("transitions", "ScaleOut"),
    "SlideInVertically": ("transitions", "SlideInVertically"),
    "SlideOutVertically": ("transitions", "SlideOutVertically"),
}


def __getattr__(name: str) -> Any:
    spec = _EXPORTS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = spec
    module = importlib.import_module(f"{__name__}.{module_name}")
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_EXPORTS.keys()))
