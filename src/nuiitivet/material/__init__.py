from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .badge import BadgeValue, LargeBadge, SmallBadge
    from .app import MaterialApp
    from .divider import Divider
    from .buttons import (
        ElevatedButton,
        FilledButton,
        FilledTonalButton,
        FilledToggleButton,
        FloatingActionButton,
        IconButton,
        IconToggleButton,
        OutlinedButton,
        OutlinedToggleButton,
        TextToggleButton,
        TextButton,
        TonalToggleButton,
    )
    from .card import Card, ElevatedCard, FilledCard, OutlinedCard
    from .chip import AssistChip, FilterChip, InputChip, SuggestionChip
    from .dialogs import AlertDialog
    from .loading_indicator import LoadingIndicator
    from .menu import Menu, MenuDivider, MenuItem, SubMenuItem
    from .intents import LoadingIntent
    from .icon import Icon
    from .navigation_rail import NavigationRail, RailItem
    from .selection_controls import Checkbox, RadioButton, RadioGroup, Switch
    from .slider import CenteredSlider, Orientation, RangeSlider, Slider
    from .symbols import Symbol, Symbols
    from .text_fields import FilledTextField, OutlinedTextField, TextField
    from .text import Text
    from .overlay import MaterialOverlay
    from .toolbar import DockedToolbar, FloatingToolbar, ToolbarOrientation
    from .tooltip import Tooltip, RichTooltip

__all__ = [
    "MaterialApp",
    "SmallBadge",
    "LargeBadge",
    "BadgeValue",
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
    "ElevatedCard",
    "FilledCard",
    "OutlinedCard",
    "AssistChip",
    "FilterChip",
    "InputChip",
    "SuggestionChip",
    "ElevatedButton",
    "FilledButton",
    "FilledTonalButton",
    "FilledToggleButton",
    "FloatingActionButton",
    "IconButton",
    "IconToggleButton",
    "OutlinedButton",
    "OutlinedToggleButton",
    "TextToggleButton",
    "TextButton",
    "TonalToggleButton",
    "TextField",
    "FilledTextField",
    "OutlinedTextField",
    "NavigationRail",
    "RailItem",
    "MaterialOverlay",
    "AlertDialog",
    "LoadingIndicator",
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
    "FadeIn",
    "FadeOut",
    "ScaleIn",
    "ScaleOut",
    "SlideInVertically",
    "SlideOutVertically",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "MaterialApp": ("app", "MaterialApp"),
    "SmallBadge": ("badge", "SmallBadge"),
    "LargeBadge": ("badge", "LargeBadge"),
    "BadgeValue": ("badge", "BadgeValue"),
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
    "ElevatedCard": ("card", "ElevatedCard"),
    "FilledCard": ("card", "FilledCard"),
    "OutlinedCard": ("card", "OutlinedCard"),
    "AssistChip": ("chip", "AssistChip"),
    "FilterChip": ("chip", "FilterChip"),
    "InputChip": ("chip", "InputChip"),
    "SuggestionChip": ("chip", "SuggestionChip"),
    "ElevatedButton": ("buttons", "ElevatedButton"),
    "FilledButton": ("buttons", "FilledButton"),
    "FilledTonalButton": ("buttons", "FilledTonalButton"),
    "FilledToggleButton": ("buttons", "FilledToggleButton"),
    "FloatingActionButton": ("buttons", "FloatingActionButton"),
    "IconButton": ("buttons", "IconButton"),
    "IconToggleButton": ("buttons", "IconToggleButton"),
    "OutlinedButton": ("buttons", "OutlinedButton"),
    "OutlinedToggleButton": ("buttons", "OutlinedToggleButton"),
    "TextToggleButton": ("buttons", "TextToggleButton"),
    "TextButton": ("buttons", "TextButton"),
    "TonalToggleButton": ("buttons", "TonalToggleButton"),
    "TextField": ("text_fields", "TextField"),
    "FilledTextField": ("text_fields", "FilledTextField"),
    "OutlinedTextField": ("text_fields", "OutlinedTextField"),
    "NavigationRail": ("navigation_rail", "NavigationRail"),
    "RailItem": ("navigation_rail", "RailItem"),
    "MaterialOverlay": ("overlay", "MaterialOverlay"),
    "AlertDialog": ("dialogs", "AlertDialog"),
    "LoadingIndicator": ("loading_indicator", "LoadingIndicator"),
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
