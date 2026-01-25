"""Core text style.

Defines the minimal style surface required by the core Text widget.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal, Protocol

from nuiitivet.theme.types import ColorSpec


class TextStyleProtocol(Protocol):
    """Structural type for Text widget styling."""

    @property
    def font_size(self) -> int: ...

    @property
    def color(self) -> ColorSpec: ...

    @property
    def font_family(self) -> str | None: ...

    @property
    def text_alignment(self) -> Literal["start", "center", "end"]: ...

    @property
    def overflow(self) -> Literal["visible", "clip", "ellipsis"]: ...


@dataclass(frozen=True)
class TextStyle:
    """Immutable style for the core Text widget."""

    font_size: int = 14
    color: ColorSpec = "#000000"
    font_family: str | None = None
    text_alignment: Literal["start", "center", "end"] = "start"
    overflow: Literal["visible", "clip", "ellipsis"] = "visible"

    def copy_with(self, **changes: Any) -> "TextStyle":
        return replace(self, **changes)


__all__ = ["TextStyle", "TextStyleProtocol"]
