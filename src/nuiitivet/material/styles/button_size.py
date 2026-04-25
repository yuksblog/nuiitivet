"""Shared size tokens for Material Design 3 button-family widgets.

Provides the :data:`ButtonSize` literal and :data:`BUTTON_SIZE_TOKENS` table
used by ``ButtonStyle``, ``ToggleButtonStyle`` and ``ButtonGroupStyle``
factories, plus :data:`ICON_BUTTON_SIZE_TOKENS` for ``IconButtonStyle`` /
``IconToggleButtonStyle`` and :data:`FAB_SIZE_TOKENS` for ``Fab``.

All values follow the M3 component specs:
- https://m3.material.io/components/buttons/specs
- https://m3.material.io/components/icon-buttons/specs
- https://m3.material.io/components/floating-action-button/specs

The tables intentionally model the *round* shape variant only (circular
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


__all__ = [
    "ButtonSize",
    "ButtonSizeTokens",
    "BUTTON_SIZE_TOKENS",
    "IconButtonSizeTokens",
    "ICON_BUTTON_SIZE_TOKENS",
    "FabSize",
    "FabSizeTokens",
    "FAB_SIZE_TOKENS",
]


class IconButtonSizeTokens(TypedDict):
    """Typed view over a single :data:`ICON_BUTTON_SIZE_TOKENS` row."""

    container_height: int
    icon_size: int
    leading_space: int
    trailing_space: int
    corner_radius: int
    outline_width: float


# Values from https://m3.material.io/components/icon-buttons/specs
# (default leading/trailing spacing; round variant; circular corner radius).
ICON_BUTTON_SIZE_TOKENS: dict[ButtonSize, IconButtonSizeTokens] = {
    "xs": {
        "container_height": 32,
        "icon_size": 20,
        "leading_space": 6,
        "trailing_space": 6,
        "corner_radius": 16,
        "outline_width": 1.0,
    },
    "s": {
        "container_height": 40,
        "icon_size": 24,
        "leading_space": 8,
        "trailing_space": 8,
        "corner_radius": 20,
        "outline_width": 1.0,
    },
    "m": {
        "container_height": 56,
        "icon_size": 24,
        "leading_space": 16,
        "trailing_space": 16,
        "corner_radius": 28,
        "outline_width": 1.0,
    },
    "l": {
        "container_height": 96,
        "icon_size": 32,
        "leading_space": 32,
        "trailing_space": 32,
        "corner_radius": 48,
        "outline_width": 2.0,
    },
    "xl": {
        "container_height": 136,
        "icon_size": 40,
        "leading_space": 48,
        "trailing_space": 48,
        "corner_radius": 68,
        "outline_width": 3.0,
    },
}


FabSize = Literal["s", "m", "l"]
"""Framework-unified FAB size preset.

The literal values follow the project-wide ``s``/``m``/``l`` convention rather
than the MD3 spec wording (``FAB`` / ``Medium FAB`` / ``Large FAB``):

- ``"s"`` corresponds to the baseline 56dp FAB (MD3 "FAB").
- ``"m"`` corresponds to the 80dp Medium FAB.
- ``"l"`` corresponds to the 96dp Large FAB.

The deprecated 40dp Small FAB is intentionally not represented.
"""


class FabSizeTokens(TypedDict):
    """Typed view over a single :data:`FAB_SIZE_TOKENS` row."""

    container_height: int
    container_width: int
    icon_size: int
    corner_radius: int


# Values from https://m3.material.io/components/floating-action-button/specs.
# The Small FAB (40dp) is deprecated and excluded.
FAB_SIZE_TOKENS: dict[FabSize, FabSizeTokens] = {
    "s": {
        "container_height": 56,
        "container_width": 56,
        "icon_size": 24,
        "corner_radius": 16,
    },
    "m": {
        "container_height": 80,
        "container_width": 80,
        "icon_size": 28,
        "corner_radius": 20,
    },
    "l": {
        "container_height": 96,
        "container_width": 96,
        "icon_size": 36,
        "corner_radius": 28,
    },
}
