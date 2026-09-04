"""MD3 type-scale tokens.

A :class:`TypeScaleToken` bundles the typographic metrics that Material Design 3
varies **per type-scale role** — font size, line height, weight and tracking.
The :class:`TypeScale` namespace exposes the 15 baseline MD3 roles as static
tokens.

This is deliberately a *structured* value, not a bare ``int``:

* A role carries more than a size (line height / weight / tracking), so Text
  needs the whole bundle.
* Being a struct (not an ``int``) means a type-scale token does **not** satisfy
  ``Icon(size=...)`` (a ``SizingLike``). That collision is blocked at the type
  level — MD3 does not define a type-scale -> icon-size mapping, and a role's
  font size (e.g. 16) is not an icon optical size (20/24/40/48).

Reference values: https://m3.material.io/styles/typography/type-scale-tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

# Ratio used to derive a line height when only a raw size is known
# (``TypeScaleToken.from_size``). Mirrors the historical Text line spacing.
_DEFAULT_LINE_HEIGHT_RATIO = 1.25


@dataclass(frozen=True)
class TypeScaleToken:
    """Immutable typographic metrics for a single type-scale role.

    Attributes:
        font_size: Glyph size in px.
        line_height: Absolute line height in px (faithful to MD3 tokens, not a
            multiplier). Only affects multi-line layout.
        weight: Font weight (100-900); MD3 roles use 400 (Regular) or 500
            (Medium).
        tracking: Letter spacing in px; may be negative (e.g. Display Large).
    """

    font_size: float
    line_height: float
    weight: int = 400
    tracking: float = 0.0

    def copy_with(self, **changes: Any) -> "TypeScaleToken":
        """Return a new token with the given fields replaced.

        Example:
            TypeScale.TITLE_MEDIUM.copy_with(weight=700)
        """
        return replace(self, **changes)

    @classmethod
    def from_size(
        cls,
        font_size: float,
        *,
        line_height: float | None = None,
        weight: int = 400,
        tracking: float = 0.0,
    ) -> "TypeScaleToken":
        """Build a token from a raw size when no semantic role applies.

        Intended for config-driven numeric sizes (e.g. a widget's ``*Style``
        exposing ``label_font_size``), not for public typography. ``line_height``
        defaults to ``font_size * 1.25`` to preserve historical spacing.
        """
        lh = line_height if line_height is not None else float(font_size) * _DEFAULT_LINE_HEIGHT_RATIO
        return cls(font_size=float(font_size), line_height=lh, weight=weight, tracking=tracking)


class TypeScale:
    """The 15 baseline Material Design 3 type-scale roles.

    Values follow the MD3 2021 baseline type scale
    (https://m3.material.io/styles/typography/type-scale-tokens):
    ``(font_size, line_height, weight, tracking)``.
    """

    # Display
    DISPLAY_LARGE = TypeScaleToken(57, 64, 400, -0.25)
    DISPLAY_MEDIUM = TypeScaleToken(45, 52, 400, 0.0)
    DISPLAY_SMALL = TypeScaleToken(36, 44, 400, 0.0)

    # Headline
    HEADLINE_LARGE = TypeScaleToken(32, 40, 400, 0.0)
    HEADLINE_MEDIUM = TypeScaleToken(28, 36, 400, 0.0)
    HEADLINE_SMALL = TypeScaleToken(24, 32, 400, 0.0)

    # Title
    TITLE_LARGE = TypeScaleToken(22, 28, 400, 0.0)
    TITLE_MEDIUM = TypeScaleToken(16, 24, 500, 0.15)
    TITLE_SMALL = TypeScaleToken(14, 20, 500, 0.1)

    # Body
    BODY_LARGE = TypeScaleToken(16, 24, 400, 0.5)
    BODY_MEDIUM = TypeScaleToken(14, 20, 400, 0.25)
    BODY_SMALL = TypeScaleToken(12, 16, 400, 0.4)

    # Label
    LABEL_LARGE = TypeScaleToken(14, 20, 500, 0.1)
    LABEL_MEDIUM = TypeScaleToken(12, 16, 500, 0.5)
    LABEL_SMALL = TypeScaleToken(11, 16, 500, 0.5)


# Default role used when a Text is created without an explicit type_scale.
DEFAULT_TYPE_SCALE = TypeScale.BODY_MEDIUM


__all__ = ["TypeScaleToken", "TypeScale", "DEFAULT_TYPE_SCALE"]
