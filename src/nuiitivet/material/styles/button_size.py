"""Shared size tokens for Material Design 3 button-family widgets.

Provides the :data:`ButtonSize` literal and :data:`BUTTON_SIZE_TOKENS` table
used by ``ButtonStyle``, ``ToggleButtonStyle`` and ``ButtonGroupStyle``
factories.  All values follow the M3 Button spec:
https://m3.material.io/components/buttons/specs

The table intentionally models the *round* shape variant only (circular
corner radius).  Shape morphing and square variants are out of scope for
the initial style-driven refactor.
"""

from __future__ import annotations

from typing import Literal, TypedDict

ButtonSize = Literal["xs", "s", "m", "l", "xl"]
"""M3 button size preset."""


class ButtonSizeTokens(TypedDict):
    """Typed view over a single :data:`BUTTON_SIZE_TOKENS` row."""

    container_height: int
    leading_space: int
    trailing_space: int
    icon_label_space: int
    icon_size: int
    label_font_size: int
    outline_width: float
    corner_radius: int


BUTTON_SIZE_TOKENS: dict[ButtonSize, ButtonSizeTokens] = {
    "xs": {
        "container_height": 32,
        "leading_space": 12,
        "trailing_space": 12,
        "icon_label_space": 8,
        "icon_size": 20,
        "label_font_size": 14,
        "outline_width": 1.0,
        "corner_radius": 16,
    },
    "s": {
        "container_height": 40,
        "leading_space": 16,
        "trailing_space": 16,
        "icon_label_space": 8,
        "icon_size": 20,
        "label_font_size": 14,
        "outline_width": 1.0,
        "corner_radius": 20,
    },
    "m": {
        "container_height": 56,
        "leading_space": 24,
        "trailing_space": 24,
        "icon_label_space": 8,
        "icon_size": 24,
        "label_font_size": 16,
        "outline_width": 1.0,
        "corner_radius": 28,
    },
    "l": {
        "container_height": 96,
        "leading_space": 48,
        "trailing_space": 48,
        "icon_label_space": 12,
        "icon_size": 32,
        "label_font_size": 24,
        "outline_width": 2.0,
        "corner_radius": 48,
    },
    "xl": {
        "container_height": 136,
        "leading_space": 64,
        "trailing_space": 64,
        "icon_label_space": 16,
        "icon_size": 40,
        "label_font_size": 32,
        "outline_width": 3.0,
        "corner_radius": 68,
    },
}


__all__ = ["ButtonSize", "ButtonSizeTokens", "BUTTON_SIZE_TOKENS"]
