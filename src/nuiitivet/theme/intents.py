"""Theme-related intents for the App dispatch system.

CQRS design: reads go through ``Theme.of(context)``, writes go through
``App.of(context).dispatch(intent)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .theme import Theme


@dataclass(frozen=True, slots=True)
class ThemeModeIntent:
    """Switch the active theme.

    Args:
        theme: A theme name registered via :class:`ThemeRegistryIntent`, or
            ``"light"`` / ``"dark"`` as built-in aliases, or a :class:`Theme`
            instance to apply directly without touching the registry.
    """

    theme: "str | Theme"


@dataclass(frozen=True, slots=True)
class ThemeRegistryIntent:
    """Register named custom themes so they can be referenced by name.

    Args:
        themes: Mapping of name → :class:`Theme` to add to the registry.
            Subsequent :class:`ThemeModeIntent` calls can refer to these names.
    """

    themes: dict[str, "Theme"] = field(default_factory=dict)


__all__ = ["ThemeModeIntent", "ThemeRegistryIntent"]
