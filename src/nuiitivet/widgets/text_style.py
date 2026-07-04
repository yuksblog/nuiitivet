"""Core text style.

Defines the minimal *visual* style surface for the core Text widget.

Layer boundaries (see ``docs/design/TYPOGRAPHY.md``):

* Typographic metrics (font size / line height / weight / tracking) live on the
  :class:`~nuiitivet.theme.type_scale.TypeScaleToken` passed as ``type_scale``.
* Layout / flow behavior (alignment, wrapping, overflow) lives on the Text
  widget itself.
* :class:`TextStyle` holds only the reusable visual look orthogonal to role and
  layout — today ``color`` and ``font_family``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Protocol

from nuiitivet.theme.types import ColorSpec


class TextStyleProtocol(Protocol):
    """Structural type for Text widget visual styling."""

    @property
    def color(self) -> ColorSpec: ...

    @property
    def font_family(self) -> str | None: ...


@dataclass(frozen=True)
class TextStyle:
    """Immutable visual style for the core Text widget.

    Typography comes from ``type_scale`` and alignment from the widget; this
    style intentionally carries neither.
    """

    color: ColorSpec = "#000000"
    font_family: str | None = None

    def copy_with(self, **changes: Any) -> "TextStyle":
        return replace(self, **changes)


__all__ = ["TextStyle", "TextStyleProtocol"]
