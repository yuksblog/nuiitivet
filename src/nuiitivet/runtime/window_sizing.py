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
    """Represents how a window requests its initial size along an axis.

    Construct with :meth:`fixed` or :meth:`auto`.
    """

    kind: WindowSizingKind
    value: float = 0.0

    @classmethod
    def fixed(cls, value: float) -> "WindowSizing":
        """Return a size of *value* logical pixels."""
        return cls("fixed", float(value))

    @classmethod
    def auto(cls) -> "WindowSizing":
        """Return a size that follows the content's preferred size."""
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
    """Where the OS window opens on a screen.

    From an alignment string: `alignment`.

    Attributes:
        alignment_key: A nine-point alignment, the layout system's vocabulary.
            It places the window's outer frame, title bar included, inside the
            screen's work area: the part not covered by the taskbar, the menu
            bar or the dock.
        offset: Screen pixels added after alignment; $+x$ is right, $+y$ is down.
        screen_index: The screen to open on; out-of-range values use the last screen.
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


WindowPositionLike = WindowPosition | str


def parse_window_position(value: WindowPositionLike) -> WindowPosition:
    if isinstance(value, WindowPosition):
        return value
    if isinstance(value, str):
        return WindowPosition(value)
    raise TypeError("WindowPositionLike must be WindowPosition or an alignment string")


__all__ = [
    "WindowSizing",
    "WindowSizingKind",
    "WindowSizingLike",
    "parse_window_sizing",
    "WindowPosition",
    "WindowPositionLike",
    "parse_window_position",
]
