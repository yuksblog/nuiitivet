"""Comment mode: the gesture layer that turns the human's clicks and typing into comments.

The input half of :mod:`nuiitivet.dev.comments`, on the backend's real input
handlers, which the agent's synthesized actions bypass: a comment is always
the human's. Latched on ``Ctrl+Shift+C``; while latched every event is consumed,
so a click marks the widget instead of firing it.

A click marks a widget and a drag an area. ``Enter`` on a mark just made, or a
click on any mark's numbered badge, opens the inline field (:mod:`.inline_field`)
on it; the ``Enter`` is offered once per new mark and only opening the field,
losing the mark or making a newer one ends the offer. In the field ``Enter``
writes, ``Esc`` closes it unwritten, and a click elsewhere writes. Otherwise
``Enter`` keeps the session and leaves, ``Esc`` discards it, and ``Ctrl+Z`` /
``Ctrl+Shift+Z`` step through its changes. ``Backspace`` is unbound: in layout
edit mode it deletes a widget from the source.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from nuiitivet._interaction.perception import visible_rect

from .comments import Comments
from .gesture import accel_held, child_toward, chord_held, invalidate, parent_of, pick, travelled, weak
from .hud import SEPARATOR, Placement
from .inline_field import InlineField
from .interaction import InteractionJournal

logger = logging.getLogger(__name__)


# The key that enters the mode. ``C`` for *comment*.
_ENTER_KEY = "c"
# Layout edit mode's key, let through while latched so the two modes switch directly.
_LAYOUT_KEY = "e"
#: The numbered badge at a mark's top-left corner. A press inside the disc clicks
#: it; no slack, since the widget under it may be no taller than the disc.
BADGE_RADIUS = 10.0

Rect = tuple[float, float, float, float]


@dataclass
class Writing:
    """The field open over one mark, for the overlay to draw: which mark, and its text."""

    index: int
    field: InlineField


class CommentMode:
    """Latched comment mode for one running app.

    Attached as ``app._comment_mode``. The backend calls the ``on_*`` hooks on
    the UI thread; ``True`` means the event was consumed and the app must not
    see it.
    """

    def __init__(
        self,
        comments: Comments,
        *,
        journal: Optional[InteractionJournal] = None,
    ) -> None:
        self._comments = comments
        self._journal = journal
        # Where the press landed, so release can tell a click from a drag.
        self._press: Optional[tuple[float, float]] = None
        # The node the ancestor walk started from, so `down` retraces `up`. Weak.
        self._anchor: Optional[Callable[[], Any]] = None
        # The node under the cursor, for the overlay's hover highlight.
        self._hover: Optional[Callable[[], Any]] = None
        # The rect a drag has swept so far, for the overlay's rubber band.
        self._band: Optional[tuple[float, float, float, float]] = None
        self._pointer: Optional[tuple[float, float]] = None
        self._placement = Placement()
        # The field open over a mark, or ``None``.
        self._writing: Optional[Writing] = None
        # Whether ``Enter`` opens the newest mark's field rather than leaving.
        self._fresh = False

    @property
    def comments(self) -> Comments:
        """The comment buffer this mode writes to."""
        return self._comments

    @property
    def writing(self) -> Optional[Writing]:
        """The field open over a mark, or ``None``."""
        return self._writing

    @property
    def active(self) -> bool:
        """Whether the mode is latched on."""
        return self._comments.active

    @property
    def hovered(self) -> Optional[Any]:
        """The pick candidate under the cursor, for the overlay to highlight."""
        return self._hover() if self._hover is not None else None

    @property
    def band(self) -> Optional[tuple[float, float, float, float]]:
        """The rect a drag has swept so far, or ``None`` when not dragging."""
        return self._band

    @property
    def pointer(self) -> Optional[tuple[float, float]]:
        """Where the pointer last was, for the badge to keep out of its way."""
        return self._pointer

    @property
    def placement(self) -> Placement:
        """Where the badge sits, kept across frames."""
        return self._placement

    @property
    def exit(self) -> str:
        """The ways out right now, for the badge's first line."""
        if self._writing is not None:
            return "Enter write" + SEPARATOR + "Esc close"
        if self._fresh:
            return "Esc discard"
        if self._comments.marks():
            return "Enter keep" + SEPARATOR + "Esc discard"
        return "Esc leave"

    @property
    def hints(self) -> tuple[str, ...]:
        """The gestures and keys that would do something right now, for the badge."""
        if self._band is not None:
            return ()
        if self._writing is not None:
            return ("Shift+←/→ select", "Ctrl+A/C/X/V")
        parts: list[str] = []
        if self._fresh:
            parts += ["Enter write", "W/S parent/child"]
        elif self._comments.marks():
            parts += ["click a badge write", "W/S parent/child"]
        elif self.hovered is not None:
            parts += ["click / drag mark", "Ctrl+Shift+Click source"]
        if self._comments.undoable:
            parts.append("Ctrl+Z undo")
        if self._comments.redoable:
            parts.append("Ctrl+Shift+Z redo")
        if self._comments.marks():
            parts.append("Ctrl+Backspace clear")
        return tuple(parts)

    # --- keys -------------------------------------------------------------

    def on_key_press(self, app: Any, name: str, modifier_keys: int) -> bool:
        """Handle a key. ``True`` when consumed, which is every key while latched."""
        key = str(name).strip().lower()
        chord = chord_held(modifier_keys)

        if not self.active:
            if key == _ENTER_KEY and chord:
                self._enter(app)
                return True
            return False

        if key == _LAYOUT_KEY and chord and getattr(app, "_layout_edit_mode", None) is not None:
            return False
        if self._writing is not None:
            self._write_key(app, key, modifier_keys)
            return True
        if key == "escape":
            self._discard(app)
        elif key == "enter":
            if self._fresh:
                self._open_field(app, len(self._comments.marks()))
            else:
                self._commit(app)
        elif key == "z" and chord:
            self._stepped(app, self._comments.redo())
        elif key == "z" and accel_held(modifier_keys):
            self._stepped(app, self._comments.undo())
        elif key == "backspace" and accel_held(modifier_keys):
            self._comments.clear()
            self._fresh = False
            self._changed(app)
        elif key == "w":
            self._walk_up(app)
        elif key == "s":
            self._walk_down(app)
        return True

    def _stepped(self, app: Any, moved: bool) -> None:
        """After an undo or redo: the newest mark may not be the one the offer was for."""
        if moved:
            self._fresh = False
            self._changed(app)

    def on_text_motion(self, app: Any, motion: int, select: bool) -> bool:
        """Swallow the motion half of an editing key while latched. ``True`` when consumed.

        A key the mode took must not also edit a text field behind it.
        """
        return self.active

    def on_key_release(self, app: Any, name: str, modifier_keys: int) -> bool:
        """Swallow the key-up half while latched. ``True`` when consumed.

        The press was consumed, and a widget must not receive a key-up with no press.
        """
        return self.active

    def on_text(self, app: Any, text: str) -> bool:
        """Type into the open field. ``True`` when consumed; ``False`` with no field open."""
        writing = self._writing
        if not self.active or writing is None:
            return False
        writing.field.type(text)
        invalidate(app)
        return True

    def on_ime_composition(self, app: Any, text: str, start: int, length: int) -> bool:
        """Show the input method's uncommitted text at the caret. ``True`` when consumed."""
        writing = self._writing
        if not self.active or writing is None:
            return False
        writing.field.compose(text, start, length)
        invalidate(app)
        return True

    # --- the field --------------------------------------------------------

    def _open_field(self, app: Any, index: int) -> None:
        if index == len(self._comments.marks()):
            self._fresh = False
        self._writing = Writing(index, InlineField.open(self._comments.instruction(index) or ""))
        invalidate(app)

    def _write_key(self, app: Any, key: str, modifier_keys: int) -> None:
        writing = self._writing
        assert writing is not None
        outcome = writing.field.key(key, modifier_keys)
        if outcome == "commit":
            self._write(app)
            return
        if outcome == "cancel":
            self._writing = None
        invalidate(app)

    def _write(self, app: Any) -> None:
        """Close the field, keeping its text on the mark."""
        writing, self._writing = self._writing, None
        if writing is None:
            return
        self._comments.set_instruction(writing.index, writing.field.text)
        self._changed(app)

    def _badge_at(self, x: float, y: float) -> Optional[int]:
        """The number of the mark whose badge is under ``(x, y)``, or ``None``."""
        for index, kind, mark in reversed(self._comments.marks()):
            rect = mark if kind == "region" else visible_rect(mark)
            if rect is None:
                continue
            if (rect[0] - x) ** 2 + (rect[1] - y) ** 2 <= BADGE_RADIUS**2:
                return index
        return None

    def _enter(self, app: Any) -> None:
        other = getattr(app, "_layout_edit_mode", None)
        if other is not None and other.active:
            other.leave(app)
        self._comments.enter()
        self._press = None
        self._hover = None
        self._band = None
        self._writing = None
        self._fresh = False
        self._placement.reset()
        self._changed(app, note=False)

    def commit(self, app: Any) -> None:
        """Keep the session's work and leave, as ``Enter`` does. No-op when off."""
        if self.active:
            self._commit(app)

    def _commit(self, app: Any) -> None:
        self._comments.commit()
        self._reset(app)

    def _discard(self, app: Any) -> None:
        self._comments.discard()
        self._reset(app)

    def _reset(self, app: Any) -> None:
        self._press = None
        self._hover = None
        self._band = None
        self._anchor = None
        self._writing = None
        self._fresh = False
        self._changed(app)

    # --- pointer ----------------------------------------------------------

    def on_mouse_press(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Record where a press landed. Returns ``True`` when the mode consumed it."""
        if not self.active:
            return False
        self._press = (float(x), float(y))
        return True

    def on_mouse_release(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Resolve the gesture. ``True`` when consumed.

        With a field open the click writes it. Otherwise a click on a badge opens
        that mark's field, any other click toggles the widget under the cursor, and
        a drag marks the area it swept.
        """
        if not self.active:
            return False
        press, self._press = self._press, None
        self._band = None
        if self._writing is not None:
            self._write(app)
            return True
        if press is None:
            return True
        if travelled(press, x, y):
            before = len(self._comments.marks())
            self._comments.add_region(_normalized(press, (float(x), float(y))))
            self._fresh = self._fresh or len(self._comments.marks()) > before
            self._changed(app)
            return True
        badge = self._badge_at(press[0], press[1])
        if badge is not None:
            self._open_field(app, badge)
            return True

        root = getattr(app, "root", None)
        node = pick(app, press[0], press[1])
        if root is None or node is None:
            return True
        newest = self._comments.last()
        if self._comments.toggle(node, root=root):
            self._fresh = True
        elif node is newest:
            # The mark the offer was for is the one that just went.
            self._fresh = False
        self._anchor = weak(node)
        self._changed(app)
        return True

    def on_mouse_motion(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Track the pick candidate, or the rubber band while a press is outstanding. ``True`` when consumed."""
        if not self.active:
            return False
        self._pointer = (float(x), float(y))
        if self._placement.crosses(self._pointer):
            invalidate(app)
        if self._press is not None and self._writing is None:
            band = _normalized(self._press, (float(x), float(y)))
            if band != self._band:
                self._band = band
                invalidate(app)
            return True
        candidate = pick(app, x, y)
        if candidate is self.hovered:
            # No repaint for a move that keeps the candidate.
            return True
        self._hover = weak(candidate)
        invalidate(app)
        return True

    # --- ancestor walk ----------------------------------------------------

    def _walk_up(self, app: Any) -> None:
        """Replace the newest member with its parent."""
        current = self._comments.last()
        parent = parent_of(current) if current is not None else None
        if parent is None:
            return
        self._comments.replace_last(parent, root=getattr(app, "root", None))
        self._changed(app)

    def _walk_down(self, app: Any) -> None:
        """Step back toward the node the walk started from."""
        current = self._comments.last()
        anchor = self._anchor() if self._anchor is not None else None
        child = child_toward(current, anchor)
        if child is None:
            return
        self._comments.replace_last(child, root=getattr(app, "root", None))
        self._changed(app)

    # --- change notification ----------------------------------------------

    def _changed(self, app: Any, *, note: bool = True) -> None:
        """Repaint, and leave a journal marker.

        The overlay reads this state at paint time, so a change with no frame
        requested is invisible.
        """
        invalidate(app)
        if note and self._journal is not None:
            try:
                self._journal.record_comment()
            except Exception:
                logger.debug("comment: recording the comment marker failed", exc_info=True)


def _normalized(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float, float, float]:
    """Return the rect two corners span, whichever direction the drag went."""
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return (x0, y0, x1 - x0, y1 - y0)


__all__ = ["BADGE_RADIUS", "CommentMode", "Writing"]
