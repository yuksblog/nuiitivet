"""context_menu() modifier – a menu opened at the pointer by secondary click."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

from nuiitivet.input.codes import BUTTON_RIGHT
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.layout.alignment import AlignmentLike
from nuiitivet.modifiers.popup import PopupBox
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.interaction import (
    InteractionHostMixin,
    PointerListenerNode,
    ensure_interaction_region,
)

if TYPE_CHECKING:
    from nuiitivet.navigation.transition_spec import TransitionSpec


class ContextMenuBox(PopupBox):
    """PopupBox variant that opens at the pointer instead of at the widget rect.

    A widget-anchored popup has a stable anchor, so :class:`PopupBox` resolves it
    from the anchor widget's layout rect. A context menu's anchor is the click
    point — transient, and different on every open — so this subclass overrides
    :meth:`_rect_provider` to report a zero-size rect at the most recent
    secondary-click position. Everything else (open/close lifecycle, overlay
    handle monitoring, unmount cleanup) is inherited unchanged.
    """

    def __init__(
        self,
        child: Widget,
        content: Widget,
        *,
        content_anchor: AlignmentLike = "top-left",
        offset: Tuple[float, float] = (0.0, 0.0),
        transition_spec: Optional["TransitionSpec"] = None,
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        """Initialize a context-menu wrapper around a widget.

        Args:
            child: Widget that responds to the secondary click.
            content: Menu widget shown at the pointer.
            content_anchor: Reference point on the menu placed at the click point.
            offset: Additional ``(dx, dy)`` offset in screen pixels.
            transition_spec: Optional overlay transition.
            width: Width sizing for this wrapper.
            height: Height sizing for this wrapper.
        """
        super().__init__(
            child,
            content,
            is_open=None,
            # A zero-size rect makes every target_anchor equivalent; the menu is
            # placed by content_anchor alone.
            target_anchor="top-left",
            content_anchor=content_anchor,
            offset=offset,
            transition_spec=transition_spec,
            # A menu blocks the UI behind it and closes on an outside tap.
            passthrough=False,
            dismiss_on_outside_tap=True,
            width=width,
            height=height,
        )
        self._point: Optional[Tuple[float, float]] = None
        self._listener_node: Optional[PointerListenerNode] = None
        self._install_interactions()

    # ------------------------------------------------------------------
    # Pointer wiring
    # ------------------------------------------------------------------

    def _install_interactions(self) -> None:
        if self._listener_node is not None:
            return
        if not isinstance(self._child, InteractionHostMixin):
            # ContextMenuModifier.apply() guarantees an InteractionHostMixin
            # child. This guard prevents wiring onto a detached wrapper.
            return
        # A dedicated node rather than reusing an existing PointerListenerNode:
        # reconfiguring one would clobber a user's own pointer_input() handlers,
        # and the region dispatches to every node it holds.
        node = PointerListenerNode(
            on_press=self._on_secondary_press,
            buttons=[BUTTON_RIGHT],
            capture=False,
        )
        self._child.add_node(node)
        self._listener_node = node

    def on_unmount(self) -> None:
        """Drop the pointer listener before the base class tears the popup down."""
        node = self._listener_node
        if node is not None:
            self._listener_node = None
            node.configure(on_press=None, buttons=[BUTTON_RIGHT], capture=False)
        super().on_unmount()

    def _on_secondary_press(self, event: PointerEvent) -> None:
        # The rect provider is consulted on every layout pass, so recording the
        # point is all that placement needs. Setting an already-True observable
        # is a no-op, which is the right behaviour: while the menu is open its
        # light-dismiss hit layer covers the widget, so this handler is not
        # reached again until the menu closes.
        self._point = (event.x, event.y)
        self._is_open.value = True

    # ------------------------------------------------------------------
    # Position
    # ------------------------------------------------------------------

    def _rect_provider(self) -> Optional[Tuple[int, int, int, int]]:
        """Return a zero-size rect at the last secondary-click point."""
        point = self._point
        if point is None:
            return None
        px, py = point
        return (int(round(px)), int(round(py)), 0, 0)


@dataclass(slots=True)
class ContextMenuModifier(ModifierElement):
    """Modifier that opens a menu at the pointer on secondary click."""

    content: Widget
    content_anchor: AlignmentLike = "top-left"
    offset: Tuple[float, float] = (0.0, 0.0)
    transition_spec: Optional["TransitionSpec"] = None

    def apply(self, widget: Widget) -> Widget:
        """Wrap *widget* in a :class:`ContextMenuBox`.

        Args:
            widget: The widget that should respond to the secondary click.

        Returns:
            A :class:`ContextMenuBox` wrapping *widget*.
        """
        host: Widget
        if isinstance(widget, InteractionHostMixin):
            host = widget
        else:
            host = ensure_interaction_region(widget)
        return ContextMenuBox(
            host,
            self.content,
            content_anchor=self.content_anchor,
            offset=self.offset,
            transition_spec=self.transition_spec,
            width=host.width_sizing,
            height=host.height_sizing,
        )


def context_menu(
    content: Widget,
    *,
    content_anchor: AlignmentLike = "top-left",
    offset: Tuple[float, float] = (0.0, 0.0),
    transition_spec: Optional["TransitionSpec"] = None,
) -> ContextMenuModifier:
    """Open *content* at the pointer when the widget is secondary-clicked.

    Unlike :func:`popup`, which anchors to the widget's
    rect and is driven by an external ``is_open``, a context menu is driven by
    the click itself: the modifier owns both the open state and the transient
    click coordinate, so neither appears in caller code. The menu closes on an
    outside tap.

    Args:
        content: Menu widget to display. Usually a ``Menu`` from
            ``nuiitivet.material``, but any widget is accepted.
        content_anchor: Reference point on the menu that lands on the click point
            (default ``"top-left"``, so the menu hangs down-right of the cursor).
        offset: Additional ``(dx, dy)`` offset in screen pixels.
        transition_spec: Passed to :meth:`Overlay.show` for
            enter/exit animation.

    Returns:
        A :class:`ContextMenuModifier` suitable for :meth:`Widget.modifier`.

    Example::

        image.modifier(
            context_menu(
                Menu(items=[MenuItem("Open"), MenuItem("Rename")]),
            )
        )

    Note:
        The menu is kept inside the viewport, so a click near the right or
        bottom edge pulls it back into view rather than clipping it.

        While the menu is open, its light-dismiss hit layer covers the widget and
        only the *primary* button dismisses it. A secondary click elsewhere is
        therefore swallowed rather than re-targeting the menu: close it with a
        left click first.
    """
    return ContextMenuModifier(
        content=content,
        content_anchor=content_anchor,
        offset=offset,
        transition_spec=transition_spec,
    )


__all__ = ["ContextMenuBox", "ContextMenuModifier", "context_menu"]
