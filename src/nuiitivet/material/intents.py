"""Material overlay intent types.

These intents are intended to be used by view models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AlertDialogIntent:
    """Intent for showing a Material Alert Dialog.

    Attributes:
        title (str | None): The title of the dialog.
        message (str | None): The message body of the dialog.
        icon (Any | None): The icon to display. Can be a Widget or other supported type.
    """

    title: str | None = None
    message: str | None = None
    icon: Any | None = None


@dataclass(frozen=True, slots=True)
class LoadingIntent:
    """Intent for showing a loading indicator via MaterialOverlay.

    This is a marker intent with no parameters.
    Visual properties should be configured via overlay_routes in MaterialApp.
    """

    pass


__all__ = ["LoadingIntent"]
