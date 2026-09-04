"""Interaction journal: a pull-able record of the human's recent UI actions (dev-only).

The dev bridge is **AI-initiated**: the assistant reads (``describe_tree`` /
``screenshot``) and acts (``click`` / ``type`` / ``key``) on its own turns. The
reload journal closed one perception gap between turns -- "the *code*
changed under me". This module closes the complementary one: **"the human *drove
the app* under me."** In a pair session the human often reproduces a bug or
navigates to a screen while the assistant is mid-task, so the assistant's cached
``describe_tree`` is of a stale screen and it cannot tell *how* the human got to
the current state.

The design is a deliberate **mirror of the assistant's own action vocabulary**
(``click`` / ``key`` / ``type`` / ``scroll``): whatever the human does that the
assistant would need to reproduce, the assistant reproduces *through those same
verbs*, so recording exactly those inbound is necessary and sufficient to
reconstruct a replayable path. Higher-level *semantic* events (navigate / dialog
open-close / submit) are deliberately **not** recorded -- they are states
derivable from a click sequence plus ``describe_tree``, not primitive inputs.

Window lifecycle events (``window_opened`` / ``window_closed``) are the
one exception, because the derivability argument fails for them: a close can
happen on the OS title bar, entirely outside the widget tree, so no click
sequence records it -- the assistant could only reconstruct it by diffing
``status``'s window list against a remembered snapshot. They are recorded from
the App's register/unregister choke points (the dev runner wires them in), so
every open/close path -- in-app button, OS close, parent cascade, programmatic
-- lands in the same journal, interleaved with the input events in one ``seq``
order.

Two boundaries are load-bearing:

* **Never raw input.** Only coarse, *identifiable* actions are recorded: a click
  resolved to a widget ``key`` / ``label`` (never coordinates), a semantic key
  (``enter`` / ``tab`` / a modifier chord like ``ctrl+s``), and a content-free
  marker that the human *typed* into a field.
* **Never typed content.** A key that is a bare printable character with no
  command modifier is treated as typing and is *not* recorded as a ``key`` (that
  would leak the text a character at a time); a burst of ``on_text`` collapses to
  a single content-free ``text`` marker. Field values never enter the journal.

Scrolling obeys those rules too, plus two of its own, since a single wheel
gesture arrives as dozens of events:

* **Only what a region consumed.** An unconsumed wheel event moved nothing, so it
  is dropped -- which also inherits the region's own trackpad-jitter deadband.
* **A gesture is one event.** Consecutive scrolls of the same region in the same
  direction replace the journal's tail instead of appending. A different region,
  a reversal, or any intervening click / key / text starts a new event, which
  bounds the count *structurally* rather than by a timeout.

Recording happens on the UI thread (the input handlers that feed the real
backend); reads happen on HTTP worker threads, so the buffer is guarded by a
lock -- the same shape as the reload journal.
"""

from __future__ import annotations

import logging
import threading
import time
import weakref
from collections import deque
from dataclasses import dataclass, replace
from itertools import count
from typing import Any, Callable, Deque, Optional

from nuiitivet.input.codes import MOD_ALT, MOD_CTRL, MOD_META, MOD_SHIFT

logger = logging.getLogger(__name__)

# Default number of interaction events retained. A reproduction path is usually
# short (a handful of clicks); a small buffer holds the recent tail an assistant
# needs to answer "where is the human now, and how did they get here?".
DEFAULT_CAPACITY = 200

# Cap on a single identity string echoed into a target, so one giant text node
# cannot bloat the log. Mirrors ``perception._MAX_IDENTITY_LEN``.
_MAX_IDENTITY_LEN = 120

# Physical modifier flags, most-significant first, mapped to display names. Used
# both to name a chord and to decide whether a key press is a shortcut worth
# recording (see ``_COMMAND_MODS``).
_MOD_FLAGS: tuple[tuple[int, str], ...] = (
    (MOD_CTRL, "ctrl"),
    (MOD_ALT, "alt"),
    (MOD_META, "meta"),
    (MOD_SHIFT, "shift"),
)

# Modifiers that turn a key press into a *command* (a shortcut) rather than
# typing. Shift is intentionally excluded: shift+letter is a capital letter, i.e.
# typed content, which must never be recorded key-by-key.
_COMMAND_MODS = MOD_CTRL | MOD_ALT | MOD_META

# Modifier keys pressed *on their own*. Their key-down fires with the modifier
# bit already set, which would otherwise read as a shortcut (``ctrl`` mask) and
# be recorded -- but a bare modifier press is noise (the meaningful event is the
# chord that follows). Dropped by name so ``ctrl`` alone never litters the log.
_MODIFIER_KEY_NAMES = frozenset(
    {
        "lshift",
        "rshift",
        "lctrl",
        "rctrl",
        "lalt",
        "ralt",
        "loption",
        "roption",
        "lcommand",
        "rcommand",
        "lmeta",
        "rmeta",
        "lwindows",
        "rwindows",
        "capslock",
        "numlock",
        "scrolllock",
        # Unprefixed spellings, in case a backend does not distinguish sides.
        "shift",
        "ctrl",
        "control",
        "alt",
        "option",
        "command",
        "meta",
        "windows",
    }
)

# Bare (unmodified) keys that carry navigation / commit meaning and are safe to
# record because they reveal no typed content. A bare printable character is not
# in this set, so typing never lands in the journal as ``key`` events.
_SEMANTIC_KEYS = frozenset(
    {
        "enter",
        "tab",
        "escape",
        "space",
        "backspace",
        "delete",
        "up",
        "down",
        "left",
        "right",
        "home",
        "end",
        "pageup",
        "pagedown",
    }
)

# Direction names per axis, ordered (negative, positive) -- positive being toward
# the content's end, the sign convention ``scroll(dx=, dy=)`` takes.
_AXIS_DIRECTIONS: dict[str, tuple[str, str]] = {
    "vertical": ("up", "down"),
    "horizontal": ("left", "right"),
}

# Below this a wheel delta counts as "not on this axis". Same threshold
# ``Scrollable._handle_scroll`` falls back from ``scroll_x`` to ``scroll_y`` at.
_AXIS_EPSILON = 1e-6


def _coerce_display(value: Any) -> Optional[str]:
    """Return a short display string for ``value``, or ``None`` if unusable.

    Mirrors ``perception._coerce_display``: observables are unwrapped via
    ``.value``; only genuine text-like scalars survive (a widget-valued ``label``
    is ignored); the result is stripped and length-capped.
    """
    if value is None:
        return None
    if hasattr(value, "value"):
        try:
            value = value.value
        except Exception:
            return None
    if not isinstance(value, (str, int, float, bool)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > _MAX_IDENTITY_LEN:
        text = text[: _MAX_IDENTITY_LEN - 1] + "…"
    return text


def _modifier_names(mask: int) -> tuple[str, ...]:
    """Return the display names of the physical modifiers set in ``mask``."""
    return tuple(name for flag, name in _MOD_FLAGS if mask & flag)


def _should_record_key(name: str, mask: int) -> bool:
    """Whether a key press is recordable without leaking typed content.

    A command modifier (ctrl / alt / meta) makes any key a shortcut worth
    recording. Otherwise only an explicit navigation / commit key qualifies -- a
    bare printable character is typing and is deliberately dropped so the journal
    never reconstructs field text a keystroke at a time. A modifier key pressed on
    its own is always dropped: its key-down carries the modifier bit but is only
    noise ahead of the chord that follows.
    """
    if name in _MODIFIER_KEY_NAMES:
        return False
    if mask & _COMMAND_MODS:
        return True
    return name in _SEMANTIC_KEYS


def _visible_label(node: Any) -> Optional[str]:
    """Return ``node``'s first visible identity (label / text / title), if any."""
    for attr in ("label", "text", "title"):
        display = _coerce_display(getattr(node, attr, None))
        if display is not None:
            return display
    return None


def own_identity(node: Any) -> dict[str, Any]:
    """Return ``node``'s *own* identity, without :func:`resolve_target`'s walk up.

    The counterpart to :func:`resolve_target`, and the two answer different
    questions. ``resolve_target`` answers "how would you drive this?", which for
    a click on a button's inner label is the button. That is exactly right for an
    action, and wrong as the sole answer to "what is this node?" -- inspect-mode
    picking exists precisely so an anonymous ``Text`` can be designated,
    and reporting the button's identity beside that text's rect would describe
    neither node.

    Same shape either way: ``{"type", optional "key", optional "label"}``.
    """
    info: dict[str, Any] = {"type": type(node).__name__}
    key = _coerce_display(getattr(node, "key", None))
    if key is not None:
        info["key"] = key
    label = _visible_label(node)
    if label is not None:
        info["label"] = label
    return info


def window_identity(window: Any) -> dict[str, Any]:
    """Summarize ``window`` for a lifecycle event: ``{"id", optional "title", "main"}``.

    The same fields ``status``'s window listing reports (minus the transient
    ``focused``), so an assistant can join a lifecycle event to that listing --
    in particular, a ``window_closed`` id marks any remembered ``window=`` id
    as stale before acting on it. The title goes through the same display
    coercion as widget identities, so an observable title is unwrapped and an
    unset one is omitted rather than recorded as ``null``.
    """
    info: dict[str, Any] = {"id": getattr(window, "id", None)}
    title = _coerce_display(getattr(window, "title", None))
    if title is not None:
        info["title"] = title
    try:
        info["main"] = bool(getattr(window, "is_main", False))
    except Exception:
        info["main"] = False
    return info


def resolve_target(node: Any) -> dict[str, Any]:
    """Resolve a hit-tested ``node`` to a stable, coordinate-free identity.

    Walks up the parent chain and **prefers a ``key``**: a click on a ``Button``'s
    internal label ``Text`` resolves to the ``Button`` that carries the ``key``,
    not the inner text -- so the recorded target matches what ``describe_tree``
    shows and what the action bridge (`click --key ...`) drives. The result is
    ``{"type", optional "key", optional "label"}``:

    * If any ancestor has a ``key``, that node anchors the identity (its ``type``
      and ``key``), and the nearest visible label found at or below it is attached
      as human context.
    * Otherwise the nearest node with a visible label anchors it.
    * If nothing in the chain is identifiable, the hit node's ``type`` alone is
      returned -- a coarse but honest record that never invents a coordinate.
    """
    key_val: Optional[str] = None
    key_type: Optional[str] = None
    label_val: Optional[str] = None
    label_type: Optional[str] = None

    cur = node
    while cur is not None:
        if key_val is None:
            candidate = _coerce_display(getattr(cur, "key", None))
            if candidate is not None:
                key_val = candidate
                key_type = type(cur).__name__
                # Prefer the keyed node's *own* label; fall back to the nearest
                # descendant label already seen while walking up to it.
                own_label = _visible_label(cur)
                if own_label is not None:
                    label_val = own_label
        if label_val is None:
            candidate = _visible_label(cur)
            if candidate is not None:
                label_val = candidate
                label_type = type(cur).__name__
        if key_val is not None:
            break
        cur = getattr(cur, "_parent", None)

    if key_val is not None:
        info: dict[str, Any] = {"type": key_type, "key": key_val}
        if label_val is not None:
            info["label"] = label_val
        return info
    if label_val is not None:
        return {"type": label_type, "label": label_val}
    return {"type": type(node).__name__}


def _consumed_axis(reported_axis: Any, dx: float, dy: float) -> tuple[str, float]:
    """Pick the axis a scroll region consumed on, and the delta it consumed.

    Mirrors ``Scrollable._handle_scroll``: a vertical region reads the wheel's
    ``dy``; a horizontal one reads ``dx`` but falls back to ``dy``, so a strip
    still scrolls under an ordinary vertical wheel. A handler reporting no axis is
    named from whichever delta the wheel carried.
    """
    if reported_axis == "horizontal":
        return ("horizontal", float(dx) if abs(dx) >= _AXIS_EPSILON else float(dy))
    if reported_axis == "vertical":
        return ("vertical", float(dy))
    if abs(dy) < _AXIS_EPSILON <= abs(dx):
        return ("horizontal", float(dx))
    return ("vertical", float(dy))


def _weak_ref(obj: Any) -> Optional[Callable[[], Any]]:
    """Return a weak reference to ``obj``, or ``None`` if it does not support one.

    ``None`` degrades safely: the next scroll compares against nothing, so it
    starts a fresh event instead of risking a merge with the wrong region.
    """
    try:
        return weakref.ref(obj)
    except TypeError:
        return None


def read_scroll_metrics(widget: Any) -> dict[str, Any]:
    """Read the scroll position ``widget`` reports, or ``{}`` if it reports none.

    The same ``scroll_metrics()`` probe the ``scroll`` action reads (both land on
    :meth:`~nuiitivet.scrolling.controller.ScrollController.metrics`), so a
    journal entry and an action result describe a region identically.
    """
    probe = getattr(widget, "scroll_metrics", None)
    if not callable(probe):
        return {}
    try:
        metrics = probe()
    except Exception:
        logger.debug("interaction: reading scroll metrics failed", exc_info=True)
        return {}
    return dict(metrics) if isinstance(metrics, dict) else {}


@dataclass(frozen=True)
class InteractionEvent:
    """One recorded, coarse UI action taken by the human.

    Attributes:
        seq: Monotonic id, unique and increasing across the app's lifetime. A
            client compares it against the last ``seq`` it saw to tell whether new
            interactions happened since its previous turn. A coalesced ``scroll``
            is re-issued a fresh one, so an ongoing gesture reads as new activity.
        timestamp: Unix time (seconds) when the event was recorded -- for a
            coalesced ``scroll``, when it was last updated.
        kind: ``"click"``, ``"key"``, ``"text"``, ``"scroll"``, ``"select"``,
            ``"window_opened"``, or ``"window_closed"``.
        target: For a ``click`` or a ``scroll``, the resolved widget identity
            (``{"type", optional "key"/"label"}``); ``None`` otherwise. Never a
            coordinate.
        window: For a ``window_opened`` / ``window_closed``, the affected
            window's identity (see :func:`window_identity`); ``None`` otherwise.
        key: For a ``key``, the key name (e.g. ``"enter"``, ``"s"``); ``None``
            otherwise.
        modifiers: For a ``key``, the held modifier names (e.g. ``("ctrl",)``);
            empty otherwise.
        started_at: For a ``scroll``, when the gesture began; it survives the
            coalescing that moves :attr:`timestamp` forward.
        direction: For a ``scroll``, ``"up"`` / ``"down"`` / ``"left"`` /
            ``"right"``, from the sign of the delta the consuming region used.
        dx: For a ``scroll`` on a horizontal region, the accumulated delta in
            **wheel notches**, in the sign convention the ``scroll`` action takes,
            so it replays verbatim.
        dy: Likewise for a ``scroll`` on a vertical region.
        axis: For a ``scroll``, the consuming region's axis -- which need not match
            the wheel's, since a horizontal region also consumes a vertical wheel.
        offset, max_extent, at_start, at_end: For a ``scroll``, where the region
            ended up. ``at_end`` is how a reader tells "scrolled to the bottom"
            from "still going".
    """

    seq: int
    timestamp: float
    kind: str
    target: Optional[dict[str, Any]] = None
    window: Optional[dict[str, Any]] = None
    key: Optional[str] = None
    modifiers: tuple[str, ...] = ()
    started_at: Optional[float] = None
    direction: Optional[str] = None
    dx: float = 0.0
    dy: float = 0.0
    axis: Optional[str] = None
    offset: Optional[float] = None
    max_extent: Optional[float] = None
    at_start: Optional[bool] = None
    at_end: Optional[bool] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict, omitting fields that do not apply.

        A ``click`` carries ``target``; a ``key`` carries ``key`` and (when
        non-empty) ``modifiers``; a ``text`` marker carries neither; a ``scroll``
        carries its target, its gesture (``direction`` plus the non-zero delta)
        and the region's resulting position; a ``window_opened`` /
        ``window_closed`` carries ``window``. The absent fields are omitted so
        each event reads as exactly its kind.
        """
        payload: dict[str, Any] = {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "kind": self.kind,
        }
        if self.started_at is not None:
            payload["started_at"] = self.started_at
        if self.target is not None:
            payload["target"] = self.target
        if self.window is not None:
            payload["window"] = self.window
        if self.key is not None:
            payload["key"] = self.key
        if self.modifiers:
            payload["modifiers"] = list(self.modifiers)
        if self.direction is not None:
            payload["direction"] = self.direction
        if self.dx:
            payload["dx"] = self.dx
        if self.dy:
            payload["dy"] = self.dy
        for name in ("axis", "offset", "max_extent", "at_start", "at_end"):
            value = getattr(self, name)
            if value is not None:
                payload[name] = value
        return payload


class InteractionJournal:
    """A thread-safe, bounded ring buffer of recent :class:`InteractionEvent`\\ s.

    The recorder appends on the UI thread; the bridge reads on HTTP worker
    threads. Both paths take the lock, so the buffer is safe to share without
    either side owning the other. Mirrors
    :class:`~nuiitivet.dev.journal.ReloadJournal`.
    """

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._events: Deque[InteractionEvent] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        # Monotonic sequence source. Starts at 1 so a client's "last seen seq"
        # sentinel of 0 means "I have seen nothing yet".
        self._seq = count(1)

    @property
    def capacity(self) -> int:
        """The maximum number of events retained."""
        return self._capacity

    def record_click(self, target: dict[str, Any]) -> InteractionEvent:
        """Record a click on the resolved ``target`` identity and return the event."""
        return self._record("click", target=target)

    def record_key(self, name: str, modifiers: tuple[str, ...] = ()) -> InteractionEvent:
        """Record a key press ``name`` with held ``modifiers`` and return the event."""
        return self._record("key", key=name, modifiers=modifiers)

    def record_select(self) -> InteractionEvent:
        """Record a content-free marker that the human designated something.

        The counterpart to :meth:`record_text`, and content-free for a different
        reason. A designation *may* carry rects and field text -- it is an
        explicit act of disclosure, unlike this journal's ambient recording -- but
        the layering still holds: the marker here says only *that* it happened,
        and the payload is served only when the assistant explicitly calls
        ``describe_selection``. So an assistant catching up on the journal sees
        the designation without the journal itself becoming a second, unasked-for
        channel for it.
        """
        return self._record("select")

    def record_text(self) -> InteractionEvent:
        """Record a content-free marker that the human typed, and return the event."""
        return self._record("text")

    def record_window_opened(self, window: dict[str, Any]) -> InteractionEvent:
        """Record that a window opened and return the event.

        Args:
            window: The window's identity (see :func:`window_identity`).
        """
        return self._record("window_opened", window=window)

    def record_window_closed(self, window: dict[str, Any]) -> InteractionEvent:
        """Record that a window closed and return the event.

        Recorded from the App's unregister choke point, so an OS-button close or
        a parent-cascade close -- invisible to the input recorders -- appears in
        the same sequence as the clicks around it.

        Args:
            window: The window's identity (see :func:`window_identity`).
        """
        return self._record("window_closed", window=window)

    def record_scroll(
        self,
        target: dict[str, Any],
        *,
        direction: str,
        dx: float = 0.0,
        dy: float = 0.0,
        metrics: Optional[dict[str, Any]] = None,
        coalesce: bool = True,
    ) -> InteractionEvent:
        """Record a consumed scroll into the ongoing gesture, and return the event.

        If the newest event is already a ``scroll`` of the same ``target`` in the
        same ``direction``, this **replaces** it rather than appending: the deltas
        accumulate, ``metrics`` refresh, ``seq`` and ``timestamp`` move forward,
        and ``started_at`` is kept. Any other tail starts a new event. Splitting
        on direction is what keeps the accumulated delta honest: within one event
        it is monotonic, so down-then-up cannot collapse into a net-zero entry
        that reads as "did not scroll".

        Args:
            target: The consuming region's identity (see :func:`resolve_target`).
            direction: ``"up"`` / ``"down"`` / ``"left"`` / ``"right"``.
            dx: Horizontal delta in wheel notches (zero for a vertical region).
            dy: Vertical delta in wheel notches (zero for a horizontal region).
            metrics: The region's position (see :func:`read_scroll_metrics`);
                unknown keys are ignored.
            coalesce: Whether this scroll may continue the tail gesture. Pass
                ``False`` when the caller knows a *different* region produced it:
                two anonymous siblings resolve to the same ``target``, so the
                tail check alone would merge them into one entry with summed
                deltas. The caller knows the region's object identity; the
                journal only ever sees the resolved -- and deliberately coarse --
                identity, so it cannot tell them apart on its own.
        """
        fields = {
            name: value
            for name, value in (metrics or {}).items()
            if name in ("axis", "offset", "max_extent", "at_start", "at_end")
        }
        with self._lock:
            now = time.time()
            tail = self._events[-1] if self._events else None
            if (
                coalesce
                and tail is not None
                and tail.kind == "scroll"
                and tail.direction == direction
                and tail.target == target
            ):
                event = replace(
                    tail,
                    seq=next(self._seq),
                    timestamp=now,
                    dx=tail.dx + dx,
                    dy=tail.dy + dy,
                    **fields,
                )
                self._events[-1] = event
                return event
            event = InteractionEvent(
                seq=next(self._seq),
                timestamp=now,
                kind="scroll",
                target=target,
                started_at=now,
                direction=direction,
                dx=dx,
                dy=dy,
                **fields,
            )
            self._events.append(event)
            return event

    def _record(
        self,
        kind: str,
        *,
        target: Optional[dict[str, Any]] = None,
        window: Optional[dict[str, Any]] = None,
        key: Optional[str] = None,
        modifiers: tuple[str, ...] = (),
    ) -> InteractionEvent:
        with self._lock:
            event = InteractionEvent(
                seq=next(self._seq),
                timestamp=time.time(),
                kind=kind,
                target=target,
                window=window,
                key=key,
                modifiers=modifiers,
            )
            self._events.append(event)
            return event

    def recent(self, limit: Optional[int] = None) -> list[InteractionEvent]:
        """Return the most recent events, oldest-first.

        Args:
            limit: Maximum number of events to return (the newest ``limit``). A
                non-positive limit returns an empty list; ``None`` returns all
                retained events.
        """
        with self._lock:
            events = list(self._events)
        if limit is None:
            return events
        if limit <= 0:
            return []
        return events[-limit:]


class InteractionRecorder:
    """Turns raw human input into coarse, privacy-safe journal entries.

    The dev runner attaches one of these to the running app as
    ``app._interaction_recorder`` and calls it from the *real* input handlers --
    the layer the human drives but the assistant's synthesized actions bypass
    (those enter below, at ``app._dispatch_*``). So the journal captures the human
    only, with no need to tag synthetic events.

    All ``on_*`` hooks run on the UI thread and are the sole writers, so the
    text-coalescing state (:attr:`_last_kind`) needs no lock; the journal's own
    lock guards the shared buffer.
    """

    def __init__(self, journal: InteractionJournal) -> None:
        self._journal = journal
        # Kind of the most recent recorded event, used to coalesce a burst of
        # per-character ``on_text`` callbacks into a single ``text`` marker.
        self._last_kind: Optional[str] = None
        # The region the last recorded scroll went to, so a gesture coalesces on
        # the *object*, not on its resolved identity -- two keyless siblings look
        # identical to the journal. Weak, so tracking it never keeps a detached
        # subtree alive; a dead referent simply reads as a different region.
        self._last_scroll: Optional[Callable[[], Any]] = None

    def on_mouse_press(self, app: Any, x: float, y: float) -> None:
        """Record a primary press, resolved to the widget identity under ``(x, y)``.

        A press on empty space (no hit target) is not recorded -- there is no
        widget identity to reconstruct, and a bare coordinate is never stored.
        """
        root = getattr(app, "root", None)
        if root is None:
            return
        try:
            node = root.hit_test(int(x), int(y))
        except Exception:
            node = None
        if node is None:
            return
        self._journal.record_click(resolve_target(node))
        self._last_kind = "click"

    def on_mouse_scroll(self, handler: Any, dx: float, dy: float) -> None:
        """Record a wheel event that ``handler`` consumed, as part of a gesture.

        ``handler`` is what the pointer dispatch returned -- the region that
        actually scrolled, possibly an ancestor of the widget under the cursor.
        ``None`` means nothing consumed the event, so nothing moved and nothing is
        recorded, which also inherits the region's own sub-notch deadband. The
        deltas are notches, already normalized into the framework's sign
        convention by the backend.

        The **consuming region names the gesture**, not the raw input: its
        ``axis`` decides which delta was used (see :func:`_consumed_axis`) and
        that delta's sign names the direction. Reading the wheel instead would
        mislabel a horizontal region driven by a vertical wheel.

        Coalescing keys off the region's **object identity**, decided here and
        passed down: two keyless siblings of the same type resolve to the same
        target, and merging them would sum the deltas of two separate regions
        into one entry that describes neither.
        """
        if handler is None:
            return
        metrics = read_scroll_metrics(handler)
        axis, delta = _consumed_axis(metrics.get("axis"), dx, dy)
        if delta == 0.0:
            return
        negative, positive = _AXIS_DIRECTIONS[axis]
        previous = self._last_scroll() if self._last_scroll is not None else None
        self._journal.record_scroll(
            resolve_target(handler),
            direction=positive if delta > 0.0 else negative,
            dx=delta if axis == "horizontal" else 0.0,
            dy=delta if axis == "vertical" else 0.0,
            metrics=metrics,
            coalesce=previous is handler,
        )
        self._last_scroll = _weak_ref(handler)
        self._last_kind = "scroll"

    def on_key_press(self, name: str, modifier_keys: int) -> None:
        """Record a semantic key press, dropping bare typing to protect content."""
        key_name = str(name).strip().lower()
        if not key_name or not _should_record_key(key_name, modifier_keys):
            return
        self._journal.record_key(key_name, _modifier_names(modifier_keys))
        self._last_kind = "key"

    def on_text(self) -> None:
        """Record a content-free marker that the human typed into a field.

        Consecutive ``on_text`` callbacks (typing a word fires one per character)
        collapse to a single marker: the useful signal is *that* the human typed
        here, and the content must never be stored. The caller passes no text --
        so content cannot leak here -- and filters control-only input (Enter / Tab)
        upstream, so this is reached only for genuine typing.
        """
        if self._last_kind == "text":
            return
        self._journal.record_text()
        self._last_kind = "text"


__all__ = [
    "DEFAULT_CAPACITY",
    "InteractionEvent",
    "InteractionJournal",
    "InteractionRecorder",
    "own_identity",
    "read_scroll_metrics",
    "resolve_target",
    "window_identity",
]
