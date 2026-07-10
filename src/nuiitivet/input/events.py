"""Generic input events.

These types are backend-agnostic and do not depend on the widget tree.
"""

from __future__ import annotations

from dataclasses import dataclass
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
