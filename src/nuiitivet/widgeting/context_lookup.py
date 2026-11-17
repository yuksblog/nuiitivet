"""Shared machinery for ``X.of(context)`` lookups.

``of()`` resolves by walking *upward* from ``context``, so it can only work once
the widget has been attached to a tree. Calling it from ``__init__`` therefore
fails for a reason that has nothing to do with a missing provider, and the
"not found in ancestors" message sends the reader hunting for the wrong bug.

Every ``of()`` funnels its failure path through :func:`raise_if_premature_lookup`
so that the premature case is reported as such, consistently and without drift.

:func:`find_window` is the second half: some providers are owned by the
``Window`` rather than placed in the tree by the author, and the Window's own
``Overlay`` is not even an ancestor of the content (it is a sibling layer of
the ``Navigator``). Those ``of()`` implementations fall back to the Window
reached through :class:`~nuiitivet.runtime.window.WindowScope`, which keeps
the answer scoped to *this* window instead of a process-wide global.
:func:`find_app` resolves the app-wide half through
:class:`~nuiitivet.runtime.app.AppScope`.

:class:`ContextProxy` is the base of what ``X.proxy(context)`` returns: a
stand-in made in ``__init__`` that runs the lookup when it is used.
"""

from __future__ import annotations

import logging
import weakref
from typing import TYPE_CHECKING, Any, Callable, Final, Generic, Optional, Type, TypeVar

if TYPE_CHECKING:
    from nuiitivet.runtime.app import App, AppScope
    from nuiitivet.runtime.window import Window

logger = logging.getLogger(__name__)

__all__ = [
    "ContextProxy",
    "find_app",
    "find_app_scope",
    "find_provider",
    "forget_app_scope",
    "find_window",
    "is_premature_lookup",
    "is_uninitialized_context",
    "premature_lookup_message",
    "raise_if_premature_lookup",
    "raise_if_uninitialized_proxy",
]

_MISSING: Final = object()

#: Attribute holding a widget's resolved ``AppScope`` while it is mounted.
_APP_SCOPE_CACHE: Final = "_app_scope"

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


def find_app_scope(context: Any) -> Optional["AppScope"]:
    """Return the nearest :class:`~nuiitivet.runtime.app.AppScope` above ``context``.

    The answer is remembered on ``context`` for as long as it stays mounted:
    a widget changes the tree it belongs to only through ``mount()`` and
    ``unmount()``, and both call :func:`forget_app_scope`. ``Theme.of`` runs
    on every paint of every leaf, so the walk happens once per mount instead
    of once per frame.

    Nothing is remembered while the walk comes back empty -- a widget measured
    before it is attached must resolve the real scope on its next read.

    Args:
        context: The widget to search upward from.

    Returns:
        The nearest ``AppScope``, or ``None`` if there is none (or if
        ``context`` cannot be searched yet).
    """
    scope: Optional["AppScope"] = getattr(context, _APP_SCOPE_CACHE, None)
    if scope is not None:
        return scope
    from nuiitivet.runtime.app import AppScope

    scope = find_provider(context, AppScope)
    if scope is not None:
        setattr(context, _APP_SCOPE_CACHE, scope)
    return scope


def forget_app_scope(context: Any) -> None:
    """Drop what :func:`find_app_scope` remembered on ``context``.

    Called by ``mount()`` and ``unmount()``: a re-mount resolves afresh, and
    an unmounted widget does not keep its old tree alive through the cache.

    Args:
        context: The widget leaving its tree.
    """
    if getattr(context, _APP_SCOPE_CACHE, None) is not None:
        setattr(context, _APP_SCOPE_CACHE, None)


def find_app(context: Any) -> Optional["App"]:
    """Return the :class:`~nuiitivet.runtime.app.App` owning ``context``'s tree.

    Resolved through the ``AppScope`` that wraps every App-built root, so two
    Apps in one process each see their own. Returns ``None`` for a widget tree
    that no App owns -- a bare tree in a test, or a widget not attached yet.

    Args:
        context: The widget to search upward from.

    Returns:
        The owning App, or ``None`` if there is none to be found.
    """
    scope = find_app_scope(context)
    if scope is None:
        return None
    return scope.app


def find_window(context: Any) -> Optional["Window"]:
    """Return the :class:`~nuiitivet.runtime.window.Window` owning ``context``.

    Resolved through the ``WindowScope`` that wraps every window root, so each
    window in one process sees its own. Returns ``None`` for a widget tree
    that no Window owns — a bare tree in a test, or a widget not attached yet.

    Args:
        context: The widget to search upward from.

    Returns:
        The owning Window, or ``None`` if there is none to be found.
    """
    from nuiitivet.runtime.window import WindowScope

    scope = find_provider(context, WindowScope)
    if scope is None:
        return None
    return scope.window


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


def is_uninitialized_context(context: Any) -> bool:
    """Return whether ``context`` has no parent link *attribute* at all.

    The strict subset of :func:`is_premature_lookup` that can only mean one
    thing: the lookup ran before ``super().__init__()``, so the widget is still
    mid-construction. Unlike the broader predicate this cannot be confused with
    a fully built widget that simply has not been attached yet -- which is a
    legitimate state for offscreen measurement and for tests.

    Args:
        context: The widget the lookup started from.

    Returns:
        ``True`` if ``context`` has not run ``Widget.__init__`` yet.
    """
    return getattr(context, "_parent", _MISSING) is _MISSING


def premature_lookup_message(api: str, context: Any) -> str:
    """Build the error text for a premature :meth:`of` call.

    Args:
        api: The API being called, e.g. ``"Geometry.of"``.
        context: The widget the lookup started from.

    Returns:
        A message naming the cause (not mounted) and the fix (``proxy``, or
        a later lookup).
    """
    uninitialized = getattr(context, "_parent", _MISSING) is _MISSING
    cause = (
        "before super().__init__() had run, so it has no parent link yet"
        if uninitialized
        else "before it was mounted, so its ancestor chain does not exist yet"
    )
    proxy = f"{api.rsplit('.', 1)[0]}.proxy"
    return (
        f"{api}() was called on {type(context).__name__} {cause}. "
        f"This usually means the call is in __init__; a widget only learns its "
        f"parent when it is attached to the tree. Use {proxy}(self) there, or "
        f"move the lookup to an event handler or on_mount()."
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


def raise_if_uninitialized_proxy(api: str, context: Any) -> None:
    """Raise when ``X.proxy(context)`` ran before ``super().__init__()``.

    Args:
        api: The API being called, e.g. ``"Geometry.proxy"``.
        context: The widget the proxy is made for.

    Raises:
        RuntimeError: If ``context`` has not run ``Widget.__init__`` yet.
    """
    if is_uninitialized_context(context):
        raise RuntimeError(
            f"{api}() was called on {type(context).__name__} before super().__init__() "
            f"had run. Call super().__init__() first."
        )


P = TypeVar("P")


class ContextProxy(Generic[P]):
    """A stand-in for the provider an ``of()`` lookup resolves from one widget.

    It holds the widget weakly and runs the lookup at each use. A use before
    the widget is mounted raises. After the widget is unmounted, or collected,
    there is no provider: the subclass drops the call.
    """

    def __init__(self, api: str, context: Any, lookup: Callable[[Any], P], *, keep: bool = False) -> None:
        """Make the stand-in for ``lookup(context)``.

        Args:
            api: The API that made this proxy, e.g. ``"Overlay.proxy"``.
            context: The widget to look up from.
            lookup: The ``of()`` call, taking the widget.
            keep: Remember the provider resolved at each mount, and answer
                with it after the unmount. For a provider that outlives the
                widget.

        Raises:
            RuntimeError: If ``context`` has not run ``Widget.__init__`` yet.
        """
        raise_if_uninitialized_proxy(api, context)
        self._api = api
        self._context = weakref.ref(context)
        self._context_name = type(context).__name__
        self._lookup = lookup
        self._kept: Optional[weakref.ReferenceType[P]] = None
        self._drop_logged = False
        if keep:
            context._add_pre_mount_hook(self._keep)

    def _keep(self) -> None:
        context = self._context()
        if context is None:
            return
        try:
            self._kept = weakref.ref(self._lookup(context))
        except RuntimeError:
            # A tree with no provider: the use reports it.
            return

    def _provider(self) -> Optional[P]:
        """Return the provider to forward to, or ``None`` to drop the call.

        Raises:
            RuntimeError: If the widget is not mounted yet, or its tree has no
                provider.
        """
        context = self._context()
        if context is not None and not getattr(context, "_unmounted", False):
            if is_premature_lookup(context):
                raise RuntimeError(
                    f"{self._api}({self._context_name}) was used before {self._context_name} "
                    f"was mounted, so its ancestor chain does not exist yet. A proxy can be "
                    f"made in __init__; use it once the widget is in the tree."
                )
            return self._lookup(context)
        kept = self._kept() if self._kept is not None else None
        if kept is None and not self._drop_logged:
            self._drop_logged = True
            logger.debug("%s: call dropped, %s is no longer mounted", self._api, self._context_name)
        return kept
