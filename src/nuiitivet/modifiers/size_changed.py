"""on_size_changed() modifier - react to a widget's own measured size.

A widget's size is decided by its parent, so a component that must adapt to the
space it was given has no way to read that space from `build()`. This modifier
pushes the measurement back to the widget that carries it::

    Row([rail, card], width=Sizing.weight(1)).modifier(
        on_size_changed(lambda s: vm.apply_width(s.width))
    )

Like :func:`on_mount` / :func:`on_unmount` it does **not** wrap the target: the
callback is registered on the target itself and the same instance is returned,
so no extra node appears in the tree.

Reach for :class:`Geometry` instead when the measurer and the consumer are
different widgets - a descendant at arbitrary depth reading an ancestor's size,
without the widgets in between knowing about it.
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.widget_size_change import SizeCallback


@dataclass(slots=True)
class OnSizeChangedModifier(ModifierElement):
    """Modifier that reports the target widget's measured size to *callback*."""

    callback: SizeCallback

    def apply(self, widget: Widget) -> Widget:
        widget.add_size_callback(self.callback)
        return widget


def on_size_changed(callback: SizeCallback) -> OnSizeChangedModifier:
    """Return a modifier that calls *callback* with the widget's measured size.

    The callback receives a :class:`Size` - the widget's own ``(width, height)``
    after layout, excluding its position. Use it to feed a size into imperative
    state: a ViewModel, or a plain ``Observable`` a child widget binds to::

        class ResponsiveScaffold(ComposableWidget):
            def __init__(self) -> None:
                super().__init__()
                self.expanded = Observable(False)

            def _on_size(self, size: Size) -> None:
                self.expanded.value = size.width >= 700

            def build(self) -> Widget:
                rail = NavigationRail(..., expanded=self.expanded)
                return Row([rail, card], ...).modifier(on_size_changed(self._on_size))

    Args:
        callback: A callable taking a :class:`Size`, sync or async. An async
            callback is scheduled as a task. Exceptions are logged and contained.

    Returns:
        An :class:`OnSizeChangedModifier` to apply via ``widget.modifier(...)``.

    Note:
        **Fires once with the first measurement**, so the callback alone is
        enough to seed the state it drives. After that it fires only when the
        measured size actually changed; a widget that is re-laid-out at the same
        size, or merely moved, is silent.

    Note:
        **Dispatched between frames, never during layout**, so the callback may
        safely do anything - push a route, write an Observable, replace
        children - and its effect lands on the frame after the measurement.

        That includes the first call, which therefore arrives *after* the first
        paint. Give an Observable the value you expect at the initial size and
        the first report writes the same value, which de-dupes: no visible
        transition. Seed it differently and the widget animates once on startup.

    Warning:
        Avoid making the callback change the measured widget's *own* size: that
        feeds back into the next measurement and can oscillate. The structurally
        safe pattern is to measure a widget whose size the parent imposes
        (``Sizing.weight(...)`` / ``"wt"``) and let the callback change only what
        is *inside* it.
    """
    return OnSizeChangedModifier(callback=callback)


__all__ = [
    "OnSizeChangedModifier",
    "on_size_changed",
]
