"""Runtime intents for application lifecycle and control."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExitAppIntent:
    """Intent to exit the application."""

    exit_code: int = 0


@dataclass(frozen=True, slots=True)
class CenterWindowIntent:
    """Intent to center the window on screen."""


@dataclass(frozen=True, slots=True)
class MaximizeWindowIntent:
    """Intent to maximize the window."""


@dataclass(frozen=True, slots=True)
class MinimizeWindowIntent:
    """Intent to minimize the window."""


@dataclass(frozen=True, slots=True)
class RestoreWindowIntent:
    """Intent to restore the window from maximized/minimized state."""


@dataclass(frozen=True, slots=True)
class FullScreenIntent:
    """Intent to request full screen mode."""


@dataclass(frozen=True, slots=True)
class CloseWindowIntent:
    """Intent to close the window."""


@dataclass(frozen=True, slots=True)
class MoveWindowIntent:
    """Intent to move the window to a specific position."""

    x: int
    y: int


@dataclass(frozen=True, slots=True)
class ResizeWindowIntent:
    """Intent to resize the window."""

    width: int
    height: int
