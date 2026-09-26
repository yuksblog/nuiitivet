"""Intent resolution for overlay subclasses."""

from __future__ import annotations

from typing import Any, Protocol

from nuiitivet.widgeting.widget import Widget


# MEMO consider standardizing IntentResolver across Overlay and Navigator


class IntentResolver(Protocol):
    """Resolves an intent object to the widget the overlay presents."""

    def resolve(self, intent: Any) -> Widget: ...
