"""Theme subsystem: color roles, palette utilities, and manager."""

from __future__ import annotations

from .theme import (
    ColorValue,
    Theme,
)
from .manager import ThemeManager, manager
from .types import ColorLike, ColorSpec, ColorToken, ThemeExtension

__all__ = [
    "ColorValue",
    "Theme",
    "ThemeManager",
    "manager",
    "ThemeExtension",
    "ColorLike",
    "ColorSpec",
    "ColorToken",
]
