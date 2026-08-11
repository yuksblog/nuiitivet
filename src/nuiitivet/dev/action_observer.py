"""The bridge's :class:`~nuiitivet._interaction.action.ActionObserver`: draw what the assistant did.

The action verbs are silent on their own. The bridge is the driver that wants
them not to be: when the assistant drives the app the screen updates by itself,
and without a marker the human watching cannot tell which action caused it.

Every hook is best-effort. A marker is a courtesy to the human, so a failure to
draw one must never turn a working action into an error the assistant has to
reason about.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from nuiitivet._interaction.action import ActionObserver

logger = logging.getLogger(__name__)


class OverlayActionObserver:
    """Record each action as a short-lived marker on the action overlay."""

    def on_click(self, app: Any, x: float, y: float, *, target: Optional[str]) -> None:
        """Pulse at the clicked point, captioned with the target's key."""
        try:
            from . import action_overlay

            action_overlay.record_click(app, x, y, target=target)
        except Exception:
            logger.debug("action: click visualization failed", exc_info=True)

    def on_scroll(
        self,
        app: Any,
        x: float,
        y: float,
        *,
        dx: float,
        dy: float,
        target: Optional[str],
        verb: str,
    ) -> None:
        """Drift a chevron along the scroll direction.

        An unexplained scroll jump is worse than an unexplained click -- the
        whole screen moves -- so the direction is carried into the marker.
        """
        try:
            from . import action_overlay

            action_overlay.record_scroll(app, x, y, dx=dx, dy=dy, target=target, verb=verb)
        except Exception:
            logger.debug("action: scroll visualization failed", exc_info=True)

    def on_type(self, app: Any) -> None:
        """Place a caret marker at the focused widget (never the typed text)."""
        try:
            from . import action_overlay

            x, y = _focus_anchor(app)
            action_overlay.record_type(app, x=x, y=y)
        except Exception:
            logger.debug("action: type visualization failed", exc_info=True)

    def on_key(self, app: Any, key: str, modifiers: int) -> None:
        """Caption the keystroke as a human-readable modifier combo."""
        try:
            from . import action_overlay

            action_overlay.record_key(app, key, modifiers)
        except Exception:
            logger.debug("action: key visualization failed", exc_info=True)


def _focus_anchor(app: Any) -> tuple[Optional[float], Optional[float]]:
    """Anchor point for the ``type`` marker on the focused widget, or ``(None, None)``.

    The focus system reports the *editable text region* as the focused target,
    whose rect already starts at the text origin (no left padding). So the caret
    is placed just to the **left** of that origin -- before the first glyph --
    rather than inset into it (which would land the caret in the middle of the
    typed text) or at the geometric centre (a stray flash in a wide field).
    """
    target = getattr(app, "_focused_target", None)
    if target is None:
        return (None, None)
    rect = getattr(target, "last_rect", None) or getattr(target, "global_layout_rect", None)
    if rect is None or len(rect) < 4:
        return (None, None)
    x, y, w, h = rect
    # Sit the caret just left of the text origin so it never overlaps the glyphs.
    return (x - 6.0, y + h / 2.0)


# The observer is stateless -- every hook takes the app it draws into -- so the
# bridge binds this one instance into every verb. Annotated so a signature drift
# in the core protocol fails type-checking here rather than at a call site.
OVERLAY_OBSERVER: ActionObserver = OverlayActionObserver()
