"""Keyboard shortcut value types.

A :class:`Shortcut` is a key gesture (``Accel+S``, ``Ctrl+Shift+Z``); a
:class:`ShortcutBinding` pairs that gesture with the callback it triggers. Both
are pure values — they carry no widget-tree or backend state, so they can be
declared as constants and shared between a menu item and a
:func:`~nuiitivet.modifiers.key_shortcut` binding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


#: What :func:`~nuiitivet.modifiers.key_shortcut` accepts: a typed gesture or its
#: string spec.
ShortcutLike = Union[Shortcut, str]


def to_shortcut(shortcut: ShortcutLike) -> Shortcut:
    """Coerce a :data:`ShortcutLike` to a :class:`Shortcut`."""
    if isinstance(shortcut, Shortcut):
        return shortcut
    return Shortcut.parse(shortcut)


@dataclass(frozen=True)
class ShortcutBinding:
    """A gesture bound to the callback it triggers.

    This is the unit the shortcut dispatch tier stores, kept as a type rather
    than a bare callable so richer command semantics (``can_execute``, menu
    binding) can be added without changing every call site.

    Args:
        shortcut: The gesture that triggers the binding.
        on_trigger: Called with no arguments when the gesture fires. May be sync
            or async.
    """

    shortcut: Shortcut
    on_trigger: VoidCallback = field(compare=False)
