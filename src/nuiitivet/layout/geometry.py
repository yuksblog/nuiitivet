"""The :class:`Geometry` widget: container-scoped measured size."""

from __future__ import annotations

from typing import Optional, Tuple, Type, TypeVar

from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.observable import Observable
from nuiitivet.rendering.size import Size
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.context_lookup import find_provider, raise_if_premature_lookup
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.widget_children import ChildContainerMixin
from nuiitivet.widgeting.widget_size_change import queue_size_change

GeometryT = TypeVar("GeometryT", bound="Geometry")


class Geometry(Widget):
    """Publishes this widget's own measured geometry to its subtree.

    Transparent to layout: the single child receives this widget's own size.
    Each layout pass publishes that size as an ``Observable[Size]``, read by
    descendants via :meth:`Geometry.of` — bind it (mapped); a ``.value`` read at
    build time is a one-time snapshot. Map it into a value widget, or drive a
    ``Deck`` index for a structural switch::

        class Panel(ComposableWidget):
            def build(self) -> Widget:
                size = Geometry.of(self).size
                return Deck(
                    children=[_NarrowLayout(...), _WideLayout(...)],
                    index=size.map(lambda s: 1 if s.width >= 600 else 0),
                )

        Geometry(Panel())

    The nearest ancestor provider wins, so wrapping a panel makes descendants
    react to the panel, not the window; with no nearer provider, reads fall back
    to the root ``Geometry`` the app installs at the window and track the window
    size. The size is measured during layout and published between frames:
    consumers see it one frame later, never a torn mix of old and new.
    """

    def __init__(
        self,
        child: Widget,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        key: Optional[str] = None,
    ) -> None:
        """Wrap *child*, publishing this widget's measured size to its subtree.

        Args:
            child: The single child laid out at this widget's own size.
            width: Sizing for this widget (``None`` shrink-wraps the child;
                ``"wt"`` / ``Sizing.weight(...)`` fills the space the parent
                offers). Use a filling size to measure the space *available* to a
                content pane, not just the child's intrinsic size.
            height: Sizing for this widget; see ``width``.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(width=width, height=height, max_children=1, overflow_policy="replace_last", key=key)
        # A single atomic Observable[Size]: width and height update together so
        # consumers never read a torn (new width, old height) pair. The
        # Observable de-dupes equal values, so an unchanged size performs no
        # write and triggers no dependent recomposition (the oscillation guard).
        self._size: Observable[Size] = Observable(Size(0, 0))
        self.add_size_callback(self._publish_size)
        self.add_child(child)

    def _publish_size(self, size: Size) -> None:
        self._size.value = size

    def add_child(self, w: Widget) -> None:
        """Keep at most one child; bypass overrides like :class:`Container`."""
        ChildContainerMixin.add_child(self, w)

    @property
    def size(self) -> Observable[Size]:
        """This widget's resolved ``(width, height)``, published between frames."""
        return self._size

    @classmethod
    def of(cls: Type[GeometryT], context: Widget) -> GeometryT:
        """Return the nearest ancestor :class:`Geometry` (nearest provider wins).

        Args:
            context: A widget in the subtree from which to search upward.

        Raises:
            RuntimeError: If called before ``context`` is mounted (typically from
                ``__init__``), or if no ``Geometry`` ancestor exists.
        """
        geometry = find_provider(context, cls)
        if geometry is None:
            raise_if_premature_lookup(f"{cls.__name__}.of", context)
            raise RuntimeError("Geometry not found in ancestors")
        return geometry

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Report preferred size: own fixed sizing wins, else the child's.

        A ``weight`` / ``"wt"`` sizing is not fixed, so the child's intrinsic
        size is reported here and the parent's weight distribution then stretches
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
        """Lay the child out at this widget's own size, then queue its publish."""
        super().layout(width, height)
        if self.children:
            child = self.children[0]
            child.layout(width, height)
            child.set_layout_rect(0, 0, width, height)
        # Queue, don't write: an Observable write here would propagate to
        # consumers mid-pass. The queue delivers the final measurement to
        # _publish_size between frames, de-duped against the last report.
        queue_size_change(self, Size(int(width), int(height)))

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
