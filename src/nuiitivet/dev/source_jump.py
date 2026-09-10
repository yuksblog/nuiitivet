"""Source jump: ``Ctrl+Shift+Click`` opens the code that built a widget.

Modeless, unlike :mod:`.select_mode`. A mode earns its latch by carrying state
from one gesture to the next -- select mode's marks -- and a jump carries none:
the click opens the editor and is over. Making it a mode would put a mode entry
in front of every look at the code and confine it to one mode, when "where is
this built?" comes up in every state the app can be in. So it sits on the real
input handlers *ahead of* the modes, and the chord means the same thing outside
a mode and inside one.

The chord is the dev runner's prefix plus a click. ``Ctrl+Shift`` (``Cmd+Shift``
on macOS) is what every chord the runner claims starts with, and a
double-modified click is one applications almost never bind -- which is what
makes a modeless accelerator safe from a click the human meant for the app.
"""

from __future__ import annotations

import logging
import os
import weakref
from typing import Any, Callable, Optional

from nuiitivet._interaction.perception import pick_at
from nuiitivet.input.codes import (
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    resolve_modifiers as _resolve_physical_modifiers,
)

from .editor import open_at
from .select_mode import _DRAG_THRESHOLD
from .source import absolute_target

logger = logging.getLogger(__name__)


def _chord_held(modifier_keys: int) -> bool:
    physical = _resolve_physical_modifiers(int(modifier_keys))
    return bool(physical & (MOD_CTRL | MOD_META)) and bool(physical & MOD_SHIFT)


class SourceJump:
    """The source-jump accelerator for one window.

    Attach to the window as ``app._source_jump``; the backend's real input
    handlers offer every pointer and key event to it before any mode, and honour
    a ``True`` return as "consumed". Only a chorded press and its release are
    ever consumed; keys and plain motion are observed, never taken, so the
    accelerator costs an app nothing it did not already give up to the prefix.

    All hooks run on the UI thread.
    """

    def __init__(self) -> None:
        # Where a chorded press landed, so release can tell a click from a drag.
        self._press: Optional[tuple[float, float]] = None
        # Where the pointer last was, so a chord pressed while it is stationary
        # can still light up the widget it is over.
        self._pointer: Optional[tuple[float, float]] = None
        # The widget a chorded click would open, for the overlay. Weak: the
        # affordance must never keep a detached subtree alive.
        self._hover: Optional[Callable[[], Any]] = None
        # What the last jump did, shown in place of the hover caption and cleared
        # on the next pointer move, so it never lingers.
        self._notice: Optional[str] = None

    @property
    def hovered(self) -> Optional[Any]:
        """The widget the chord is held over, for the overlay to bracket."""
        return self._hover() if self._hover is not None else None

    @property
    def notice(self) -> Optional[str]:
        """What the last jump did, or why it did not happen. Transient."""
        return self._notice

    # --- keys -------------------------------------------------------------

    def on_key_press(self, app: Any, name: str, modifier_keys: int) -> bool:
        """Refresh the affordance as the chord goes down. Never consumes."""
        self._sync_hover(app, modifier_keys)
        return False

    def on_key_release(self, app: Any, name: str, modifier_keys: int) -> bool:
        """Refresh the affordance as the chord comes up. Never consumes."""
        self._sync_hover(app, modifier_keys)
        return False

    # --- pointer ----------------------------------------------------------

    def on_mouse_press(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Take a chorded press. Returns ``True`` when consumed.

        Decided on press, not release: the press has to be kept from the app
        here or the button under the cursor fires before the jump can happen.
        """
        if not _chord_held(modifier_keys):
            return False
        self._press = (float(x), float(y))
        return True

    def on_mouse_release(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Resolve a chorded press. Returns ``True`` when consumed.

        Travel beyond :data:`_DRAG_THRESHOLD` is a drag, and there is nothing to
        open for a drag; it is consumed all the same, since the app never saw
        the press it would be releasing.
        """
        press, self._press = self._press, None
        if press is None:
            return False
        if abs(float(x) - press[0]) > _DRAG_THRESHOLD or abs(float(y) - press[1]) > _DRAG_THRESHOLD:
            return True
        node = self._pick(app, press[0], press[1])
        if node is not None:
            self._jump(app, node)
        return True

    def on_mouse_motion(self, app: Any, x: float, y: float, modifier_keys: Optional[int] = None) -> bool:
        """Track the pointer, and the affordance while the chord is held.

        Consumes only while a chorded press is outstanding. A plain move
        carries no modifiers from the backend, so the window's own mask stands
        in for them.
        """
        self._pointer = (float(x), float(y))
        if self._notice is not None:
            self._notice = None
            _invalidate(app)
        if self._press is not None:
            return True
        if modifier_keys is None:
            modifier_keys = int(getattr(app, "modifier_keys", 0) or 0)
        self._sync_hover(app, modifier_keys)
        return False

    def _sync_hover(self, app: Any, modifier_keys: int) -> None:
        candidate = None
        if _chord_held(modifier_keys) and self._pointer is not None:
            candidate = self._pick(app, self._pointer[0], self._pointer[1])
        if candidate is self.hovered:
            return
        self._hover = _weak(candidate)
        _invalidate(app)

    def _pick(self, app: Any, x: float, y: float) -> Optional[Any]:
        root = getattr(app, "root", None)
        if root is None:
            return None
        try:
            return pick_at(root, x, y)
        except Exception:
            logger.debug("source_jump: pick_at failed", exc_info=True)
            return None

    def _jump(self, app: Any, node: Any) -> None:
        """Take the human to where ``node`` was built, and say what happened."""
        target = absolute_target(node)
        if target is None:
            self._notice = "no source recorded for this widget"
        else:
            path, line = target
            # Success is announced too, not just failure. The URL is
            # fire-and-forget: an opener succeeds whether or not anything is
            # registered for the scheme, so a jump that goes nowhere leaves no
            # trace at all. Naming the file is the only evidence the click was
            # received, which is what makes "nothing happened" readable as an
            # editor problem.
            reason = open_at(path, line)
            self._notice = reason or f"opening {os.path.basename(path)}:{line}"
        _invalidate(app)


def _invalidate(app: Any) -> None:
    try:
        app.invalidate()
    except Exception:
        logger.debug("source_jump: invalidate failed", exc_info=True)


def _weak(obj: Any) -> Optional[Callable[[], Any]]:
    if obj is None:
        return None
    try:
        return weakref.ref(obj)
    except TypeError:
        return None


__all__ = ["SourceJump"]
