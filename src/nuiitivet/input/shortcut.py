"""Keyboard shortcut value types.

A :class:`Shortcut` is a key gesture (``Accel+S``, ``Ctrl+Shift+Z``); a
:class:`ShortcutBinding` pairs that gesture with the callback it triggers. Both
are pure values — they carry no widget-tree or backend state, so they can be
declared as constants and shared between a menu item and a
:func:`~nuiitivet.modifiers.key_shortcut` binding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Union

from ..widgeting.callbacks import VoidCallback
from .codes import (
    MOD_ACCEL,
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    resolve_modifiers,
)

_MODIFIER_NAMES: dict[str, int] = {
    "shift": MOD_SHIFT,
    "ctrl": MOD_CTRL,
    "control": MOD_CTRL,
    "alt": MOD_ALT,
    "option": MOD_ALT,
    "opt": MOD_ALT,
    "meta": MOD_META,
    "cmd": MOD_META,
    "command": MOD_META,
    "super": MOD_META,
    "win": MOD_META,
    "accel": MOD_ACCEL,
    "primary": MOD_ACCEL,
}

_KEY_ALIASES: dict[str, str] = {
    "esc": "escape",
    "return": "enter",
    "del": "delete",
    "ins": "insert",
    "pgup": "pageup",
    "pgdn": "pagedown",
}


#: Keys that yield text without being a single character.
_TEXT_KEY_NAMES: frozenset[str] = frozenset({"space"})

#: Non-letter keys whose display form is not just ``capitalize()``.
_DISPLAY_KEY_NAMES: dict[str, str] = {
    "escape": "Esc",
    "delete": "Del",
    "insert": "Ins",
    "pageup": "Page Up",
    "pagedown": "Page Down",
}


def _display_key_name(key: str) -> str:
    """Return the display form of a normalized key name (``"s"`` → ``"S"``)."""
    if len(key) == 1:
        return key.upper()
    if key.startswith("f") and key[1:].isdigit():
        return key.upper()
    return _DISPLAY_KEY_NAMES.get(key, key.capitalize())


def normalize_key_name(key: str) -> str:
    """Normalize a key name to the form shortcuts are matched in.

    Lowercases, drops the leading underscore that backends put in front of digit
    keys (pyglet reports ``1`` as ``_1``), and applies the common spelling
    aliases (``esc`` → ``escape``). Both sides of a match run through this, so a
    shortcut written as ``"Accel+1"`` still fires on the ``_1`` the backend
    delivers.
    """
    name = key.strip().lower()
    if len(name) > 1 and name.startswith("_"):
        name = name[1:]
    return _KEY_ALIASES.get(name, name)


def produces_text(key: str, modifier_keys: int) -> bool:
    """Return True if this key press may be consumed as text input.

    This keeps the shortcut tier off keys a focused text field is about to turn
    into characters. Text insertion arrives through the separate ``on_text``
    route, so the ``on_key`` return value the dispatcher sees cannot tell it that
    the key was consumed after all.

    The answer cannot be exact. Windows reports AltGr as ``Ctrl+Alt``, and a
    German layout turns ``AltGr+Q`` into ``@``; macOS ``Option`` both produces
    characters (``Option+A`` → ``å``) and starts dead-key compositions that
    resolve only on the *next* keystroke; and the active layout can change at
    runtime. So this errs **toward** text: a misjudgement must cost a shortcut
    that does not fire — recoverable, and obvious to the user — never a keystroke
    that silently runs a command.

    Args:
        key: The key name, as delivered by the backend.
        modifier_keys: The physical modifier-key mask held with it. ``MOD_ACCEL``
            is not expected here; backends never emit it.
    """
    if modifier_keys & MOD_ALT:
        # Alt is text on macOS (Option), and Windows/X11 spell AltGr as Ctrl+Alt,
        # so no Alt gesture can be ruled out as non-text on any platform.
        return True
    if modifier_keys & (MOD_CTRL | MOD_META):
        # Ctrl/Cmd without Alt produce no text on any platform.
        return False

    # Bare or Shift-only: text iff the key is one the layout can insert.
    name = normalize_key_name(key)
    return len(name) == 1 or name in _TEXT_KEY_NAMES


@dataclass(frozen=True)
class Shortcut:
    """A key gesture: one key plus a mask of the modifiers held with it.

    Args:
        key: The key name, normalized via :func:`normalize_key_name`
            (e.g. ``"s"``, ``"enter"``, ``"f1"``).
        modifiers: A bitmask of ``MOD_*`` values, which may include
            ``MOD_ACCEL`` — the logical primary modifier, resolved to Cmd on
            macOS and Ctrl elsewhere when the gesture is matched.
    """

    key: str
    modifiers: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", normalize_key_name(self.key))

    @classmethod
    def parse(cls, spec: str) -> "Shortcut":
        """Parse a ``"Accel+Shift+S"``-style spec into a :class:`Shortcut`.

        Modifier names are case-insensitive and accept the usual spellings:
        ``Accel``/``Primary``, ``Ctrl``/``Control``, ``Alt``/``Option``,
        ``Meta``/``Cmd``/``Command``/``Super``/``Win``, ``Shift``. The last
        token is the key. A literal ``+`` is written as the final token
        (``"Accel++"``).

        Raises:
            ValueError: If the spec is empty, names an unknown modifier, or
                carries no key.
        """
        tokens = [t.strip() for t in spec.split("+")]
        if tokens and tokens[-1] == "" and len(tokens) > 1:
            # Trailing empty token means the key itself is "+" ("Accel++").
            tokens = tokens[:-2] + ["+"]

        if not tokens or not tokens[-1]:
            raise ValueError(f"Shortcut spec has no key: {spec!r}")

        modifiers = 0
        for token in tokens[:-1]:
            mod = _MODIFIER_NAMES.get(token.lower())
            if mod is None:
                raise ValueError(f"Unknown modifier {token!r} in shortcut spec {spec!r}")
            modifiers |= mod

        return cls(key=tokens[-1], modifiers=modifiers)

    def matches(self, key: str, modifier_keys: int) -> bool:
        """Return True if a key press of ``key`` with ``modifier_keys`` is this gesture.

        ``MOD_ACCEL`` is resolved to the platform's physical modifier here, and
        the modifier mask must match exactly — ``Accel+S`` does not fire on
        ``Accel+Shift+S``.
        """
        return normalize_key_name(key) == self.key and modifier_keys == resolve_modifiers(self.modifiers)

    @property
    def display(self) -> str:
        """Human-readable accelerator label for this gesture, per platform.

        macOS uses the compact symbol form in Apple's canonical modifier order
        (``⌃⌥⇧⌘S``); other platforms use the ``Ctrl+Shift+S`` form.
        ``MOD_ACCEL`` renders as its resolved physical modifier (⌘ on macOS,
        ``Ctrl`` elsewhere), so one :class:`Shortcut` yields the right label
        everywhere — this is what menu items show next to their command.
        """
        import sys

        mods = resolve_modifiers(self.modifiers)
        key_label = _display_key_name(self.key)
        if sys.platform == "darwin":
            parts = []
            if mods & MOD_CTRL:
                parts.append("⌃")
            if mods & MOD_ALT:
                parts.append("⌥")
            if mods & MOD_SHIFT:
                parts.append("⇧")
            if mods & MOD_META:
                parts.append("⌘")
            parts.append(key_label)
            return "".join(parts)
        parts = []
        if mods & MOD_CTRL:
            parts.append("Ctrl")
        if mods & MOD_ALT:
            parts.append("Alt")
        if mods & MOD_SHIFT:
            parts.append("Shift")
        if mods & MOD_META:
            parts.append("Meta")
        parts.append(key_label)
        return "+".join(parts)

    @property
    def conflicts_with_text_input(self) -> bool:
        """Return True if this gesture is one a focused text field would type.

        Such a gesture does not fire while a text field holds focus — the field
        turns it into a character instead. ``Alt`` gestures count as conflicting
        on every platform, so they are unavailable there too; see
        :func:`produces_text` for why that cannot be narrowed down safely.
        """
        return produces_text(self.key, resolve_modifiers(self.modifiers))


#: What :func:`~nuiitivet.modifiers.key_shortcut` accepts: a typed gesture or its
#: string spec.
ShortcutLike = Union[Shortcut, str]


def to_shortcut(shortcut: ShortcutLike) -> Shortcut:
    """Coerce a :data:`ShortcutLike` to a :class:`Shortcut`."""
    if isinstance(shortcut, Shortcut):
        return shortcut
    return Shortcut.parse(shortcut)


class ShortcutScope(Enum):
    """When a :class:`ShortcutBinding` is live.

    The members widen: each is a superset of the one before it.

    Attributes:
        FOCUS: Live only while the subtree contains the focused node. Needed only
            when the same command has several targets on screen **at once** (a
            dual-pane file manager, a split-view editor), so nothing but focus
            can decide which one acts.
        FOREGROUND: Live while the subtree is on the topmost interactable layer —
            not hidden, not on a covered route, not behind a blocking overlay.
            The default, and the right answer for almost everything.
        MOUNT: Live while the subtree is in the widget tree at all, displayed or
            not. How an app-wide command is expressed: bind it on the content
            root, which stays mounted across navigation.
    """

    FOCUS = "focus"
    FOREGROUND = "foreground"
    MOUNT = "mount"


@dataclass(frozen=True)
class ShortcutBinding:
    """A gesture bound to the callback it triggers, and the scope it is live in.

    This is the unit the shortcut dispatch tier stores, kept as a type rather
    than a bare callable so richer command semantics (``can_execute``, menu
    binding) can be added without changing every call site.

    Args:
        shortcut: The gesture that triggers the binding.
        on_trigger: Called with no arguments when the gesture fires. May be sync
            or async.
        scope: When the binding is live. Defaults to
            :attr:`ShortcutScope.FOREGROUND`.
    """

    shortcut: Shortcut
    on_trigger: VoidCallback = field(compare=False)
    scope: ShortcutScope = ShortcutScope.FOREGROUND
