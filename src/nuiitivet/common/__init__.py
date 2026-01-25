"""Shared internal utilities.

This package is intended for helpers used across multiple layers (core/layout/rendering)
without introducing import cycles.
"""

from .logging_once import debug_once, exception_once

__all__ = [
    "debug_once",
    "exception_once",
]
