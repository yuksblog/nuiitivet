"""Flat widget API for nuiitivet.

Expose the flat widget implementations under `nuiitivet.widgets`.
"""

from __future__ import annotations

from .text import TextBase
from .icon import IconBase
from .size_transition import SizeTransition

__all__ = [
    "TextBase",
    "IconBase",
    "SizeTransition",
]
