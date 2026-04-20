"""Material Design 3 ButtonGroup components.

This module provides:
- ``GroupButton``: A single interactive segment, shared by both group types.
- ``_ButtonGroupBase``: Internal base class with shared validation and mount logic.
- ``StandardButtonGroup``: Action-oriented group; adjacent shape animation ON.
- ``ConnectedButtonGroup``: Option-selector group; manages single / multi-select.
- ``ButtonGroupPosition``: Literal type for segment position within a group.
"""

from __future__ import annotations

import logging
from typing import (
    Callable,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TYPE_CHECKING,
    cast,
)

from nuiitivet.animation import Animatable
from nuiitivet.animation.converter import VectorConverter
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.motion import EXPRESSIVE_FAST_SPATIAL
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable import ObservableProtocol, ReadOnlyObservableProtocol
from nuiitivet.rendering.sizing import Sizing, SizingLike
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgets.box import Box

if TYPE_CHECKING:
    from nuiitivet.material.styles.button_group_style import (
        ButtonGroupStyle,
        ConnectedButtonGroupStyle,
        StandardButtonGroupStyle,
    )
    from nuiitivet.material.symbols import Symbol
    from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public type alias
# ---------------------------------------------------------------------------

ButtonGroupPosition = Literal["start", "middle", "end", "only"]
"""Position of a segment within a ButtonGroup."""

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Maps position → (tl_kind, tr_kind, br_kind, bl_kind)
# Tuple order follows Box.corner_radius convention: (tl, tr, br, bl).
# Each entry is either "outer" (group edge) or "inner" (junction).
_CORNER_KIND: dict[str, Tuple[str, str, str, str]] = {
    "start": ("outer", "inner", "inner", "outer"),
    "middle": ("inner", "inner", "inner", "inner"),
    "end": ("inner", "outer", "outer", "inner"),
    "only": ("outer", "outer", "outer", "outer"),
}


class _CornerTupleConverter(VectorConverter[Tuple[float, float, float, float]]):
    """Animation vector converter for a 4-float corner-radius tuple."""

    def to_vector(self, v: Tuple[float, float, float, float]) -> List[float]:
        return [float(v[0]), float(v[1]), float(v[2]), float(v[3])]

    def from_vector(self, vector: List[float]) -> Tuple[float, float, float, float]:
        return (vector[0], vector[1], vector[2], vector[3])


_CORNER_CONVERTER = _CornerTupleConverter()

# ---------------------------------------------------------------------------
# GroupButton
# ---------------------------------------------------------------------------


class GroupButton(InteractiveWidget):
    """A single interactive segment in a ButtonGroup (Standard or Connected).

    Handles position-aware corner-radius shape morphing via ``EXPRESSIVE_FAST_SPATIAL``
    motion on press / release.  ``set_position()`` is called exclusively by the
    containing ``_ButtonGroupBase`` during ``on_mount``; it is not part of the
    public user API.

    Args:
        label: Optional text label.  Can be a plain ``str`` or a
            ``ReadOnlyObservableProtocol[str]`` for dynamic text.
        icon: Optional icon.  Accepts a ``Symbol``, ``str`` icon name, or
            ``ReadOnlyObservableProtocol`` wrapping either.
        selected: Initial selected (toggle) state.  Pass an
            ``ObservableProtocol[bool]`` to bind to external state.
        on_change: Callback fired with the new ``bool`` selected state after each
            toggle.  In ``ConnectedButtonGroup`` this callback is composed with
            the group-level selection logic.
        disabled: Whether the item ignores pointer events.
        width: Optional width sizing.  ``ConnectedButtonGroup`` overrides this to
            ``Sizing.flex(1)`` to achieve equal-width segments.
        style: Optional style override.  If omitted the ``filled`` preset is used.
    """

    def __init__(
        self,
        label: "str | ReadOnlyObservableProtocol[str] | None" = None,
        icon: "Symbol | str | ReadOnlyObservableProtocol | None" = None,
        *,
        selected: "bool | ObservableProtocol[bool]" = False,
        on_change: Optional[Callable[[bool], None]] = None,
        disabled: "bool | ObservableProtocol[bool]" = False,
        width: SizingLike = None,
        style: "Optional[ButtonGroupStyle]" = None,
    ) -> None:
        """Initialize GroupButton.

        Args:
            label: Text label, or an observable string.
            icon: Icon symbol, string name, or observable icon.
            selected: Initial selected state, or an observable bool.
            on_change: Toggle-state change callback.
            disabled: Disable interaction.
            width: Width sizing spec.
            style: Visual style override.
        """
        from nuiitivet.material.styles.button_group_style import StandardButtonGroupStyle

        if label is None and icon is None:
            raise ValueError("GroupButton requires at least one of label or icon")

        self._has_user_style = style is not None
        self._style: "ButtonGroupStyle" = style or StandardButtonGroupStyle.filled()
        self._label = label
        self._icon = icon

        # on_change is interceptable by the containing group
        self._on_change: Optional[Callable[[bool], None]] = on_change

        # Selected state
        self._selected_external: "Optional[ObservableProtocol[bool]]" = None
        if hasattr(selected, "subscribe") and hasattr(selected, "value"):
            self._selected_external = cast("ObservableProtocol[bool]", selected)
            self._selected: bool = bool(self._selected_external.value)
        else:
            self._selected = bool(selected)

        # Corner animation state
        self._position: ButtonGroupPosition = "only"
        self._neighbors: Tuple[Optional["GroupButton"], Optional["GroupButton"]] = (None, None)
        self._adjacent_animation: bool = True
        self._persistent_selected_pressed_shape: bool = False
        self._connected_inner_press_only: bool = False
        self._own_pressed: bool = False
        self._left_neighbor_pressed: bool = False
        self._right_neighbor_pressed: bool = False

        # Store child widget refs for colour updates
        self._text_widget: "Optional[Widget]" = None
        self._icon_widget_ref: "Optional[Widget]" = None

        # Compute initial effective colours
        bg, fg, bc, bw = self._effective_colors()

        # Build content child (stores text/icon refs)
        content = self._build_content(fg)

        # Initialize corner animation (no motion yet; motion is enabled in
        # set_position() so the initial position snap is immediate)
        initial_corners = self._compute_raw_idle_corners(
            self._style.outer_corner_radius,
            self._style.outer_corner_radius,  # "only" position: all outer
        )
        self._corner_anim: "Animatable[Tuple[float, float, float, float]]" = Animatable.vector(
            initial_value=initial_corners,
            converter=_CORNER_CONVERTER,
            motion=None,  # Enabled after first set_position()
        )

        super().__init__(
            child=content,
            on_click=self._handle_click,
            on_press=self._handle_press_down,
            on_release=self._handle_press_up,
            disabled=disabled,
            width=width,
            height=self._style.container_height,
            padding=(12, 0, 12, 0),
            background_color=bg,
            border_color=bc,
            border_width=bw,
            corner_radius=initial_corners,
            state_layer_color=self._style.overlay_color or ColorRole.ON_SURFACE,
        )

        # Override state-layer opacities from style
        self._PRESS_OPACITY = self._style.overlay_alpha
        self._HOVER_OPACITY = self._style.overlay_alpha * 2 / 3

    # ------------------------------------------------------------------
    # Preferred size
    # ------------------------------------------------------------------

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return preferred size, enforcing ``min_item_width``.

        Args:
            max_width: Available width constraint.
            max_height: Available height constraint.

        Returns:
            ``(width, height)`` in pixels.
        """
        w, _h = super().preferred_size(max_width=max_width, max_height=max_height)
        return (max(w, self._style.min_item_width), self._style.container_height)

    # ------------------------------------------------------------------
    # Position injection (called by container on_mount)
    # ------------------------------------------------------------------

    def set_position(
        self,
        position: ButtonGroupPosition,
        neighbors: Tuple[Optional["GroupButton"], Optional["GroupButton"]],
        adjacent_animation: bool = True,
    ) -> None:
        """Configure this item's position within its group.

        Called exclusively by ``_ButtonGroupBase.on_mount()``.  Snaps the
        corner radius to the idle value for the given position without
        animation, then arms the ``EXPRESSIVE_FAST_SPATIAL`` motion for
        subsequent press interactions.

        Args:
            position: One of ``"start"``, ``"middle"``, ``"end"``, ``"only"``.
            neighbors: ``(left_neighbor, right_neighbor)``; either may be ``None``.
            adjacent_animation: ``True`` for Standard groups (neighbor corners
                respond); ``False`` for Connected groups.
        """
        self._position = position
        self._neighbors = neighbors
        self._adjacent_animation = adjacent_animation
        self._own_pressed = False
        self._left_neighbor_pressed = False
        self._right_neighbor_pressed = False

        idle = self._compute_target_corners(False, False, False)

        # Snap the animation to idle (no motion for position init)
        self._corner_anim.stop()
        # Directly set internal observable to avoid a spurious animation tick
        self._corner_anim._value.value = idle  # type: ignore[attr-defined]
        self._corner_anim._target = idle  # type: ignore[attr-defined]
        if self._corner_anim._state is not None:  # type: ignore[attr-defined]
            v = _CORNER_CONVERTER.to_vector(idle)
            state = self._corner_anim._state  # type: ignore[attr-defined]
            state.value = v.copy()
            state.start = v.copy()
            state.target = v.copy()

        # Enable expressive motion for future press interactions
        self._corner_anim._motion = EXPRESSIVE_FAST_SPATIAL  # type: ignore[attr-defined]
        v0 = _CORNER_CONVERTER.to_vector(idle)
        self._corner_anim._state = EXPRESSIVE_FAST_SPATIAL.create_state(v0, v0)  # type: ignore[attr-defined]

        # Apply immediately to Box's corner_radius (invalidates paint cache)
        self.corner_radius = idle

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Subscribe to corner animation and external selected observable."""
        super().on_mount()

        # Subscribe to corner animation ticks
        self.bind(self._corner_anim.subscribe(self._on_corner_value_changed))

        # Subscribe to external selected observable if provided
        if self._selected_external is not None:
            sub = self._selected_external.subscribe(lambda v: self._set_selected(bool(v)))
            self.bind(sub)

    # ------------------------------------------------------------------
    # Interaction handlers (pointer events)
    # ------------------------------------------------------------------

    def _handle_press_down(self, event: PointerEvent) -> None:
        """Start press shape animation and notify adjacent neighbors."""
        self._own_pressed = True
        self._update_corner_target()
        if self._adjacent_animation:
            left, right = self._neighbors
            if left is not None:
                left._on_neighbor_pressed("right", True)
            if right is not None:
                right._on_neighbor_pressed("left", True)

    def _handle_press_up(self, event: PointerEvent) -> None:
        """Restore shape animation on release and notify adjacent neighbors."""
        self._own_pressed = False
        self._update_corner_target()
        if self._adjacent_animation:
            left, right = self._neighbors
            if left is not None:
                left._on_neighbor_pressed("right", False)
            if right is not None:
                right._on_neighbor_pressed("left", False)

    def _on_neighbor_pressed(self, side: Literal["left", "right"], pressed: bool) -> None:
        """React to an adjacent item's press state change.

        Animates the junction corner facing the pressed neighbor.
        Called exclusively from pointer event handlers; never from ``paint()``.

        Args:
            side: Which side the pressed neighbor is on.
            pressed: ``True`` when the neighbor becomes pressed; ``False`` on release.
        """
        if side == "left":
            self._left_neighbor_pressed = pressed
        else:
            self._right_neighbor_pressed = pressed
        self._update_corner_target()

    def _handle_click(self) -> None:
        """Toggle selected state, fire change and click callbacks."""
        if self.disabled:
            return
        new_selected = not self._selected
        self._set_selected(new_selected)
        if self._on_change is not None:
            self._on_change(new_selected)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _set_selected(self, value: bool) -> None:
        """Update selected state and refresh visual colours.

        Does NOT call ``_on_change``; callers must do so explicitly when needed.

        Args:
            value: New selected state.
        """
        self._selected = bool(value)

        # Write back to external observable if mutable
        if self._selected_external is not None:
            ext = self._selected_external
            if hasattr(ext, "value") and not isinstance(ext, ReadOnlyObservableProtocol):
                try:
                    ext.value = bool(value)  # type: ignore[assignment]
                except AttributeError:
                    pass

        bg, fg, bc, _bw = self._effective_colors()
        self.bgcolor = bg
        self.border_color = bc
        self._apply_foreground(fg)
        self.state.selected = bool(value)
        self._update_corner_target()
        self.invalidate()

    # ------------------------------------------------------------------
    # Corner animation helpers
    # ------------------------------------------------------------------

    def _update_corner_target(self) -> None:
        """Recompute and apply the corner animation target."""
        left_p = self._left_neighbor_pressed if self._adjacent_animation else False
        right_p = self._right_neighbor_pressed if self._adjacent_animation else False
        target = self._compute_target_corners(self._own_pressed, left_p, right_p)
        self._corner_anim.target = target

    def _compute_target_corners(
        self,
        own_pressed: bool,
        left_neighbor_pressed: bool,
        right_neighbor_pressed: bool,
    ) -> Tuple[float, float, float, float]:
        """Compute the 4-corner radius tuple for the given interaction state.

        Corner-tuple order: ``(tl, tr, br, bl)``.

        Args:
            own_pressed: Whether this item is currently pressed.
            left_neighbor_pressed: Whether the left neighbor is pressed.
            right_neighbor_pressed: Whether the right neighbor is pressed.

        Returns:
            Target ``(tl, tr, br, bl)`` corner radii in logical pixels.
        """
        s = self._style
        kinds = _CORNER_KIND[self._position]  # (tl, tr, br, bl) kinds

        def resolve(kind: str, own: bool, neighbor: bool) -> float:
            if own:
                if self._connected_inner_press_only:
                    # Connected groups: keep outer corners stable while pressed.
                    # When selected, preserve fully rounded inner corners to avoid
                    # a temporary rectangular-looking intermediate shape.
                    if kind == "outer":
                        return s.outer_corner_radius
                    if self._selected:
                        sel = s.selected_inner_corner_radius
                        return sel if sel > 0 else s.outer_corner_radius
                    return s.pressed_inner_corner_radius
                return s.pressed_outer_corner_radius if kind == "outer" else s.pressed_inner_corner_radius
            if neighbor and kind == "inner":
                return s.pressed_inner_corner_radius
            # Standard groups: keep a squarer selected shape after release.
            if self._selected and self._persistent_selected_pressed_shape:
                return s.pressed_outer_corner_radius if kind == "outer" else s.pressed_inner_corner_radius
            # Selected inner corner: fully rounded on inner edges (Connected groups only).
            if kind == "inner" and self._selected and not self._adjacent_animation:
                sel = s.selected_inner_corner_radius
                return sel if sel > 0 else s.outer_corner_radius
            return s.outer_corner_radius if kind == "outer" else s.inner_corner_radius

        tl = resolve(kinds[0], own_pressed, left_neighbor_pressed)
        tr = resolve(kinds[1], own_pressed, right_neighbor_pressed)
        br = resolve(kinds[2], own_pressed, right_neighbor_pressed)
        bl = resolve(kinds[3], own_pressed, left_neighbor_pressed)
        return (tl, tr, br, bl)

    @staticmethod
    def _compute_raw_idle_corners(outer: float, inner: float) -> Tuple[float, float, float, float]:
        """Return idle corners for the ``"only"`` position (all outer).

        Args:
            outer: Outer corner radius.
            inner: Inner corner radius (unused for ``"only"``; kept for symmetry).

        Returns:
            ``(outer, outer, outer, outer)``
        """
        return (outer, outer, outer, outer)

    def _on_corner_value_changed(self, v: Tuple[float, float, float, float]) -> None:
        """Animation tick callback: apply animated corners to the Box."""
        # Use Box's setter so paint cache is invalidated with every shape update.
        self.corner_radius = v
        self.invalidate()

    # ------------------------------------------------------------------
    # Visual helpers
    # ------------------------------------------------------------------

    def _effective_colors(
        self,
    ) -> Tuple[Optional[ColorSpec], ColorSpec, Optional[ColorSpec], float]:
        """Return ``(background, foreground, border_color, border_width)`` for current state.

        Returns:
            Tuple of effective colour specs for the current selected state.
        """
        s = self._style
        if self._selected:
            bg: Optional[ColorSpec] = s.selected_background or s.background
            fg: ColorSpec = s.selected_foreground or s.foreground or ColorRole.ON_SURFACE
            bc: Optional[ColorSpec] = s.selected_border_color or s.border_color
        else:
            bg = s.background
            fg = s.foreground or ColorRole.ON_SURFACE
            bc = s.border_color
        return bg, fg, bc, s.border_width

    def _build_content(self, foreground: ColorSpec) -> "Widget":
        """Build the content child widget (icon + label composition).

        Stores references to the text and icon widgets for later colour updates.

        Args:
            foreground: Initial foreground colour for icon and text.

        Returns:
            A widget representing the item content.
        """
        from nuiitivet.material.icon import Icon
        from nuiitivet.material.text import Text
        from nuiitivet.material.styles.icon_style import IconStyle
        from nuiitivet.material.styles.text_style import TextStyle
        from nuiitivet.layout.row import Row

        icon_size = 20

        icon_w: "Optional[Widget]" = None
        text_w: "Optional[Widget]" = None

        if self._icon is not None:
            icon_w = Icon(self._icon, size=icon_size, style=IconStyle(color=foreground))
            self._icon_widget_ref = icon_w

        if self._label is not None:
            text_w = Text(
                self._label,
                style=TextStyle(color=foreground, font_size=14, text_alignment="center"),
            )
            self._text_widget = text_w

        if icon_w is not None and text_w is None:
            return icon_w
        if text_w is not None and icon_w is None:
            return text_w
        assert icon_w is not None and text_w is not None
        return Row([icon_w, text_w], gap=8, cross_alignment="center")

    def _apply_foreground(self, foreground: ColorSpec) -> None:
        """Update the colour of child text and icon widgets.

        Args:
            foreground: New foreground colour.
        """
        from nuiitivet.material.icon import Icon
        from nuiitivet.material.styles.icon_style import IconStyle
        from nuiitivet.material.styles.text_style import TextStyle

        if self._text_widget is not None:
            current = getattr(self._text_widget, "_style", None)
            if current is not None:
                self._text_widget._style = current.copy_with(color=foreground)  # type: ignore[attr-defined]
            else:
                self._text_widget._style = TextStyle(  # type: ignore[attr-defined]
                    color=foreground, font_size=14, text_alignment="center"
                )
            self._text_widget.invalidate()

        if self._icon_widget_ref is not None and isinstance(self._icon_widget_ref, Icon):
            current_icon = getattr(self._icon_widget_ref, "_style", None)
            if current_icon is not None:
                self._icon_widget_ref._style = current_icon.copy_with(color=foreground)
            else:
                self._icon_widget_ref._style = IconStyle(color=foreground)
            self._icon_widget_ref.invalidate()


# ---------------------------------------------------------------------------
# _ButtonGroupBase
# ---------------------------------------------------------------------------


class _ButtonGroupBase(Box):
    """Internal base for StandardButtonGroup and ConnectedButtonGroup.

    Validates items, builds the Row layout, and calls ``set_position()`` on
    each item during ``on_mount()``.
    """

    def __init__(
        self,
        items: Sequence[GroupButton],
        *,
        adjacent_animation: bool,
        persistent_selected_pressed_shape: bool,
        connected_inner_press_only: bool,
        group_width: SizingLike,
        style: "ButtonGroupStyle",
    ) -> None:
        """Initialize the shared button group layout.

        Args:
            items: Between 2 and 5 ``GroupButton`` instances.
            adjacent_animation: ``True`` to enable neighbor corner animation
                (Standard); ``False`` to disable it (Connected).
            persistent_selected_pressed_shape: ``True`` to keep a squarer
                shape on selected items after release (Standard groups).
            connected_inner_press_only: ``True`` to keep outer corners
                stable while pressed, animating only inner corners
                (Connected groups).
            group_width: Width sizing passed to the inner ``Row`` and outer
                ``Box``.  ``None`` for content-fit; ``"100%"`` for full-width.
            style: Resolved ``ButtonGroupStyle`` for this group.
        """
        _validate_items(items)

        self._items: List[GroupButton] = list(items)
        self._style = style
        self._adjacent_animation = adjacent_animation
        self._persistent_selected_pressed_shape = persistent_selected_pressed_shape
        self._connected_inner_press_only = connected_inner_press_only

        from nuiitivet.layout.row import Row

        row = Row(
            list(items),
            gap=style.item_gap,
            cross_alignment="center",
            width=group_width,
            height=style.container_height,
        )

        super().__init__(child=row, width=group_width)

    def _item_size_tokens(self) -> dict[str, int | float]:
        """Return size tokens to propagate to items with user-provided styles.

        Subclasses override to include only field names valid for their
        concrete style type (e.g. ``inner_corner_radius`` is a field only
        on ``ConnectedButtonGroupStyle``).
        """
        return {
            "container_height": self._style.container_height,
            "outer_corner_radius": self._style.outer_corner_radius,
            "pressed_inner_corner_radius": self._style.pressed_inner_corner_radius,
        }

    def on_mount(self) -> None:
        """Assign positions, sync size-layout tokens, and set neighbors for all items."""
        super().on_mount()
        n = len(self._items)
        _size_tokens = self._item_size_tokens()
        for i, item in enumerate(self._items):
            if n == 1:
                pos: ButtonGroupPosition = "only"
            elif i == 0:
                pos = "start"
            elif i == n - 1:
                pos = "end"
            else:
                pos = "middle"

            # Propagate group style to items.  Items without a user-provided
            # style inherit the full group style; items with a custom style
            # only receive size tokens so they keep their custom colours.
            if not item._has_user_style:
                item._style = self._style
            else:
                item._style = item._style.copy_with(**_size_tokens)
            item.height_sizing = Sizing.fixed(self._style.container_height)
            # Refresh visual properties that were baked in during __init__.
            bg, fg, bc, bw = item._effective_colors()
            item.bgcolor = bg
            item.border_color = bc
            item.border_width = bw
            item.state_layer_color = item._style.overlay_color or ColorRole.ON_SURFACE
            item._PRESS_OPACITY = item._style.overlay_alpha
            item._HOVER_OPACITY = item._style.overlay_alpha * 2 / 3
            item._apply_foreground(fg)
            item.mark_needs_layout()
            item._persistent_selected_pressed_shape = self._persistent_selected_pressed_shape
            item._connected_inner_press_only = self._connected_inner_press_only

            left = self._items[i - 1] if i > 0 else None
            right = self._items[i + 1] if i < n - 1 else None
            item.set_position(pos, (left, right), adjacent_animation=self._adjacent_animation)


def _validate_items(items: Sequence[object]) -> None:
    """Raise if items fail the ButtonGroup constraints.

    Args:
        items: Sequence to validate.

    Raises:
        ValueError: If the number of items is outside [2, 5].
        TypeError: If any element is not a ``GroupButton``.
    """
    if len(items) < 2:
        raise ValueError(f"ButtonGroup requires at least 2 items, got {len(items)}")
    if len(items) > 5:
        raise ValueError(f"ButtonGroup requires at most 5 items, got {len(items)}")
    for item in items:
        if not isinstance(item, GroupButton):
            raise TypeError(f"All items must be GroupButton instances, got {type(item).__name__}")


# ---------------------------------------------------------------------------
# StandardButtonGroup
# ---------------------------------------------------------------------------


class StandardButtonGroup(_ButtonGroupBase):
    """A ButtonGroup that organises action or toggle segments horizontally.

    Width fits the combined item widths.  Adjacent segments animate their
    junction corners in response to a neighbor's press (M3 Expressive motion).
    Item selected states are independent — no group-level enforcement.

    Args:
        items: Between 2 and 5 ``GroupButton`` instances.
        style: Visual style.  Use ``StandardButtonGroupStyle.filled()``,
            ``.tonal()``, or ``.outlined()``, optionally passing a size
            (e.g. ``StandardButtonGroupStyle.filled("m")``).
    """

    def __init__(
        self,
        items: Sequence[GroupButton],
        *,
        style: "Optional[StandardButtonGroupStyle]" = None,
    ) -> None:
        """Initialize StandardButtonGroup.

        Args:
            items: Between 2 and 5 ``GroupButton`` instances.
            style: Visual style override.  Defaults to
                ``StandardButtonGroupStyle.filled()`` (size ``"s"``).
        """
        from nuiitivet.material.styles.button_group_style import (
            StandardButtonGroupStyle as _Std,
        )

        eff_style = style if style is not None else _Std.filled()
        super().__init__(
            items,
            adjacent_animation=False,
            persistent_selected_pressed_shape=True,
            connected_inner_press_only=False,
            group_width=None,  # Fits content
            style=eff_style,
        )


# ---------------------------------------------------------------------------
# ConnectedButtonGroup
# ---------------------------------------------------------------------------


class ConnectedButtonGroup(_ButtonGroupBase):
    """A ButtonGroup that functions as an option selector / view switcher.

    Width expands to fill the containing widget (``width="100%"``).  Items
    share space equally (``Sizing.flex(1)``).  Only corner shapes animate on
    press — adjacent segment corners are unaffected.  Selection is always
    enforced by the group.

    Args:
        items: Between 2 and 5 ``GroupButton`` instances.
        select_mode: ``"single"`` ensures at most one item is selected;
            ``"multi"`` allows any combination.
        style: Visual style.  Use ``ConnectedButtonGroupStyle.filled()``,
            ``.tonal()``, or ``.outlined()``, optionally passing a size
            (e.g. ``ConnectedButtonGroupStyle.filled("m")``).
    """

    def __init__(
        self,
        items: Sequence[GroupButton],
        *,
        select_mode: Literal["single", "multi"] = "single",
        style: "Optional[ConnectedButtonGroupStyle]" = None,
    ) -> None:
        """Initialize ConnectedButtonGroup.

        Args:
            items: Between 2 and 5 ``GroupButton`` instances.
            select_mode: ``"single"`` or ``"multi"`` selection enforcement.
            style: Visual style override.  Defaults to
                ``ConnectedButtonGroupStyle.filled()`` (size ``"s"``).
        """
        from nuiitivet.material.styles.button_group_style import (
            ConnectedButtonGroupStyle as _Con,
        )

        eff_style = style if style is not None else _Con.filled()
        self._select_mode = select_mode

        super().__init__(
            items,
            adjacent_animation=False,
            persistent_selected_pressed_shape=False,
            connected_inner_press_only=True,
            group_width="100%",
            style=eff_style,
        )

    def _item_size_tokens(self) -> dict[str, int | float]:
        """Include ``inner_corner_radius`` (a real field on Connected style)."""
        tokens = super()._item_size_tokens()
        tokens["inner_corner_radius"] = self._style.inner_corner_radius
        return tokens

    def on_mount(self) -> None:
        """Assign positions, set flex widths, and wire group selection logic."""
        super().on_mount()  # Calls _ButtonGroupBase.on_mount → set_position()

        # Equal-width distribution for connected layout
        for item in self._items:
            item.width_sizing = Sizing.flex(1)
            item.mark_needs_layout()

        # Intercept each item's on_change to apply group selection logic
        for i, item in enumerate(self._items):
            original_on_change = item._on_change

            def _make_wrapper(
                item_idx: int,
                orig_cb: Optional[Callable[[bool], None]],
            ) -> Callable[[bool], None]:
                def _wrapper(selected: bool) -> None:
                    # 1. Item-level callback fires first
                    if orig_cb is not None:
                        orig_cb(selected)
                    # 2. Group selection logic
                    self._handle_group_selection_change(item_idx, selected)

                return _wrapper

            item._on_change = _make_wrapper(i, original_on_change)

    def _handle_group_selection_change(self, changed_idx: int, selected: bool) -> None:
        """Apply select_mode logic.

        Args:
            changed_idx: Index of the item whose state just changed.
            selected: New selected state of the changed item.
        """
        if self._select_mode == "single" and selected:
            for i, item in enumerate(self._items):
                if i != changed_idx and item._selected:
                    item._set_selected(False)


__all__ = [
    "GroupButton",
    "ButtonGroupPosition",
    "StandardButtonGroup",
    "ConnectedButtonGroup",
]
