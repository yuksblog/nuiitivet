"""Generic input events.

These types are backend-agnostic and do not depend on the widget tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Optional

InputKind = Literal["pointer", "scroll", "key", "focus"]
InputHandler = Callable[[Any], bool]


@dataclass(frozen=True)
class KeyInputEvent:
    """Normalized key input delivered to widgets."""

    key: str
    modifier_keys: int = 0
    released: bool = False
    """True when the event is a key release rather than a key press."""


@dataclass(frozen=True)
class FocusEvent:
    """Represents focus transitions for widgets."""

    gained: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class FileDropEvent:
    """OS file paths dropped onto the window, delivered to a widget.

    ``x`` / ``y`` are window coordinates of the drop point (top-left origin,
    logical pixels); ``local_x`` / ``local_y`` are relative to the receiving
    widget's top-left and are populated at delivery time.
    """

    paths: tuple[Path, ...]
    x: float
    y: float
    local_x: Optional[float] = None
    local_y: Optional[float] = None
