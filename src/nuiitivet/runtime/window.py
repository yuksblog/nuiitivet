"""Window sizing and positioning types.

These types are intentionally separate from widget layout Sizing.
Window sizing is resolved before layout and uses absolute pixels or "auto".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple

from nuiitivet.layout.alignment import NINE_POINT_ALIGNMENTS


WindowSizingKind = Literal["fixed", "auto"]


@dataclass(frozen=True, slots=True)
class WindowSizing:
    """Represents how a window requests its initial size along an axis."""

    kind: WindowSizingKind
    value: float = 0.0

    @classmethod
    def fixed(cls, value: float) -> "WindowSizing":
        return cls("fixed", float(value))

    @classmethod
    def auto(cls) -> "WindowSizing":
        return cls("auto", 0.0)


WindowSizingLike = WindowSizing | int | Literal["auto"]


def parse_window_sizing(value: WindowSizingLike) -> WindowSizing:
    if isinstance(value, WindowSizing):
        return value
    if isinstance(value, int):
        return WindowSizing.fixed(value)
    if value == "auto":
        return WindowSizing.auto()
    raise TypeError("WindowSizingLike must be WindowSizing, int, or 'auto'")


@dataclass(frozen=True, slots=True)
class WindowPosition:
    """Represents how the OS window is positioned within a screen.

    Coordinates:
    - `alignment` uses the 9-point vocabulary from the layout system.
    - `offset` is applied after alignment in logical pixels.
      The offset uses UI coordinates: $+x$ is right, $+y$ is down.
    """

    alignment_key: str
    offset: Tuple[float, float] = (0.0, 0.0)
    screen_index: int = 0

    def __post_init__(self) -> None:
        key = str(self.alignment_key).strip().lower().replace("_", "-")
        if key not in NINE_POINT_ALIGNMENTS:
            allowed = ", ".join(sorted(NINE_POINT_ALIGNMENTS))
            raise ValueError(f"Invalid alignment: {self.alignment_key!r}. Allowed: {allowed}")

        dx, dy = self.offset
        object.__setattr__(self, "alignment_key", key)
        object.__setattr__(self, "offset", (float(dx), float(dy)))
        object.__setattr__(self, "screen_index", int(self.screen_index))

    @classmethod
    def alignment(
        cls,
        alignment: str,
        *,
        offset: Tuple[float, float] = (0.0, 0.0),
        screen_index: int = 0,
    ) -> "WindowPosition":
        return cls(alignment_key=alignment, offset=offset, screen_index=screen_index)


__all__ = [
    "WindowSizing",
    "WindowSizingKind",
    "WindowSizingLike",
    "parse_window_sizing",
    "WindowPosition",
]
