"""Interaction journal: a pull-able record of the human's recent UI actions (dev-only).

The dev bridge is **AI-initiated**: the assistant reads (``describe_tree`` /
``screenshot``) and acts (``click`` / ``type`` / ``key``) on its own turns. The
reload journal (#388) closed one perception gap between turns -- "the *code*
changed under me". This module closes the complementary one: **"the human *drove
the app* under me."** In a pair session the human often reproduces a bug or
navigates to a screen while the assistant is mid-task, so the assistant's cached
``describe_tree`` is of a stale screen and it cannot tell *how* the human got to
the current state.

The design is a deliberate **mirror of the assistant's own action vocabulary**
(``click`` / ``key`` / ``type``): whatever the human does that the assistant
would need to reproduce, the assistant reproduces *through those same verbs*, so
recording exactly those inbound is necessary and sufficient to reconstruct a
replayable path. Higher-level *semantic* events (navigate / dialog open-close /
submit) are deliberately **not** recorded -- they are states derivable from a
click sequence plus ``describe_tree``, not primitive inputs (#390).

Two boundaries are load-bearing:

* **Never raw input.** Only coarse, *identifiable* actions are recorded: a click
  resolved to a widget ``key`` / ``label`` (never coordinates), a semantic key
  (``enter`` / ``tab`` / a modifier chord like ``ctrl+s``), and a content-free
  marker that the human *typed* into a field.
* **Never typed content.** A key that is a bare printable character with no
  command modifier is treated as typing and is *not* recorded as a ``key`` (that
  would leak the text a character at a time); a burst of ``on_text`` collapses to
  a single content-free ``text`` marker. Field values never enter the journal.

Recording happens on the UI thread (the input handlers that feed the real
backend); reads happen on HTTP worker threads, so the buffer is guarded by a
lock -- the same shape as the reload journal. See #390 and
``docs/design/HOT_RELOAD.md`` (§12).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from itertools import count
from typing import Any, Deque, Optional

from nuiitivet.input.codes import MOD_ALT, MOD_CTRL, MOD_META, MOD_SHIFT

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


@dataclass(frozen=True)
class InteractionEvent:
    """One recorded, coarse UI action taken by the human.

    Attributes:
        seq: Monotonic id, unique and increasing across the app's lifetime. A
            client compares it against the last ``seq`` it saw to tell whether
            new interactions happened since its previous turn.
        timestamp: Unix time (seconds) when the event was recorded.
        kind: ``"click"``, ``"key"``, or ``"text"``.
        target: For a ``click``, the resolved widget identity
            (``{"type", optional "key"/"label"}``); ``None`` otherwise. Never a
            coordinate.
        key: For a ``key``, the key name (e.g. ``"enter"``, ``"s"``); ``None``
            otherwise.
        modifiers: For a ``key``, the held modifier names (e.g. ``("ctrl",)``);
            empty otherwise.
    """

    seq: int
    timestamp: float
    kind: str
    target: Optional[dict[str, Any]] = None
    key: Optional[str] = None
    modifiers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict, omitting fields that do not apply.

        A ``click`` carries ``target``; a ``key`` carries ``key`` and (when
        non-empty) ``modifiers``; a ``text`` marker carries neither. The absent
        fields are omitted so each event reads as exactly its kind.
        """
        payload: dict[str, Any] = {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "kind": self.kind,
        }
        if self.target is not None:
            payload["target"] = self.target
        if self.key is not None:
            payload["key"] = self.key
        if self.modifiers:
            payload["modifiers"] = list(self.modifiers)
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

    def record_text(self) -> InteractionEvent:
        """Record a content-free marker that the human typed, and return the event."""
        return self._record("text")

    def _record(
        self,
        kind: str,
        *,
        target: Optional[dict[str, Any]] = None,
        key: Optional[str] = None,
        modifiers: tuple[str, ...] = (),
    ) -> InteractionEvent:
        with self._lock:
            event = InteractionEvent(
                seq=next(self._seq),
                timestamp=time.time(),
                kind=kind,
                target=target,
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

    All three ``on_*`` hooks run on the UI thread and are the sole writers, so the
    text-coalescing state (:attr:`_last_kind`) needs no lock; the journal's own
    lock guards the shared buffer.
    """

    def __init__(self, journal: InteractionJournal) -> None:
        self._journal = journal
        # Kind of the most recent recorded event, used to coalesce a burst of
        # per-character ``on_text`` callbacks into a single ``text`` marker.
        self._last_kind: Optional[str] = None

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
    "resolve_target",
]
