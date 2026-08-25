"""Foundational attributes shared by all widgets."""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple, TypeAlias, Union

from ..common.logging_once import exception_once
from ..rendering.padding import PaddingLike, parse_padding
from ..rendering.size import Size
from ..rendering.sizing import Sizing, SizingLike, parse_sizing
from ..runtime.threading import assert_ui_thread
from .widget_size_change import SizeCallback, invoke_size_callback, queue_size_change
from nuiitivet.observable.protocols import ObservableBase


_logger = logging.getLogger(__name__)

Rect: TypeAlias = Tuple[int, int, int, int]


class WidgetKernel:
    """Provides layout primitives and shared widget state."""

    _parent: Optional["WidgetKernel"]
    _last_rect: Optional[Rect]
    _layout_rect: Optional[Rect]
    # ``None`` until a size callback is attached: every widget carries these, so
    # the common case must not allocate a list.
    _size_callbacks: Optional[List[SizeCallback]]
    _reported_size: Optional[Size]
    # Memoized preferred_size results, owned by ``layout.measure``; ``None``
    # until first measured. Dropped by ``mark_needs_layout()`` so any change
    # that dirties layout also re-measures.
    _measure_cache: Optional[List[Tuple[Optional[int], Optional[int], int, int]]] = None

    def __init__(
        self,
        *,
        width: Union[SizingLike, ObservableBase] = None,
        height: Union[SizingLike, ObservableBase] = None,
        padding: Union[PaddingLike, ObservableBase] = None,
        **_: Any,
    ) -> None:
        super().__init__()
        self._parent = None
        self._last_rect = None
        self._layout_rect = None
        self._size_callbacks = None
        self._reported_size = None

        # Initialize with None/default first, as properties will handle observables later
        # But properties rely on binding mixin capabilities already being initialized?
        # Typically MRO calls Mixins.__init__ FIRST if using super().
        # Wait, WidgetKernel calls super().__init__() at top.
        # But WidgetKernel is at the END of Widget MRO.
        # So BindingHostMixin.__init__ has already run.

        # However, we cannot pass Observable to parse_sizing.
        # We should use the setters we defined!
        # But setters need `self` to be fully initialized?

        # Initialize internal storage to defaults first to satisfy type checker/logic
        self._width_sizing = parse_sizing(None)
        self._height_sizing = parse_sizing(None)
        self._padding = (0, 0, 0, 0)

        self._layout_align: Optional[Union[str, Tuple[str, str]]] = None
        self._cross_align: Optional[str] = None

        # Now use property setters which handle Observables
        self.width_sizing = width  # type: ignore
        self.height_sizing = height  # type: ignore
        self.padding = padding  # type: ignore

    @property
    def parent(self) -> Optional["WidgetKernel"]:
        return self._parent

    @property
    def needs_layout(self) -> bool:
        return bool(getattr(self, "_needs_layout", True))

    def clear_needs_layout(self) -> None:
        self._needs_layout = False

    @property
    def layout_cache_token(self) -> Optional[int]:
        return None

    @property
    def layout_rect(self) -> Optional[Rect]:
        return self._layout_rect

    @property
    def global_layout_rect(self) -> Optional[Rect]:
        """Return this widget's layout rectangle in root (global) coordinates.

        This is derived purely from layout state by accumulating ancestor
        layout offsets. It intentionally does not depend on paint-time state
        like `last_rect`.
        """

        rect = self._layout_rect
        if rect is None:
            return None
        x, y, w, h = rect

        current = self._parent
        visited: set[int] = set()
        while current is not None:
            ident = id(current)
            if ident in visited:
                break
            visited.add(ident)

            parent_rect = getattr(current, "layout_rect", None)
            if parent_rect:
                px, py, _pw, _ph = parent_rect
                x += int(px)
                y += int(py)
            current = getattr(current, "parent", None)

        return (int(x), int(y), int(w), int(h))

    def set_layout_rect(self, x: int, y: int, width: int, height: int) -> None:
        self._layout_rect = (int(x), int(y), int(width), int(height))
        if self._size_callbacks:
            # Queue only; the callbacks run after layout. Position is not part of
            # the report, so a widget that merely moves does not fire.
            queue_size_change(self, Size(int(width), int(height)))

    def clear_layout_rect(self) -> None:
        self._layout_rect = None

    @property
    def last_rect(self) -> Optional[Rect]:
        return self._last_rect

    def set_last_rect(self, x: int, y: int, width: int, height: int) -> None:
        self._last_rect = (int(x), int(y), int(width), int(height))

    def clear_last_rect(self) -> None:
        self._last_rect = None

    # --- Size reporting ----------------------------------------------------
    def add_size_callback(self, callback: SizeCallback) -> None:
        """Register *callback* to receive this widget's own measured size.

        The callback is dispatched between frames (never inline from
        :meth:`set_layout_rect`), and only when the size actually changed. It
        fires once with the first measurement: registering on a widget that has
        already been laid out invokes it immediately, since registration happens
        at build time and is therefore outside the layout pass.

        Args:
            callback: A callable taking a :class:`Size`, sync or async.
        """
        if self._size_callbacks is None:
            self._size_callbacks = []
        self._size_callbacks.append(callback)
        rect = self._layout_rect
        if rect is None:
            return
        size = Size(rect[2], rect[3])
        if self._reported_size is None:
            self._reported_size = size
        invoke_size_callback(callback, size, owner_name=type(self).__name__)

    def _dispatch_size_change(self, size: Size) -> bool:
        """Deliver a queued measurement to the callbacks; report whether it ran."""
        callbacks = self._size_callbacks
        if not callbacks:
            return False
        if size == self._reported_size:
            return False
        self._reported_size = size
        owner_name = type(self).__name__
        for callback in list(callbacks):
            invoke_size_callback(callback, size, owner_name=owner_name)
        return True

    # --- Sizing helpers -------------------------------------------------
    @property
    def width_sizing(self) -> Sizing:
        return self._width_sizing

    @width_sizing.setter
    def width_sizing(self, value: Union[SizingLike, ObservableBase]) -> None:
        if isinstance(value, ObservableBase):
            if hasattr(self, "observe"):
                self.observe(value, lambda v: setattr(self, "width_sizing", v))  # type: ignore
            return
        self._width_sizing = parse_sizing(value)
        self._notify_layout_param_changed()

    @property
    def height_sizing(self) -> Sizing:
        return self._height_sizing

    @height_sizing.setter
    def height_sizing(self, value: Union[SizingLike, ObservableBase]) -> None:
        if isinstance(value, ObservableBase):
            if hasattr(self, "observe"):
                self.observe(value, lambda v: setattr(self, "height_sizing", v))  # type: ignore
            return
        self._height_sizing = parse_sizing(value)
        self._notify_layout_param_changed()

    # --- Padding helpers ---------------------------------------------------
    @property
    def padding(self) -> Tuple[int, int, int, int]:
        return self._padding

    @padding.setter
    def padding(self, pad: Union[PaddingLike, ObservableBase]) -> None:
        if isinstance(pad, ObservableBase):
            if hasattr(self, "observe"):
                self.observe(pad, lambda v: setattr(self, "padding", v))  # type: ignore
            return
        try:
            self._padding = parse_padding(pad)
        except Exception:
            self._padding = (0, 0, 0, 0)
        self._notify_layout_param_changed()

    @property
    def layout_align(self) -> Optional[Union[str, Tuple[str, str]]]:
        return self._layout_align

    @layout_align.setter
    def layout_align(self, value: Optional[Union[str, Tuple[str, str]]]) -> None:
        self._layout_align = value
        self._notify_layout_param_changed()

    @property
    def cross_align(self) -> Optional[str]:
        return self._cross_align

    @cross_align.setter
    def cross_align(self, value: Optional[str]) -> None:
        self._cross_align = str(value) if value is not None else None
        self._notify_layout_param_changed()

    def content_rect(self, x: int, y: int, width: int, height: int) -> Tuple[int, int, int, int]:
        """Return the inner rectangle after subtracting padding."""

        l, t, r, b = self._padding
        cx = x + int(l)
        cy = y + int(t)
        cw = max(0, int(width) - int(l) - int(r))
        ch = max(0, int(height) - int(t) - int(b))
        return (cx, cy, cw, ch)

    def mark_needs_layout(self) -> None:
        """Mark this widget as needing layout and propagate up the tree."""
        self._needs_layout = True
        self._measure_cache = None
        if self._parent:
            marker = getattr(self._parent, "mark_needs_layout", None)
            if callable(marker):
                marker()

    # --- Rendering helpers -------------------------------------------------
    def layout(self, width: int, height: int) -> None:
        """Compute layout geometry for this widget and its children.

        Default implementation accepts the assigned size.

        Child layout must be performed by container widgets (e.g. Row/Column/Box).
        Automatically laying out children here causes duplicate/exponential layout
        passes when containers also lay out children.
        """
        if __debug__:
            assert_ui_thread()
        self.clear_needs_layout()
        # Preserve the widget's position in its parent.
        # `layout_rect` is defined in parent coordinate space.
        current = self._layout_rect
        x = int(current[0]) if current is not None else 0
        y = int(current[1]) if current is not None else 0
        self.set_layout_rect(x, y, width, height)

    # --- Hit testing -------------------------------------------------------
    #
    # Hit participation factors into two internal axes (issue #448):
    #   S -- self surface: does this widget's own rect become the hit target?
    #   C -- children:     does hit-testing descend into this subtree?
    #
    # The default resolves S as ``auto``: a widget catches on its own surface
    # only when it paints a visible surface or is interactive; a bare,
    # non-painting layout/alignment container defers to its children. The
    # S tri-state (none/painted/all) is intentionally internal -- there is no
    # public string enum or raw S API here.

    def hit_test(self, x: int, y: int):
        """Return the widget located at the coordinate if any.

        Resolves the internal S x C hit-participation model: descends into
        children first, then falls back to this widget's own surface via the
        ``auto`` policy (see :meth:`_hit_self_opaque`).
        """

        return self._resolve_hit(x, y, child_hit=self._hit_test_children(x, y))

    def _hit_test_children(self, x: int, y: int):
        """Descend into children (C axis) and return the first hit, or ``None``.

        Children are visited top-most first (reverse order) for correct
        Z-order hit testing.
        """

        children: Tuple = getattr(self, "children", tuple())
        for child in reversed(children):
            # Try to use layout rect for coordinate translation
            rect = getattr(child, "layout_rect", None)

            if rect:
                rx, ry, rw, rh = rect
                # Check if point is within child's bounds (in parent's coordinate space)
                if rx <= x < rx + rw and ry <= y < ry + rh:
                    # Translate to child's local coordinate space
                    hit = child.hit_test(x - rx, y - ry)
                    if hit:
                        return hit
            else:
                # Fallback for non-layout widgets or unlaid-out children
                # If no layout rect, we assume the child is positioned at (0,0) or handles its own hit testing
                # without coordinate translation.
                hit = child.hit_test(x, y)
                if hit:
                    return hit

        return None

    def _resolve_hit(
        self,
        x: int,
        y: int,
        *,
        child_hit: Optional["WidgetKernel"],
        self_opaque: Optional[bool] = None,
    ) -> Optional["WidgetKernel"]:
        """Combine a child-descent result (C) with the self-surface policy (S).

        Args:
            child_hit: The target found by descending into children, or ``None``.
            self_opaque: Whether this widget's own surface catches the hit
                (resolved S). ``None`` resolves it via the ``auto`` default
                (:meth:`_hit_self_opaque`); pass ``False`` for pure pass-through
                wrappers that must never become the hit target.
        """

        if child_hit is not None:
            return child_hit

        opaque = self._hit_self_opaque() if self_opaque is None else self_opaque

        if opaque and self._in_local_bounds(x, y):
            return self
        return None

    def _hit_self_opaque(self) -> bool:
        """Resolve the ``auto`` policy for this widget's own surface (S axis).

        Returns ``True`` when this widget should catch a hit on its own rect.
        A widget catches when it is interactive (see :meth:`_hit_is_interactive`);
        widgets that also paint a visible surface (e.g. :class:`Box`) widen this.
        The bare widget paints only its children, so it defers by default.
        """

        return self._hit_is_interactive()

    def _hit_is_interactive(self) -> bool:
        """Whether this widget participates in pointer input (drives ``auto``).

        Overridden by :class:`InputHubMixin` to detect pointer/scroll handling.
        The bare kernel has no input surface, so it reports ``False``.
        """

        return False

    def _in_local_bounds(self, x: int, y: int) -> bool:
        """Whether the local point ``(x, y)`` lies within this widget's rect.

        ``x``/``y`` are in this widget's local coordinate space, so the rect is
        evaluated at the origin using the widget's own size.
        """

        my_rect = getattr(self, "layout_rect", None)
        if not my_rect:
            return False
        _, _, w, h = my_rect
        return 0 <= x < w and 0 <= y < h

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        """Render this widget; default implementation paints children."""
        if __debug__:
            assert_ui_thread()

        for child in getattr(self, "children", tuple()):
            child.paint(canvas, x, y, width, height)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return preferred (width, height) under optional max constraints.

        If a constraint is provided, implementations should treat it as an upper
        bound on the allocated size they will receive from the parent.
        """

        _ = (max_width, max_height)
        return (0, 0)

    # --- Layout cache helpers ---------------------------------------------
    def _notify_layout_param_changed(self) -> None:
        handler = getattr(self, "_invalidate_layout_cache", None)
        if callable(handler):
            try:
                handler()
            except Exception:
                exception_once(
                    _logger,
                    "widget_kernel_invalidate_layout_cache_exc",
                    "_invalidate_layout_cache raised",
                )
