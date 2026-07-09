"""Material design system root.

This is the single public import root for Material apps. It re-exports every
core symbol from :mod:`nuiitivet` *and* adds the Material widgets/styles, so a
single import gives access to everything::

    import nuiitivet.material as nv

    nv.Column(...)   # core symbol
    nv.Button(...)   # material symbol

Deep imports (``nuiitivet.material.buttons``, ``nuiitivet.material.styles.*``,
...) are internal and unsupported. See the "Imports" section of
``docs/guide/index.md``.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .badge import LargeBadge, SmallBadge
    from .app import MaterialApp as App
    from .divider import HorizontalDivider, VerticalDivider
    from .buttons import (
        Button,
        ExtendedFab,
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
    from .dialogs import BasicDialog
    from .loading_indicator import LoadingIndicator
    from .progress_indicators import (
        CircularProgressIndicator,
        IndeterminateCircularProgressIndicator,
        IndeterminateLinearProgressIndicator,
        LinearProgressIndicator,
    )
    from .menu import Menu, MenuDivider, MenuItem, SubMenuItem
    from .fab_menu import FabMenu, FabMenuItem
    from .intents import LoadingIntent
    from .icon import Icon
    from .navigation_rail import NavigationRail, RailItem
    from .selection_controls import Checkbox, RadioButton, RadioGroup, Switch
    from .slider import (
        HorizontalCenteredSlider,
        HorizontalRangeSlider,
        HorizontalSlider,
        VerticalCenteredSlider,
        VerticalRangeSlider,
        VerticalSlider,
    )
    from .symbols import Symbol, Symbols
    from .text_fields import TextField
    from .styles.text_field_style import TextFieldStyle
    from .styles.text_style import TextStyle
    from .styles.icon_style import IconStyle
    from .styles.divider_style import DividerStyle
    from .styles.toolbar_style import ToolbarStyle
    from .styles.progress_indicator_style import (
        CircularProgressIndicatorStyle,
        LinearProgressIndicatorStyle,
    )
    from .snackbar import Snackbar
    from .intents import BasicDialogIntent
    from .theme.color_role import ColorRole
    from .text import Text
    from .navigator import MaterialNavigator as Navigator
    from .overlay import MaterialOverlay as Overlay
    from .overlay import WhileLoading
    from .theme.material_theme import MaterialThemeFactory as ThemeFactory
    from .toolbar import DockedToolbar, HorizontalFloatingToolbar, VerticalFloatingToolbar
    from .tooltip_widgets import Tooltip, RichTooltip
    from .styles.sheet_style import SideSheetStyle, BottomSheetStyle, StandardSideSheetStyle
    from .sheet import SideSheet, BottomSheet, StandardSideSheet
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
    from .split_button import SplitButton
    from .styles.split_button_style import SplitButtonStyle
    from .transition_spec import MaterialTransitionSpec
    from .date_picker import (
        DatePicker,
        DockedDatePicker,
        ModalDatePicker,
        ModalDateRangePicker,
        ModalDateInput,
    )
    from .styles.date_picker_style import (
        DatePickerStyle,
        DockedDatePickerStyle,
        ModalDatePickerStyle,
        ModalDateRangePickerStyle,
        ModalDateInputStyle,
    )
    from nuiitivet.widgets.image import Image

__all__ = [
    "App",
    "ThemeFactory",
    "SmallBadge",
    "LargeBadge",
    "HorizontalDivider",
    "VerticalDivider",
    "Text",
    "Icon",
    "Symbols",
    "Symbol",
    "Checkbox",
    "RadioButton",
    "RadioGroup",
    "Switch",
    "HorizontalSlider",
    "VerticalSlider",
    "HorizontalCenteredSlider",
    "VerticalCenteredSlider",
    "HorizontalRangeSlider",
    "VerticalRangeSlider",
    "Card",
    "CardStyle",
    "AssistChip",
    "FilterChip",
    "InputChip",
    "SuggestionChip",
    "Button",
    "ToggleButton",
    "Fab",
    "ExtendedFab",
    "FabMenu",
    "FabMenuItem",
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
    "TextStyle",
    "IconStyle",
    "DividerStyle",
    "ToolbarStyle",
    "CircularProgressIndicatorStyle",
    "LinearProgressIndicatorStyle",
    "Snackbar",
    "BasicDialogIntent",
    "ColorRole",
    "NavigationRail",
    "RailItem",
    "Navigator",
    "Overlay",
    "WhileLoading",
    "BasicDialog",
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
    "HorizontalFloatingToolbar",
    "VerticalFloatingToolbar",
    "Tooltip",
    "RichTooltip",
    "MaterialTransitions",
    "MaterialTransitionSpec",
    "SideSheetStyle",
    "BottomSheetStyle",
    "StandardSideSheetStyle",
    "SideSheet",
    "BottomSheet",
    "StandardSideSheet",
    "GroupButton",
    "ButtonGroupPosition",
    "StandardButtonGroupStyle",
    "ConnectedButtonGroupStyle",
    "StandardButtonGroup",
    "ConnectedButtonGroup",
    "SplitButton",
    "SplitButtonStyle",
    "DatePicker",
    "DockedDatePicker",
    "ModalDatePicker",
    "ModalDateRangePicker",
    "ModalDateInput",
    "DatePickerStyle",
    "DockedDatePickerStyle",
    "ModalDatePickerStyle",
    "ModalDateRangePickerStyle",
    "ModalDateInputStyle",
    "FadeIn",
    "FadeOut",
    "ScaleIn",
    "ScaleOut",
    "SlideInVertically",
    "SlideOutVertically",
    "Image",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "App": ("app", "MaterialApp"),
    "ThemeFactory": ("theme", "MaterialThemeFactory"),
    "SmallBadge": ("badge", "SmallBadge"),
    "LargeBadge": ("badge", "LargeBadge"),
    "HorizontalDivider": ("divider", "HorizontalDivider"),
    "VerticalDivider": ("divider", "VerticalDivider"),
    "Text": ("text", "Text"),
    "Icon": ("icon", "Icon"),
    "Symbols": ("symbols", "Symbols"),
    "Symbol": ("symbols", "Symbol"),
    "Checkbox": ("selection_controls", "Checkbox"),
    "RadioButton": ("selection_controls", "RadioButton"),
    "RadioGroup": ("selection_controls", "RadioGroup"),
    "Switch": ("selection_controls", "Switch"),
    "HorizontalSlider": ("slider", "HorizontalSlider"),
    "VerticalSlider": ("slider", "VerticalSlider"),
    "HorizontalCenteredSlider": ("slider", "HorizontalCenteredSlider"),
    "VerticalCenteredSlider": ("slider", "VerticalCenteredSlider"),
    "HorizontalRangeSlider": ("slider", "HorizontalRangeSlider"),
    "VerticalRangeSlider": ("slider", "VerticalRangeSlider"),
    "Card": ("card", "Card"),
    "CardStyle": ("styles.card_style", "CardStyle"),
    "AssistChip": ("chip", "AssistChip"),
    "FilterChip": ("chip", "FilterChip"),
    "InputChip": ("chip", "InputChip"),
    "SuggestionChip": ("chip", "SuggestionChip"),
    "Button": ("buttons", "Button"),
    "ToggleButton": ("buttons", "ToggleButton"),
    "Fab": ("buttons", "Fab"),
    "ExtendedFab": ("buttons", "ExtendedFab"),
    "FabMenu": ("fab_menu", "FabMenu"),
    "FabMenuItem": ("fab_menu", "FabMenuItem"),
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
    "TextStyle": ("styles.text_style", "TextStyle"),
    "IconStyle": ("styles.icon_style", "IconStyle"),
    "DividerStyle": ("styles.divider_style", "DividerStyle"),
    "ToolbarStyle": ("styles.toolbar_style", "ToolbarStyle"),
    "CircularProgressIndicatorStyle": ("styles.progress_indicator_style", "CircularProgressIndicatorStyle"),
    "LinearProgressIndicatorStyle": ("styles.progress_indicator_style", "LinearProgressIndicatorStyle"),
    "Snackbar": ("snackbar", "Snackbar"),
    "BasicDialogIntent": ("intents", "BasicDialogIntent"),
    "ColorRole": ("theme.color_role", "ColorRole"),
    "NavigationRail": ("navigation_rail", "NavigationRail"),
    "RailItem": ("navigation_rail", "RailItem"),
    "Navigator": ("navigator", "MaterialNavigator"),
    "Overlay": ("overlay", "MaterialOverlay"),
    "WhileLoading": ("overlay", "WhileLoading"),
    "LoadingScope": ("overlay", "LoadingScope"),
    "BasicDialog": ("dialogs", "BasicDialog"),
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
    "HorizontalFloatingToolbar": ("toolbar", "HorizontalFloatingToolbar"),
    "VerticalFloatingToolbar": ("toolbar", "VerticalFloatingToolbar"),
    "Tooltip": ("tooltip_widgets", "Tooltip"),
    "RichTooltip": ("tooltip_widgets", "RichTooltip"),
    "MaterialLoadingIndicatorIntent": ("overlay_intents", "MaterialLoadingIndicatorIntent"),
    "MaterialTransitions": ("transition_spec", "MaterialTransitions"),
    "MaterialTransitionSpec": ("transition_spec", "MaterialTransitionSpec"),
    "SideSheetStyle": ("styles.sheet_style", "SideSheetStyle"),
    "BottomSheetStyle": ("styles.sheet_style", "BottomSheetStyle"),
    "StandardSideSheetStyle": ("styles.sheet_style", "StandardSideSheetStyle"),
    "SideSheet": ("sheet", "SideSheet"),
    "BottomSheet": ("sheet", "BottomSheet"),
    "StandardSideSheet": ("sheet", "StandardSideSheet"),
    "GroupButton": ("button_group", "GroupButton"),
    "ButtonGroupPosition": ("button_group", "ButtonGroupPosition"),
    "StandardButtonGroupStyle": ("styles.button_group_style", "StandardButtonGroupStyle"),
    "ConnectedButtonGroupStyle": ("styles.button_group_style", "ConnectedButtonGroupStyle"),
    "StandardButtonGroup": ("button_group", "StandardButtonGroup"),
    "ConnectedButtonGroup": ("button_group", "ConnectedButtonGroup"),
    "SplitButton": ("split_button", "SplitButton"),
    "SplitButtonStyle": ("styles.split_button_style", "SplitButtonStyle"),
    "DatePicker": ("date_picker", "DatePicker"),
    "DockedDatePicker": ("date_picker", "DockedDatePicker"),
    "ModalDatePicker": ("date_picker", "ModalDatePicker"),
    "ModalDateRangePicker": ("date_picker", "ModalDateRangePicker"),
    "ModalDateInput": ("date_picker", "ModalDateInput"),
    "DatePickerStyle": ("styles.date_picker_style", "DatePickerStyle"),
    "DockedDatePickerStyle": ("styles.date_picker_style", "DockedDatePickerStyle"),
    "ModalDatePickerStyle": ("styles.date_picker_style", "ModalDatePickerStyle"),
    "ModalDateRangePickerStyle": ("styles.date_picker_style", "ModalDateRangePickerStyle"),
    "ModalDateInputStyle": ("styles.date_picker_style", "ModalDateInputStyle"),
    "FadeIn": ("transitions", "FadeIn"),
    "FadeOut": ("transitions", "FadeOut"),
    "ScaleIn": ("transitions", "ScaleIn"),
    "ScaleOut": ("transitions", "ScaleOut"),
    "SlideInVertically": ("transitions", "SlideInVertically"),
    "SlideOutVertically": ("transitions", "SlideOutVertically"),
    "Image": ("..widgets.image", "Image"),
}


# --- Re-export every core symbol (Option B: single public root) ------------
# Core names are bound eagerly here so that ``import nuiitivet.material as nv``
# exposes ``nv.Column`` etc. Names that Material overrides (e.g. ``Navigator``
# -> ``MaterialNavigator``) are skipped and resolved lazily via ``_EXPORTS``.
import nuiitivet as _core  # noqa: E402 — must follow _EXPORTS to detect overrides

_reexported_core = [name for name in _core.__all__ if name not in _EXPORTS]
for _name in _reexported_core:
    globals()[_name] = getattr(_core, _name)

# Extend (do not reassign) so ``__all__`` stays a literal list that static
# analysers can read for the Material-specific exports.
__all__.extend(_reexported_core)

del _core, _name, _reexported_core


def __getattr__(name: str) -> Any:
    spec = _EXPORTS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = spec
    if module_name.startswith("."):
        module = importlib.import_module(module_name, package=__name__)
    else:
        module = importlib.import_module(f"{__name__}.{module_name}")
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_EXPORTS.keys()))
