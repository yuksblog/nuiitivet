"""The :class:`Geometry` widget: container-scoped measured size."""

from __future__ import annotations

from typing import Optional, Tuple, Type, TypeVar

from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.observable import Observable
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.widget_children import ChildContainerMixin

from .size import Size

GeometryT = TypeVar("GeometryT", bound="Geometry")


class Geometry(Widget):
    """Publishes this widget's own measured geometry to its subtree.

    ``Geometry`` wraps a single child and is transparent to layout: the child
    receives the same size this widget receives. After each layout pass it
    publishes its own resolved size as an ``Observable[Size]``, which descendants
    read via :meth:`Geometry.of`. Follow nuiitivet's reactivity rule: **bind the
    ``size`` Observable (mapped); do not read ``.value`` at build time** (that is
    a one-time snapshot). Map it into a value widget, or drive a ``Deck`` index
    for a structural switch::

        class Panel(ComposableWidget):
            def build(self) -> Widget:
                size = Geometry.of(self).size
                return Deck(
                    children=[_NarrowLayout(...), _WideLayout(...)],
                    index=size.map(lambda s: 1 if s.width >= 600 else 0),
                )

        Geometry(Panel())

    Because the nearest ancestor provider wins, wrapping a panel in ``Geometry``
    makes its descendants react to the *panel*, not the window: local reflow
    independent of window size falls out for free. The app installs a root
    ``Geometry`` provider at the window, so with no nearer ``Geometry`` a
    top-level read falls back to it and tracks the window size.

    The measured size is written during the layout phase, but nuiitivet flushes
    build (scope recomposition) *before* layout within a frame, so the write is
    naturally deferred to the next frame's build — never re-entrant mid-layout.
    """

    def __init__(
        self,
        child: Widget,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        """Wrap *child*, publishing this widget's measured size to its subtree.

        Args:
            child: The single child laid out at this widget's own size.
            width: Sizing for this widget (``None`` shrink-wraps the child;
                ``"100%"`` / ``Sizing.flex(...)`` fills the space the parent
                offers). Use a filling size to measure the space *available* to a
                content pane, not just the child's intrinsic size.
            height: Sizing for this widget; see ``width``.
        """
        super().__init__(width=width, height=height, max_children=1, overflow_policy="replace_last")
        # A single atomic Observable[Size]: width and height update together so
        # consumers never read a torn (new width, old height) pair. The
        # Observable de-dupes equal values, so an unchanged size performs no
        # write and triggers no dependent recomposition (the oscillation guard).
        self._size: Observable[Size] = Observable(Size(0, 0))
        self.add_child(child)

    def add_child(self, w: Widget) -> None:
        """Keep at most one child; bypass overrides like :class:`Container`."""
        ChildContainerMixin.add_child(self, w)

    @property
    def size(self) -> Observable[Size]:
        """This widget's resolved ``(width, height)``, updated after layout."""
        return self._size

    @classmethod
    def of(cls: Type[GeometryT], context: Widget) -> GeometryT:
        """Return the nearest ancestor :class:`Geometry` (nearest provider wins).

        Args:
            context: A widget in the subtree from which to search upward.

        Raises:
            RuntimeError: If no ``Geometry`` ancestor exists.
        """
        geometry = context.find_ancestor(cls)
        if geometry is None:
            raise RuntimeError("Geometry not found in ancestors")
        return geometry

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Report preferred size: own fixed sizing wins, else the child's.

        A ``flex`` / ``"100%"`` sizing is not fixed, so the child's intrinsic
        size is reported here and the parent's flex distribution then stretches
        this widget to fill — which is what lets a filling ``Geometry`` measure
        the space available to a content pane.
        """
        if self.children:
            child_w, child_h = measure_preferred_size(self.children[0], max_width=max_width, max_height=max_height)
        else:
            child_w, child_h = 0, 0
        w = int(self.width_sizing.value) if self.width_sizing.kind == "fixed" else int(child_w)
        h = int(self.height_sizing.value) if self.height_sizing.kind == "fixed" else int(child_h)
        return (w, h)

    def layout(self, width: int, height: int) -> None:
        """Lay the child out at this widget's own size, then publish that size."""
        super().layout(width, height)
        if self.children:
            child = self.children[0]
            child.layout(width, height)
            child.set_layout_rect(0, 0, width, height)
        # Publish the measured size. Equal values are de-duped by the Observable,
        # so a stable size does not re-fire and cannot drive an oscillation loop.
        self._size.value = Size(int(width), int(height))

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint the child at this widget's own rect (transparent to paint)."""
        self.set_last_rect(x, y, width, height)
        if not self.children:
            return
        child = self.children[0]
        if child.layout_rect is None:
            self.layout(width, height)
        child.set_last_rect(x, y, width, height)
        child.paint(canvas, x, y, width, height)


__all__ = ["Geometry"]
