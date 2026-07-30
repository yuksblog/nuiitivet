"""Shared diagnostics for ``X.of(context)`` ancestor lookups.

``of()`` resolves by walking *upward* from ``context``, so it can only work once
the widget has been attached to a tree. Calling it from ``__init__`` therefore
fails for a reason that has nothing to do with a missing provider, and the
"not found in ancestors" message sends the reader hunting for the wrong bug.

Every ``of()`` funnels its failure path through :func:`raise_if_premature_lookup`
so that the premature case is reported as such, consistently and without drift.
"""

from __future__ import annotations

from typing import Any, Final, Optional, Type, TypeVar

__all__ = [
    "find_provider",
    "is_premature_lookup",
    "premature_lookup_message",
    "raise_if_premature_lookup",
]

_MISSING: Final = object()

T = TypeVar("T")


def find_provider(context: Any, widget_type: Type[T]) -> Optional[T]:
    """Search upward for ``widget_type``, tolerating an uninitialized context.

    :meth:`Widget.find_ancestor` reads ``self._parent``, which does not exist
    before ``super().__init__()`` has run; that ``AttributeError`` is reported
    here as "not found" so the caller can hand it to
    :func:`raise_if_premature_lookup` for a message that explains itself.

    Args:
        context: The widget to search upward from.
        widget_type: The provider type to look for.

    Returns:
        The nearest matching ancestor, or ``None`` if there is none (or if
        ``context`` cannot be searched yet).
    """
    try:
        return context.find_ancestor(widget_type)  # type: ignore[no-any-return]
    except AttributeError:
        return None


def is_premature_lookup(context: Any) -> bool:
    """Return whether ``context`` cannot resolve ancestors yet.

    True only while the widget has no upward link *and* has not been mounted:

    - ``_parent`` missing entirely — ``of()`` ran before ``super().__init__()``.
    - ``_parent is None`` and not mounted — constructed, not yet attached.

    A widget with a parent, or a mounted root (whose ``_parent`` is legitimately
    ``None``), is *not* premature: for those, a failed lookup really does mean
    the provider is absent.

    Args:
        context: The widget the lookup started from.

    Returns:
        ``True`` if the ancestor chain does not exist yet.
    """
    parent = getattr(context, "_parent", _MISSING)
    if parent is _MISSING:
        return True
    if parent is not None:
        return False
    return not bool(getattr(context, "_mounted", False))


def premature_lookup_message(api: str, context: Any) -> str:
    """Build the error text for a premature :meth:`of` call.

    Args:
        api: The API being called, e.g. ``"Geometry.of"``.
        context: The widget the lookup started from.

    Returns:
        A message naming the cause (not mounted) and the fix (``on_mount``).
    """
    uninitialized = getattr(context, "_parent", _MISSING) is _MISSING
    cause = (
        "before super().__init__() had run, so it has no parent link yet"
        if uninitialized
        else "before it was mounted, so its ancestor chain does not exist yet"
    )
    return (
        f"{api}() was called on {type(context).__name__} {cause}. "
        f"This usually means the call is in __init__; a widget only learns its "
        f"parent when it is attached to the tree. Move the lookup to on_mount()."
    )


def raise_if_premature_lookup(api: str, context: Any) -> None:
    """Raise a premature-call ``RuntimeError`` when the lookup ran too early.

    Call this from an ``of()`` implementation *after* the ancestor search has
    come back empty, so that the genuine "no such provider above" case keeps its
    own message.

    Args:
        api: The API being called, e.g. ``"Geometry.of"``.
        context: The widget the lookup started from.

    Raises:
        RuntimeError: If ``context`` is not yet able to resolve ancestors.
    """
    if is_premature_lookup(context):
        raise RuntimeError(premature_lookup_message(api, context))
