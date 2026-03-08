"""Image content fit mode definitions."""

from __future__ import annotations

from typing import Literal


Fit = Literal["contain", "cover", "fill", "none"]


__all__ = ["Fit"]
