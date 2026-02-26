"""Composable Widget built from modular responsibilities."""

from __future__ import annotations

import logging
from typing import Iterable, Optional, Tuple, Type, TypeVar, Union

from ..rendering.sizing import SizingLike
from nuiitivet.common.logging_once import exception_once
from nuiitivet.input.events import FocusEvent
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.observable.protocols import ReadOnlyObservableProtocol
from .modifier import Modifier, ModifierElement
from .widget_binding import BindingHostMixin
from .widget_builder import BuilderHostMixin
from .widget_children import ChildContainerMixin
from .widget_input import InputHubMixin
from .widget_kernel import PaddingLike, WidgetKernel
from .widget_lifecycle import LifecycleHostMixin

T = TypeVar("T")


logger = logging.getLogger(__name__)


class Widget(
    BindingHostMixin,
    LifecycleHostMixin,
    InputHubMixin,
    ChildContainerMixin,
    WidgetKernel,
):
    """Leaf-friendly widget base composed from mixins.

    This class intentionally does not participate in build/recomposition.
    Widgets that need `build()`/`rebuild()`/`scope()` must inherit
    `ComposableWidget`.
    """

    _layout_dependencies: Tuple[str, ...] = ()
    _paint_dependencies: Tuple[str, ...] = ()

    def __init__(
        self,
        *,
        width: Union[SizingLike, ReadOnlyObservableProtocol] = None,
        height: Union[SizingLike, ReadOnlyObservableProtocol] = None,
        padding: Union[PaddingLike, ReadOnlyObservableProtocol] = None,
        max_children: Optional[int] = None,
        overflow_policy: str = "none",
    ) -> None:
        self._layout_cache_token = 0
        self._needs_layout = True
        super().__init__(
            width=width,
            height=height,
            padding=padding,
            max_children=max_children,
            overflow_policy=overflow_policy,
        )

    @property
    def layout_cache_token(self) -> int:
        return int(self._layout_cache_token)

    def mark_needs_layout(self) -> None:
        """Mark this widget as needing layout recalculation."""
        already_dirty = self._needs_layout
        self._needs_layout = True
        parent = getattr(self, "_parent", None)
        if isinstance(parent, Widget):
            # Always propagate to root.  An early-return guard ("if already
            # dirty, skip") would be valid only if the invariant "every dirty
            # node's ancestors are also dirty" were globally maintained.
            # However, clear_needs_layout() is called only on AppScope (the
            # root), leaving intermediate nodes dirty.  When the next animation
            # tick fires, a selective guard would stop propagation at the first
            # already-dirty intermediate, never reaching the cleared root.
            # Walking all the way to the root on every call is O(tree-depth)
            # – the same cost as the original code when no ancestor was dirty.
            try:
                parent.mark_needs_layout()
            except Exception:
                exception_once(
                    logger,
                    f"widget_mark_needs_layout_parent_exc:{type(parent).__name__}",
                    "Widget.mark_needs_layout() failed for parent=%s",
                    type(parent).__name__,
                )
        if not already_dirty:
            self.invalidate()

    def invalidate(self, immediate: bool = False) -> None:
        app = getattr(self, "_app", None)
        if app is None:
            return
        try:
            app.invalidate(immediate=immediate)
        except TypeError:
            try:
                app.invalidate()
            except Exception:
                exception_once(
                    logger,
                    f"widget_invalidate_fallback_exc:{type(app).__name__}",
                    "App.invalidate() fallback call raised for app=%s",
                    type(app).__name__,
                )
        except Exception:
            exception_once(
                logger,
                f"widget_invalidate_exc:{type(app).__name__}",
                "App.invalidate(immediate=%s) raised for app=%s",
                immediate,
                type(app).__name__,
            )

    # --- Context lookup ----------------------------------------------------
    def find_ancestor(self, widget_type: Type[T]) -> Optional[T]:
        """Find the nearest ancestor of the specified type.

        Traverses up the widget tree looking for an ancestor that matches the given type.
        This is used to implement context lookup patterns like Navigator.of(context).

        Args:
            widget_type: The type of widget to find.

        Returns:
            The nearest ancestor of the specified type, or None if not found.

        Example:
            navigator = self.find_ancestor(Navigator)
            if navigator:
                navigator.push(...)
        """
        current = self._parent
        while current is not None:
            if isinstance(current, widget_type):
                return current  # type: ignore
            current = getattr(current, "_parent", None)
        return None

    # --- Modifiers ---------------------------------------------------------
    def modifier(self, modifier: Union[Modifier, ModifierElement]) -> Widget:
        """Apply a modifier to this widget, returning the wrapped result.

        Args:
            modifier: The modifier (or modifier element) to apply.

        Returns:
            The wrapped widget (e.g. ModifierBox) or the widget itself if modified in-place.
        """
        return modifier.apply(self)

    # --- Dependency invalidation ------------------------------------------
    def _invalidate_layout_cache(self) -> None:
        """Clear layout-related cached state (override in subclasses)."""

        self._layout_cache_token += 1
        self.mark_needs_layout()
        layout = getattr(self, "_layout", None)
        invalidate = getattr(layout, "invalidate_cache", None)
        if callable(invalidate):
            try:
                invalidate()
            except Exception:
                exception_once(
                    logger,
                    f"widget_invalidate_layout_cache_exc:{type(layout).__name__}",
                    "layout.invalidate_cache() failed for layout=%s",
                    type(layout).__name__,
                )

    def _invalidate_paint_cache(self) -> None:
        """Clear paint-related cached state (override in subclasses)."""

    def _handle_dependency_invalidation(self, dependency: Optional[str]) -> bool:
        layout_deps = getattr(type(self), "_layout_dependencies", ())
        paint_deps = getattr(type(self), "_paint_dependencies", ())
        if dependency is None:
            self._invalidate_layout_cache()
            self._invalidate_paint_cache()
            return True
        if isinstance(dependency, str):
            if dependency.startswith("scope:"):
                handler = getattr(self, "_handle_scope_invalidation", None)
                if callable(handler):
                    try:
                        handled = handler(dependency)
                    except Exception:
                        exception_once(
                            logger,
                            f"widget_handle_scope_invalidation_exc:{type(self).__name__}",
                            "_handle_scope_invalidation(dep=%s) raised for widget=%s",
                            dependency,
                            type(self).__name__,
                        )
                        handled = False
                    if handled:
                        return True
                return False
            scope_router = getattr(self, "_handle_scope_dependency", None)
            if callable(scope_router):
                try:
                    if scope_router(dependency):
                        return True
                except Exception:
                    exception_once(
                        logger,
                        f"widget_handle_scope_dependency_exc:{type(self).__name__}",
                        "_handle_scope_dependency(dep=%s) raised for widget=%s",
                        dependency,
                        type(self).__name__,
                    )
        handled = False
        if dependency in layout_deps:
            self._invalidate_layout_cache()
            handled = True
        if dependency in paint_deps:
            self._invalidate_paint_cache()
            handled = True
        if not handled:
            self._invalidate_layout_cache()
            self._invalidate_paint_cache()
        return True

    def invalidate_paint_cache(self) -> None:
        self._invalidate_paint_cache()
        self.invalidate()

    def paint_outsets(self) -> Tuple[int, int, int, int]:
        return (0, 0, 0, 0)


class ComposableWidget(BuilderHostMixin, Widget):
    """Widget base that participates in build/recomposition.

    Composition widgets can override `build()` and use `scope()` /
    `render_scope()` for fine-grained recomposition.
    """


def _normalize_dependencies(names: Iterable[Optional[str]]) -> Tuple[str, ...]:
    normalized = []
    for name in names:
        if name is None:
            continue
        value = str(name).strip()
        if value:
            normalized.append(value)
    return tuple(normalized)


def _extend_dependency_metadata(
    cls: type[Widget],
    attr: str,
    names: Iterable[str],
) -> type[Widget]:
    normalized = _normalize_dependencies(names)
    existing: Tuple[str, ...] = getattr(cls, attr, tuple())
    merged = tuple(sorted(set(existing).union(normalized)))
    setattr(cls, attr, merged)
    return cls


def layout_depends_on(*names: str):
    def decorator(cls: type[Widget]) -> type[Widget]:
        if not issubclass(cls, Widget):  # pragma: no cover - defensive guard
            raise TypeError("layout_depends_on can only decorate Widget subclasses")
        return _extend_dependency_metadata(cls, "_layout_dependencies", names)

    return decorator


def paint_depends_on(*names: str):
    def decorator(cls: type[Widget]) -> type[Widget]:
        if not issubclass(cls, Widget):  # pragma: no cover - defensive guard
            raise TypeError("paint_depends_on can only decorate Widget subclasses")
        return _extend_dependency_metadata(cls, "_paint_dependencies", names)

    return decorator


__all__ = [
    "Widget",
    "ComposableWidget",
    "FocusEvent",
    "PointerEvent",
    "layout_depends_on",
    "paint_depends_on",
]
