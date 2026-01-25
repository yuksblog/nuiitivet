"""Intent resolution for overlay subclasses."""

from __future__ import annotations

from typing import Any, Protocol

from nuiitivet.navigation.route import Route
from nuiitivet.widgeting.widget import Widget


# MEMO consider standardizing IntentResolver across Overlay and Navigator


class IntentResolver(Protocol):
    """Resolves an intent object to a Widget or Route."""

    def resolve(self, intent: Any) -> Widget | Route: ...
