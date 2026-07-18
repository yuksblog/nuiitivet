"""keyed() modifier - attach a stable identity to a widget.

A ``key`` is a stable, layout-independent identity for a widget -- the same
notion of identity :class:`~nuiitivet.layout.for_each.ForEach` already uses to
recycle children across a reorder. It is *reconciliation identity*, not a visual
or behavioral property, and it serves two dev-loop roles:

* **Action targeting** -- the dev bridge drives a widget by ``key`` instead of
  brittle pixel coordinates (#375): ``click(key="submit")``.
* **Hot-reload state restoration** -- ``key`` anchors an observable's snapshot
  across a structural edit (reorder / sibling insertion), where the position-
  based path would otherwise break (``docs/design/HOT_RELOAD.md`` §7.4).

Unlike most modifiers, ``keyed`` is *pure metadata*: it sets ``widget.key`` and
returns the **same** widget. It never wraps, so it does not add a node to the
tree -- which is required, since a wrapper node would shift the very snapshot
paths ``key`` exists to stabilize, and change the structural view the bridge
observes. Composable widgets that own state pass ``key=`` to their constructor
instead (``ComposableWidget(key=...)``); this modifier is the way to key an
already-built widget inline.

Usage::

    nv.Button("increment").modifier(keyed("increment-btn"))
    nv.TextField(label="Email").modifier(keyed("email"))

When combined with wrapping modifiers, apply ``keyed`` last so the key lands on
the outermost node::

    widget.modifier(clickable(on_click=...) | keyed("row"))
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget


@dataclass(slots=True)
class KeyedModifier(ModifierElement):
    """Modifier that stamps a stable ``key`` onto a widget without wrapping it."""

    key: str

    def apply(self, widget: Widget) -> Widget:
        # Pure metadata: mutate in place and return the same node. Never wrap --
        # a wrapper would change the tree shape and defeat the snapshot-path and
        # targeting stability this key is meant to provide.
        widget.key = str(self.key)
        return widget


def keyed(value: str) -> KeyedModifier:
    """Return a modifier that assigns the stable identity ``value`` to a widget.

    Args:
        value: The stable key (a "testID"): unique enough to disambiguate the
            widget among its realistic targets / siblings.

    Returns:
        A :class:`KeyedModifier` to apply via ``widget.modifier(...)``.
    """
    return KeyedModifier(key=value)


__all__ = [
    "KeyedModifier",
    "keyed",
]
