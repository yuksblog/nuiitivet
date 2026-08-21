"""Inspect mode: the gesture layer that turns the human's clicks into designations (#591).

The input half of :mod:`nuiitivet.dev.selection`. It sits on the *real* input
handlers -- the layer the human drives, which the assistant's synthesized actions
bypass -- so a designation is always the human's, with no need to tag synthetic
events. Same placement, and the same reason, as
:class:`~nuiitivet.dev.interaction.InteractionRecorder`.

The mode is **latched** (``Ctrl+Shift+C`` on, ``Enter`` or ``Esc`` off) rather
than held. A
held modifier cannot carry a persistent affordance and cannot survive a
multi-pick sequence, and ``Shift`` -- the obvious candidate -- is the modifier
applications own most (see ``_COMMAND_MODS`` in :mod:`.interaction`). The
shortcut matches the one Chrome DevTools uses for the same gesture.

While latched, input is **consumed**: a click is a designation, not an
interaction, and letting it also reach the app would fire the button the human
was merely pointing at.

Leaving is a decision: ``Enter`` keeps the session's work, ``Esc`` throws it
away. That is what those keys mean everywhere, and an earlier design that made
leaving an implicit commit had no way to abandon a session at all -- five marks
took five ``Backspace`` presses to undo.
"""

from __future__ import annotations

import logging
import os
import weakref
from typing import Any, Callable, Optional

from nuiitivet._interaction.perception import ancestors, pick_at
from nuiitivet.input.codes import (
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    resolve_modifiers as _resolve_physical_modifiers,
)

from .editor import open_at
from .interaction import InteractionJournal
from .selection import Selection
from .source import absolute_target

logger = logging.getLogger(__name__)

# Pointer travel, in logical pixels, below which a press/release pair is a click
# rather than a drag. Discriminating on *release* is what lets one gesture serve
# both: the press handler never has to commit to a reading it cannot yet make.
_DRAG_THRESHOLD = 4.0

# The key that enters the mode, with either accelerator -- Ctrl on Windows/Linux,
# Cmd on macOS -- matching how the same shortcut is spelled per platform.
_ENTER_KEY = "c"


class InspectMode:
    """Latched designation mode for one running app.

    Attach to the app as ``app._inspect_mode``; the backend's real input handlers
    call the ``on_*`` hooks and honour their return value, which is ``True`` when
    the mode consumed the event and the app must not also see it.

    All hooks run on the UI thread. The :class:`Selection` they write to takes
    its own lock, so bridge reads on HTTP worker threads are safe.
    """

    def __init__(
        self,
        selection: Selection,
        *,
        journal: Optional[InteractionJournal] = None,
    ) -> None:
        self._selection = selection
        # Content-free marker so an assistant catching up on the journal notices
        # a designation happened without the journal carrying the payload.
        self._journal = journal
        # Where the press landed, so release can tell a click from a drag.
        self._press: Optional[tuple[float, float]] = None
        # The node the ancestor walk started from, so `down` can retrace the way
        # `up` came. Weak: the walk must never keep a detached subtree alive.
        self._anchor: Optional[Callable[[], Any]] = None
        # The node under the cursor, for the overlay's hover highlight.
        self._hover: Optional[Callable[[], Any]] = None
        # The rect a drag has swept so far, for the overlay's rubber band.
        self._band: Optional[tuple[float, float, float, float]] = None
        # A one-off message shown in place of the hover caption, for the cases a
        # jump cannot happen. Cleared on the next move, so it never lingers.
        self._notice: Optional[str] = None

    @property
    def selection(self) -> Selection:
        """The designation buffer this mode writes to."""
        return self._selection

    @property
    def active(self) -> bool:
        """Whether the mode is latched on."""
        return self._selection.active

    @property
    def hovered(self) -> Optional[Any]:
        """The pick candidate under the cursor, for the overlay to highlight."""
        return self._hover() if self._hover is not None else None

    @property
    def band(self) -> Optional[tuple[float, float, float, float]]:
        """The rect a drag has swept so far, or ``None`` when not dragging."""
        return self._band

    @property
    def notice(self) -> Optional[str]:
        """Why the last jump did not happen, for the overlay to show. Transient."""
        return self._notice

    # --- keys -------------------------------------------------------------

    def on_key_press(self, app: Any, name: str, modifier_keys: int) -> bool:
        """Handle a key. Returns ``True`` when the mode consumed it.

        While latched, **every** key is consumed. A half-passed-through keyboard
        would let the app act on input the human meant for the picker, and the
        mode's own exits (``Enter`` / ``Esc``) are always available.
        """
        key = str(name).strip().lower()
        physical = _resolve_physical_modifiers(int(modifier_keys))

        if not self.active:
            accel = bool(physical & (MOD_CTRL | MOD_META))
            if key == _ENTER_KEY and accel and physical & MOD_SHIFT:
                self._enter(app)
                return True
            return False

        if key == "escape":
            self._discard(app)
        elif key == "enter":
            self._commit(app)
        elif key == "backspace":
            # Ctrl (or Cmd) escalates "remove one" to "remove all", the way an
            # accelerator escalates a backspace to a whole word in a text field.
            # Both land *inside* the session, so ``Esc`` undoes either -- which
            # is what makes clearing safe to reach for.
            if physical & (MOD_CTRL | MOD_META):
                self._selection.clear()
            else:
                self._selection.remove_last()
            self._changed(app)
        elif key == "up":
            self._walk_up(app)
        elif key == "down":
            self._walk_down(app)
        return True

    def on_key_release(self, app: Any, name: str, modifier_keys: int) -> bool:
        """Swallow the key-up half while latched. ``True`` when consumed.

        The press half is consumed above, so letting its release through would
        deliver a lone key-up to the focused widget -- a widget that acts on
        key-up would fire from a keystroke the app never saw the start of.
        """
        return self.active

    def _enter(self, app: Any) -> None:
        self._selection.enter()
        self._press = None
        self._hover = None
        self._band = None
        self._changed(app, note=False)

    def _commit(self, app: Any) -> None:
        self._selection.commit()
        self._reset(app)

    def _discard(self, app: Any) -> None:
        self._selection.discard()
        self._reset(app)

    def _reset(self, app: Any) -> None:
        self._press = None
        self._hover = None
        self._band = None
        self._anchor = None
        self._changed(app)

    # --- pointer ----------------------------------------------------------

    def on_mouse_press(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Record where a press landed. Returns ``True`` when the mode consumed it."""
        if not self.active:
            return False
        self._press = (float(x), float(y))
        return True

    def on_mouse_release(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Resolve the gesture. Returns ``True`` when the mode consumed it.

        Travel below :data:`_DRAG_THRESHOLD` is a click, which toggles the widget
        under the cursor; anything further is a drag, which designates the area
        it swept. Deciding here rather than on press is what lets one gesture
        serve both without the press handler committing to a reading it cannot
        yet make.
        """
        if not self.active:
            return False
        press, self._press = self._press, None
        self._band = None
        if press is None:
            return True
        if abs(float(x) - press[0]) > _DRAG_THRESHOLD or abs(float(y) - press[1]) > _DRAG_THRESHOLD:
            # A modified press that travelled is still just a drag: the accelerator
            # only ever means "jump instead of designate", and there is nothing to
            # jump to for an area.
            self._selection.add_region(_normalized(press, (float(x), float(y))))
            self._changed(app)
            return True

        root = getattr(app, "root", None)
        if root is None:
            return True
        node = self._pick(root, press[0], press[1])
        if node is None:
            return True
        if _resolve_physical_modifiers(int(modifier_keys)) & (MOD_CTRL | MOD_META):
            # Go to the source instead of designating (#593). Browsing ten
            # widgets' code must not leave ten marks behind to clear.
            self._open_source(app, node)
            return True
        self._selection.toggle(node, root=root)
        self._anchor = _weak(node)
        self._changed(app)
        return True

    def on_mouse_motion(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Track the pick candidate, or the rubber band mid-drag.

        Returns ``True`` when the mode consumed it. The two cases are told apart
        by whether a press is outstanding, so the backend can route a plain move
        and a drag to the same hook.
        """
        if not self.active:
            return False
        if self._notice is not None:
            self._notice = None
            _invalidate(app)
        if self._press is not None:
            band = _normalized(self._press, (float(x), float(y)))
            if band != self._band:
                self._band = band
                _invalidate(app)
            return True
        root = getattr(app, "root", None)
        candidate = self._pick(root, x, y) if root is not None else None
        if candidate is self.hovered:
            # A mouse move that does not change the candidate would otherwise
            # request a repaint per motion event.
            return True
        self._hover = _weak(candidate)
        _invalidate(app)
        return True

    def _pick(self, root: Any, x: float, y: float) -> Optional[Any]:
        try:
            return pick_at(root, x, y)
        except Exception:
            logger.debug("inspect: pick_at failed", exc_info=True)
            return None

    # --- ancestor walk ----------------------------------------------------

    def _walk_up(self, app: Any) -> None:
        """Replace the newest member with its parent."""
        current = self._selection.last()
        if current is None:
            return
        chain = ancestors(current)
        if not chain:
            return
        self._selection.replace_last(chain[0], root=getattr(app, "root", None))
        self._changed(app)

    def _walk_down(self, app: Any) -> None:
        """Step back toward the node the walk started from.

        ``down`` is only meaningful as the inverse of ``up``: a node has many
        children and no way to guess which the human meant, but it has exactly
        one child on the path back to where they started. Without an anchor --
        the walk never went up -- there is nothing to descend to.
        """
        current = self._selection.last()
        anchor = self._anchor() if self._anchor is not None else None
        if current is None or anchor is None or anchor is current:
            return
        previous = anchor
        for node in ancestors(anchor):
            if node is current:
                self._selection.replace_last(previous, root=getattr(app, "root", None))
                self._changed(app)
                return
            previous = node

    def _open_source(self, app: Any, node: Any) -> None:
        """Take the human to where ``node`` was built (#593).

        Deliberately does *not* leave inspect mode. Reading several widgets'
        code in a row is the normal use, and leaving would make each one cost a
        re-entry. That is only safe because the overlay repaints on every state
        change, so coming back from the editor shows the badge that says the mode
        is still on.
        """
        target = absolute_target(node)
        if target is None:
            self._notice = "no source recorded for this widget"
        else:
            path, line = target
            # Success is announced too, not just failure -- and since #597 that
            # matters more, not less. The URL is fire-and-forget: an opener
            # succeeds whether or not anything is registered for the scheme, so
            # a jump that goes nowhere leaves no trace at all. Naming the file
            # is the only evidence the click was received, which is what makes
            # "nothing happened" readable as an editor problem.
            reason = open_at(path, line)
            self._notice = reason or f"opening {os.path.basename(path)}:{line}"
        _invalidate(app)

    # --- change notification ----------------------------------------------

    def _changed(self, app: Any, *, note: bool = True) -> None:
        """Repaint, and leave a journal marker.

        The repaint is not optional. The overlay is a pure function of this
        state read at paint time, so a state change that requests no frame is
        simply invisible -- the mode latches, clicks stop reaching the app, and
        the human sees no reason why until something else happens to force a
        redraw.
        """
        _invalidate(app)
        if note and self._journal is not None:
            try:
                self._journal.record_select()
            except Exception:
                logger.debug("inspect: recording the select marker failed", exc_info=True)


def _invalidate(app: Any) -> None:
    """Ask for a frame, so the overlay reflects the change that just happened."""
    try:
        app.invalidate()
    except Exception:
        logger.debug("inspect: invalidate failed", exc_info=True)


def _normalized(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float, float, float]:
    """Return the rect two corners span, whichever direction the drag went."""
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return (x0, y0, x1 - x0, y1 - y0)


def _weak(obj: Any) -> Optional[Callable[[], Any]]:
    if obj is None:
        return None
    try:
        return weakref.ref(obj)
    except TypeError:
        return None


__all__ = ["InspectMode"]
