"""Scrollbar behavior definitions.

Lives in the framework-common ``scrolling`` package alongside the other
scrollbar config types (``ScrollbarStyle`` for geometry, ``ScrollbarThemeData``
for colors). This one carries the interaction/temporal config and, like its
siblings, has no design-system dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional

from nuiitivet.common.logging_once import exception_once

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrollbarBehavior:
    """Immutable behavior configuration for scrollbar widgets."""

    auto_hide: bool = True
    hide_delay: float = 1.0
    fade_duration: float = 0.15
    hide_threshold: float = 0.25
    track_click_behavior: str = "jump"
    interactive: bool = True
    hit_slop: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "hide_delay", max(0.0, float(self.hide_delay)))
        object.__setattr__(self, "fade_duration", max(0.0, float(self.fade_duration)))
        object.__setattr__(self, "hide_threshold", max(0.0, min(1.0, float(self.hide_threshold))))
        try:
            if self.track_click_behavior not in ("none", "page", "jump"):
                object.__setattr__(self, "track_click_behavior", "none")
        except Exception:
            exception_once(logger, "scrollbar_behavior_post_init_exc", "ScrollbarBehavior.__post_init__ failed")
            object.__setattr__(self, "track_click_behavior", "none")
