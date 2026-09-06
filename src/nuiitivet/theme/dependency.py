"""Dependency tracking for theme reads.

Reading the theme *is* how a widget subscribes to it. :meth:`Theme.of` marks the
reader here, and a theme change invalidates every marked reader that the
provider can reach. Widget authors never subscribe and never unsubscribe.

The mark lives on the **reader**, never on the provider. A provider that held
consumer references would keep every widget that ever read the theme alive for
the app's lifetime, and would need a matching release that authors can forget
silently -- which is exactly the failure mode this replaces. A mark on the
reader dies with the reader, so there is nothing to clean up.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator, List, Optional

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.context_lookup import find_app_scope

__all__ = [
    "current_theme_reader",
    "invalidate_theme_readers",
    "pop_theme_reader",
    "push_theme_reader",
    "register_theme_dependency",
    "theme_generation",
]

_logger = logging.getLogger(__name__)

#: Attribute set on a widget that has read the theme.
_MARK = "_reads_theme"

#: Hosts currently running ``build()``. A read inside a build belongs to the
#: enclosing recomposition scope rather than to whichever widget was handed in
#: as the context, so that a theme change rebuilds that scope.
_reader_stack: List[Any] = []


def push_theme_reader(reader: Any) -> None:
    """Make ``reader`` the target of theme reads until it is popped.

    Args:
        reader: The build host entering ``build()``.
    """
    _reader_stack.append(reader)


def pop_theme_reader() -> None:
    """Undo the most recent :func:`push_theme_reader`."""
    if _reader_stack:
        _reader_stack.pop()


def current_theme_reader() -> Optional[Any]:
    """Return the build host currently reading, or ``None`` outside a build."""
    return _reader_stack[-1] if _reader_stack else None


def register_theme_dependency(context: Any) -> None:
    """Record that a theme read happened, so a theme change can undo it.

    Inside ``build()`` the dependency is attributed to the building host, which
    is what a theme change rebuilds. Outside one -- a leaf reading in ``paint()``
    or ``preferred_size()`` -- it is attributed to ``context`` itself, which a
    theme change re-measures and repaints.

    Args:
        context: The widget the read resolved against.
    """
    reader = current_theme_reader()
    if reader is None:
        reader = context
    try:
        setattr(reader, _MARK, True)
    except Exception:
        exception_once(
            _logger,
            f"theme_dependency_mark_exc:{type(reader).__name__}",
            "Failed to mark theme reader (reader=%s)",
            type(reader).__name__,
        )


def theme_generation(context: Any) -> int:
    """Return how many times the theme above ``context`` has changed.

    For the widgets that cannot re-derive a value on every read and have to keep
    it on a field -- a button resolves its colour animation endpoints to concrete
    RGBA -- this is what says whether what they hold is still current.

    Comparing the ``Theme`` object instead would be subtly wrong: ``Theme`` is
    frozen but its ``extensions`` list and a ``MaterialThemeData``'s ``roles``
    dict are not, so a theme mutated in place and re-installed is a real change
    that arrives on the same object. The counter moves regardless.

    Args:
        context: A widget in the subtree to resolve the provider from.

    Returns:
        The provider's change count, or ``-1`` when no ``AppScope`` is reachable.
    """
    scope = find_app_scope(context)
    if scope is None:
        return -1
    try:
        return int(scope.theme_manager.generation)
    except Exception:
        exception_once(
            _logger,
            "theme_dependency_generation_exc",
            "Failed to read ThemeManager.generation",
        )
        return -1


def _iter_subtree(root: Any) -> Iterator[Any]:
    """Yield ``root`` and every widget below it, built children included."""
    stack: List[Any] = [root]
    seen: set[int] = set()
    while stack:
        node = stack.pop()
        if node is None or id(node) in seen:
            continue
        seen.add(id(node))
        yield node
        try:
            children = getattr(node, "children", None)
            if children:
                stack.extend(list(children))
        except Exception:
            exception_once(
                _logger,
                f"theme_dependency_children_exc:{type(node).__name__}",
                "Failed to read children while walking for theme readers (node=%s)",
                type(node).__name__,
            )
        try:
            built = getattr(node, "built_child", None)
            if built is not None:
                stack.append(built)
        except Exception:
            exception_once(
                _logger,
                f"theme_dependency_built_child_exc:{type(node).__name__}",
                "Failed to read built_child while walking for theme readers (node=%s)",
                type(node).__name__,
            )


def invalidate_theme_readers(root: Any) -> None:
    """Invalidate every theme reader in ``root``'s subtree.

    Composables are rebuilt, so a value read in ``build()`` and embedded in the
    returned tree is replaced. Leaves are re-measured and repainted, so a value
    read in ``preferred_size()`` or ``paint()`` is resolved again.

    The walk is O(tree), which is affordable because a theme change is a user
    action rather than a per-frame event.

    Args:
        root: The provider whose subtree should be refreshed, i.e. the
            ``AppScope``.
    """
    # Collect first: rebuilding a composable mutates the tree underneath us.
    readers = [node for node in _iter_subtree(root) if getattr(node, _MARK, False)]
    for reader in readers:
        # A composable's build output is stale, so discard it. Leaves have no
        # build to redo and are simply asked to measure and draw again.
        rebuild = getattr(reader, "rebuild", None)
        if callable(rebuild):
            try:
                rebuild()
            except Exception:
                exception_once(
                    _logger,
                    f"theme_dependency_rebuild_exc:{type(reader).__name__}",
                    "rebuild() raised while refreshing a theme reader (reader=%s)",
                    type(reader).__name__,
                )
            continue
        # The theme carries shape and typography as well as colour, so a change
        # can move geometry. Re-measure rather than only repaint. Dropping the
        # paint cache subsumes invalidate(), so only fall back to it when the
        # reader has no cache to drop.
        names = ("mark_needs_layout", "invalidate_paint_cache")
        if not callable(getattr(reader, "invalidate_paint_cache", None)):
            names = ("mark_needs_layout", "invalidate")
        for method_name in names:
            method = getattr(reader, method_name, None)
            if not callable(method):
                continue
            try:
                method()
            except Exception:
                exception_once(
                    _logger,
                    f"theme_dependency_{method_name}_exc:{type(reader).__name__}",
                    "%s() raised while refreshing a theme reader (reader=%s)",
                    method_name,
                    type(reader).__name__,
                )
