"""Comment mode: the human marks widgets and areas on the running app and writes on each mark.

Latched on ``Ctrl+Shift+C`` from the backend's real input handlers, which the
agent's synthesized actions bypass, so a comment is always the human's. While
latched every event is consumed: a click or a drag marks, the keys walk the
candidate and edit a mark's text, and nothing reaches the app. The marks live
in :mod:`.comments`; ``H`` held lists the keys.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from nuiitivet._interaction.perception import visible_rect

from .comments import Comments
from .gesture import accel_held, child_toward, chord_held, invalidate, parent_of, pick, sibling_of, travelled, weak
from .hud import SEPARATOR, Placement, Splash
from .inline_field import InlineField, Slot
from .interaction import InteractionJournal

logger = logging.getLogger(__name__)


# The key that enters the mode. ``C`` for *comment*.
_ENTER_KEY = "c"
# Layout edit mode's key, let through while latched so the two modes switch directly.
_LAYOUT_KEY = "e"
#: The numbered badge at a mark's top-left corner. A press inside the disc clicks
#: it; no slack, since the widget under it may be no taller than the disc.
BADGE_RADIUS = 10.0
# Both, since a Mac keyboard has no Delete key.
_DELETE_KEYS = ("delete", "backspace")
# The lines at the window's centre on entering, and on leaving either way.
_SPLASH_ON = "COMMENT MODE" + SEPARATOR + "H help"
_SPLASH_KEPT = "COMMENT MODE off" + SEPARATOR + "comments kept"
_SPLASH_DISCARDED = "COMMENT MODE off" + SEPARATOR + "comments discarded"
#: The field's size beside a badge with nothing typed; it grows with the text.
FIELD_LEAST = (180.0, 24.0)
#: Between a badge's centre and the box beside it.
BESIDE_GAP = BADGE_RADIUS + 4.0

Rect = tuple[float, float, float, float]
Point = tuple[float, float]


def beside_anchor(rect: tuple[float, ...]) -> Point:
    """The point a caption or field beside the badge on ``rect``'s corner opens from."""
    return (rect[0], rect[1] - 10.0)


@dataclass
class Writing:
    """The field open over one mark, for the overlay to draw.

    Attributes:
        index: The mark's number.
        field: The text under edit.
        slot: Where the field hangs on the badge, fixed when it opened.
    """

    index: int
    field: InlineField
    slot: Slot


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
        # The node under the cursor. Weak.
        self._picked: Optional[Callable[[], Any]] = None
        # The widget `W` / `S` / `A` / `D` walked the candidate to, or ``None``. Weak.
        self._walked: Optional[Callable[[], Any]] = None
        # Where the pointer was when the walk began; a move past the drag
        # threshold from there ends the walk.
        self._walk_from: Optional[tuple[float, float]] = None
        # The badge under the cursor, whose whole instruction the overlay shows.
        self._hovered_badge: Optional[int] = None
        # The rect a drag has swept so far, for the overlay's rubber band.
        self._band: Optional[tuple[float, float, float, float]] = None
        self._pointer: Optional[tuple[float, float]] = None
        self._placement = Placement()
        self._splash = Splash()
        # Whether ``H`` is held, showing the sheet that lists every gesture.
        self._help = False
        # The field open over a mark, or ``None``.
        self._writing: Optional[Writing] = None

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
        """The candidate a click or ``Enter`` would mark, for the overlay to highlight.

        The widget under the cursor, or the widget a walk moved it to.
        """
        walked = self._walked() if self._walked is not None else None
        if walked is not None:
            return walked
        return self._picked() if self._picked is not None else None

    @property
    def walked(self) -> bool:
        """Whether a walk moved the candidate off the widget under the cursor."""
        return self._walked is not None and self._walked() is not None

    @property
    def hovered_badge(self) -> Optional[int]:
        """The number of the mark whose badge is under the cursor, or ``None``."""
        return self._hovered_badge

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
    def help(self) -> bool:
        """Whether the sheet listing every gesture is shown: while ``H`` is held."""
        return self._help

    @property
    def splash(self) -> Optional[str]:
        """The line at the window's centre just after entering or leaving, or ``None``."""
        return self._splash.text

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
        if key == "h":
            if not self._help:
                self._help = True
                invalidate(app)
            return True
        if key == "escape":
            self._discard(app)
            self._splash.show(app, _SPLASH_DISCARDED)
        elif key == "enter":
            if self.walked:
                self._mark(app, self.hovered)
            else:
                self._commit(app)
                self._splash.show(app, _SPLASH_KEPT)
        elif key == "z" and chord:
            self._stepped(app, self._comments.redo())
        elif key == "z" and accel_held(modifier_keys):
            self._stepped(app, self._comments.undo())
        elif key == "backspace" and accel_held(modifier_keys):
            self._comments.clear()
            self._changed(app)
        elif key in _DELETE_KEYS:
            self._remove_under_pointer(app)
        elif key == "w":
            self._walk_up(app)
        elif key == "s":
            self._walk_down(app)
        elif key == "a":
            self._walk_sideways(app, -1)
        elif key == "d":
            self._walk_sideways(app, 1)
        return True

    def _stepped(self, app: Any, moved: bool) -> None:
        if moved:
            self._changed(app)

    def on_text_motion(self, app: Any, motion: int, select: bool) -> bool:
        """Swallow the motion half of an editing key while latched. ``True`` when consumed.

        A key the mode took must not also edit a text field behind it.
        """
        return self.active

    def on_key_release(self, app: Any, name: str, modifier_keys: int) -> bool:
        """Swallow the key-up half while latched. ``True`` when consumed.

        The press was consumed, and a widget must not receive a key-up with no press.
        Releasing ``H`` takes the help sheet away.
        """
        if not self.active:
            return False
        if self._help and str(name).strip().lower() == "h":
            self._help = False
            invalidate(app)
        return True

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
        rect = self._mark_rect(index)
        slot = Slot.beside(beside_anchor(rect or (0.0, 0.0)), FIELD_LEAST, BESIDE_GAP, _window(app))
        field = InlineField.open(self._comments.instruction(index) or "", wrap=slot.wrap)
        self._writing = Writing(index, field, slot)
        invalidate(app)

    def _open_newest(self, app: Any) -> None:
        """Open the field on the mark just made."""
        self._open_field(app, len(self._comments.marks()))

    def _mark_under_pointer(self) -> Optional[int]:
        """The number of the mark the pointer rests on, by its badge or by its widget, or ``None``."""
        if self._hovered_badge is not None:
            return self._hovered_badge
        return self._comments.index_of(self.hovered)

    def _remove_under_pointer(self, app: Any) -> None:
        index = self._mark_under_pointer()
        if index is not None and self._comments.remove(index):
            self._walked = None
            self._changed(app)

    def _mark_rect(self, index: int) -> Optional[Rect]:
        """The on-screen rect of mark ``index``, or ``None`` when it is off screen."""
        for number, kind, mark in self._comments.marks():
            if number == index:
                return mark if kind == "region" else visible_rect(mark)
        return None

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
        self._picked = None
        self._walked = None
        self._hovered_badge = None
        self._band = None
        self._writing = None
        self._placement.reset()
        self._splash.show(app, _SPLASH_ON)
        self._help = False
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
        self._picked = None
        self._walked = None
        self._hovered_badge = None
        self._band = None
        self._writing = None
        self._changed(app)

    # --- pointer ----------------------------------------------------------

    def on_mouse_press(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Record where a press landed. Returns ``True`` when the mode consumed it.

        A press while a field is open writes the field first, then starts the
        gesture as usual.
        """
        if not self.active:
            return False
        if self._writing is not None:
            self._write(app)
        self._press = (float(x), float(y))
        return True

    def on_mouse_release(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Resolve the gesture. ``True`` when consumed.

        A click on a badge opens that mark's field; any other click marks the
        candidate, or reopens the field on a widget already marked; a drag marks
        the area it swept. A new mark opens its field at once.
        """
        if not self.active:
            return False
        press, self._press = self._press, None
        self._band = None
        self._pointer = (float(x), float(y))
        if press is None:
            return True
        if travelled(press, x, y):
            self._comments.add_region(_normalized(press, (float(x), float(y))))
            self._changed(app)
            self._open_newest(app)
            return True
        badge = self._badge_at(press[0], press[1])
        if badge is not None:
            self._open_field(app, badge)
            return True

        if not self.walked:
            # The pointer is here, so the widget under it is the candidate from now on.
            self._picked = weak(pick(app, press[0], press[1]))
        self._mark(app, self.hovered)
        return True

    def _mark(self, app: Any, node: Any) -> None:
        """Mark ``node`` and open the new mark's field; on a marked ``node``, open its field again."""
        root = getattr(app, "root", None)
        if root is None or node is None:
            return
        self._walked = None
        index = self._comments.index_of(node)
        if index is not None:
            self._open_field(app, index)
            return
        if self._comments.add(node, root=root):
            self._changed(app)
            self._open_newest(app)

    def on_mouse_motion(self, app: Any, x: float, y: float, modifier_keys: int = 0) -> bool:
        """Track the pick candidate and the badge under the cursor, or the rubber band while a press is outstanding.

        ``True`` when consumed.
        """
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
        badge = self._badge_at(x, y)
        if badge != self._hovered_badge:
            self._hovered_badge = badge
            invalidate(app)
        before = self.hovered
        candidate = pick(app, x, y)
        self._picked = weak(candidate)
        if self._walked is not None and (self._walk_from is None or travelled(self._walk_from, x, y)):
            # A drift of a few pixels is the hand resting on the mouse; more is aiming again.
            self._walked = None
        if self.hovered is before:
            # No repaint for a move that keeps the candidate.
            return True
        invalidate(app)
        return True

    # --- ancestor walk ----------------------------------------------------

    def _walk_up(self, app: Any) -> None:
        """Move the candidate onto its parent."""
        current = self.hovered
        parent = parent_of(current) if current is not None else None
        if parent is None:
            return
        self._choose(app, parent)

    def _walk_down(self, app: Any) -> None:
        """Move the candidate back toward the widget under the cursor."""
        picked = self._picked() if self._picked is not None else None
        child = child_toward(self.hovered, picked)
        if child is None:
            return
        self._choose(app, child)

    def _walk_sideways(self, app: Any, step: int) -> None:
        """Move the candidate onto the sibling before or after it."""
        sibling = sibling_of(self.hovered, step)
        if sibling is None:
            return
        self._choose(app, sibling)

    def _choose(self, app: Any, node: Any) -> None:
        """Make ``node`` the candidate, held until the pointer travels from where it is now."""
        picked = self._picked() if self._picked is not None else None
        self._walked = None if node is picked else weak(node)
        self._walk_from = self._pointer
        invalidate(app)

    # --- change notification ----------------------------------------------

    def _changed(self, app: Any, *, note: bool = True) -> None:
        """Repaint, re-read the badge under the pointer, and leave a journal marker."""
        if self._pointer is not None:
            self._hovered_badge = self._badge_at(*self._pointer)
        invalidate(app)
        if note and self._journal is not None:
            try:
                self._journal.record_comment()
            except Exception:
                logger.debug("comment: recording the comment marker failed", exc_info=True)


def _window(app: Any) -> tuple[float, float]:
    """The window's size, for placing the field; zero where the app has none."""
    return (float(getattr(app, "width", 0) or 0), float(getattr(app, "height", 0) or 0))


def _normalized(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float, float, float]:
    """Return the rect two corners span, whichever direction the drag went."""
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return (x0, y0, x1 - x0, y1 - y0)


__all__ = ["BADGE_RADIUS", "BESIDE_GAP", "FIELD_LEAST", "CommentMode", "Writing", "beside_anchor"]
