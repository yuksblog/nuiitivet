"""Material Theme factory."""

from __future__ import annotations

from typing import Tuple

from nuiitivet.theme.theme import Theme
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.material.theme.palette import from_seed


class MaterialTheme:
    """Factory for creating Themes with Material Design configuration."""

    @staticmethod
    def from_seed(seed_color: str, mode: str = "light", name: str = "") -> Theme:
        """Create Material theme from seed color."""
        light_roles, dark_roles = from_seed(seed_color)
        roles = dark_roles if mode == "dark" else light_roles

        material_data = MaterialThemeData(roles=roles)
        return Theme(mode=mode, extensions=[material_data], name=name)

    @staticmethod
    def light(seed_color: str) -> Theme:
        return MaterialTheme.from_seed(seed_color, mode="light")

    @staticmethod
    def dark(seed_color: str) -> Theme:
        return MaterialTheme.from_seed(seed_color, mode="dark")

    @staticmethod
    def from_seed_pair(seed_color: str, name: str = "") -> Tuple[Theme, Theme]:
        """Create light and dark themes from a seed color."""
        return (
            MaterialTheme.from_seed(seed_color, mode="light", name=name),
            MaterialTheme.from_seed(seed_color, mode="dark", name=name),
        )
