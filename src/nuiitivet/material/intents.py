"""Material overlay intent types.

These intents are intended to be used by view models.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoadingIntent:
    """Intent for showing a loading indicator via MaterialOverlay.

    This is a marker intent with no parameters.
    Visual properties should be configured via overlay_routes in MaterialApp.
    """

    pass


__all__ = ["LoadingIntent"]
