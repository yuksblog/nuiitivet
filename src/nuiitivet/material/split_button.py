"""Material Design 3 Expressive SplitButton widget.

Provides a split button that combines a main action (leading button) with a
menu trigger (trailing button).  The two halves share an animated inner corner
junction that responds to hover and press interactions.  The trailing button's
expand/collapse icon rotates 180° when the menu is toggled open.

Component spec: https://m3.material.io/components/split-button/specs
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from nuiitivet.animation import Animatable
from nuiitivet.animation.converter import VectorConverter
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.motion import EXPRESSIVE_FAST_SPATIAL, EXPRESSIVE_DEFAULT_SPATIAL
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable import ObservableProtocol
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgeting.callbacks import invoke_event_handler, VoidCallback, BoolCallback
from nuiitivet.widgets.box import Box

if TYPE_CHECKING:
    from nuiitivet.material.styles.split_button_style import SplitButtonStyle
    from nuiitivet.material.symbols import Symbol
    from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal corner-tuple animation converter
# ---------------------------------------------------------------------------


class _CornerTupleConverter(VectorConverter[Tuple[float, float, float, float]]):
    """Animation vector converter for a 4-float corner-radius tuple."""

    def to_vector(self, v: Tuple[float, float, float, float]) -> List[float]:
        return [float(v[0]), float(v[1]), float(v[2]), float(v[3])]

    def from_vector(self, vector: List[float]) -> Tuple[float, float, float, float]:
        return (vector[0], vector[1], vector[2], vector[3])


_CORNER_CONVERTER = _CornerTupleConverter()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_LEADING_CORNERS_IDLE_BASE = ("outer", "inner", "inner", "outer")
"""Corner kinds for the leading button: (tl, tr, br, bl)."""

_TRAILING_CORNERS_IDLE_BASE = ("inner", "outer", "outer", "inner")
"""Corner kinds for the trailing button: (tl, tr, br, bl)."""


def _snap_anim(
    anim: "Animatable[Tuple[float, float, float, float]]",
    value: Tuple[float, float, float, float],
) -> None:
    """Immediately snap a corner-radius animation to ``value`` without motion."""
    anim.stop()
    anim._value.value = value  # type: ignore[attr-defined]
    anim._target = value  # type: ignore[attr-defined]
    if anim._state is not None:  # type: ignore[attr-defined]
        v = _CORNER_CONVERTER.to_vector(value)
        state = anim._state  # type: ignore[attr-defined]
        state.value = v.copy()
        state.start = v.copy()
        state.target = v.copy()


# ---------------------------------------------------------------------------
# _SplitLeadingButton
# ---------------------------------------------------------------------------


class _SplitLeadingButton(InteractiveWidget):
    """Leading (main action) half of a :class:`SplitButton`.

    Corners: ``(outer, inner, inner, outer)`` — fully-rounded left edges,
    inner-corner right edges adjacent to the trailing button.

    This class is private and should only be created by :class:`SplitButton`.
    """

    def __init__(
        self,
        child: "Widget",
        style: "SplitButtonStyle",
        on_click: Optional[VoidCallback] = None,
        disabled: "bool | ObservableProtocol[bool]" = False,
    ) -> None:
        """Initialize the leading button segment.

        Args:
            child: Content widget (label, icon, or combined Row).
            style: Shared :class:`SplitButtonStyle` instance.
            on_click: Callback invoked when the leading button is clicked.
            disabled: Whether the button is disabled.
        """
        self._style = style

        # Interaction state
        self._own_hovered: bool = False
        self._own_pressed: bool = False

        outer = style.outer_corner_radius
        inner = style.inner_corner_radius
        initial_corners: Tuple[float, float, float, float] = (outer, inner, inner, outer)

        self._corner_anim: "Animatable[Tuple[float, float, float, float]]" = Animatable.vector(
            initial_value=initial_corners,
            converter=_CORNER_CONVERTER,
            motion=None,
        )

        padding = (style.leading_leading_space, 0, style.leading_trailing_space, 0)

        super().__init__(
            child=child,
            on_click=on_click,
            on_press=self._handle_press_down,
            on_release=self._handle_press_up,
            disabled=disabled,
            height=style.container_height,
            padding=padding,
            background_color=style.background,
            border_color=style.border_color,
            border_width=style.border_width,
            corner_radius=initial_corners,
            state_layer_color=style.overlay_color or ColorRole.ON_SURFACE,
            on_hover=self._handle_hover_change,
        )
        self._HOVER_OPACITY = style.overlay_alpha * 2 / 3
        self._PRESS_OPACITY = style.overlay_alpha

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Subscribe to corner animation and enable expressive motion."""
        super().on_mount()
        self.bind(self._corner_anim.subscribe(self._on_corner_value_changed))
        outer = self._style.outer_corner_radius
        inner = self._style.inner_corner_radius
        idle: Tuple[float, float, float, float] = (outer, inner, inner, outer)
        _snap_anim(self._corner_anim, idle)
        self._corner_anim._motion = EXPRESSIVE_FAST_SPATIAL  # type: ignore[attr-defined]
        v0 = _CORNER_CONVERTER.to_vector(idle)
        self._corner_anim._state = EXPRESSIVE_FAST_SPATIAL.create_state(v0, v0)  # type: ignore[attr-defined]
        self.corner_radius = idle

    # ------------------------------------------------------------------
    # Interaction handlers
    # ------------------------------------------------------------------

    def _handle_hover_change(self, hovered: bool) -> None:
        """React to own hover state changes."""
        self._own_hovered = hovered
        self._update_corner_target()

    def _handle_press_down(self, event: PointerEvent) -> None:
        """Start press shape animation."""
        self._own_pressed = True
        self._update_corner_target()

    def _handle_press_up(self, event: PointerEvent) -> None:
        """Restore shape on release."""
        self._own_pressed = False
        self._update_corner_target()

    # ------------------------------------------------------------------
    # Corner animation helpers
    # ------------------------------------------------------------------

    def _update_corner_target(self) -> None:
        """Recompute and apply the corner animation target."""
        self._corner_anim.target = self._compute_target_corners()

    def _compute_target_corners(self) -> Tuple[float, float, float, float]:
        """Compute the (tl, tr, br, bl) corner-radius tuple for the current state.

        Returns:
            Target corner radii in logical pixels.
        """
        outer = self._style.outer_corner_radius
        inner = self._compute_active_inner_radius()
        return (outer, inner, inner, outer)

    def _compute_active_inner_radius(self) -> float:
        """Return the currently active inner corner radius.

        Priority: pressed > hovered > idle.

        Returns:
            Inner corner radius in logical pixels.
        """
        if self._own_pressed:
            return self._style.inner_corner_pressed_radius
        if self._own_hovered:
            return self._style.inner_corner_hovered_radius
        return self._style.inner_corner_radius

    def _on_corner_value_changed(self, v: Tuple[float, float, float, float]) -> None:
        """Animation tick: apply animated corners to the Box."""
        self.corner_radius = v
        self.invalidate()


# ---------------------------------------------------------------------------
# _SplitTrailingButton
# ---------------------------------------------------------------------------


class _SplitTrailingButton(InteractiveWidget):
    """Trailing (menu trigger) half of a :class:`SplitButton`.

    Corners: ``(inner, outer, outer, inner)`` — inner-corner left edges,
    fully-rounded right edges.  When *selected* (menu open) all corners
    become fully rounded.

    The expand/collapse icon rotates inwards 180° when selected.
    This class is private and should only be created by :class:`SplitButton`.
    """

    def __init__(
        self,
        style: "SplitButtonStyle",
        on_menu_toggle: Optional[BoolCallback] = None,
        menu_open: "bool | ObservableProtocol[bool]" = False,
        disabled: "bool | ObservableProtocol[bool]" = False,
    ) -> None:
        """Initialize the trailing button segment.

        Args:
            style: Shared :class:`SplitButtonStyle` instance.
            on_menu_toggle: Callback invoked with the new menu open state.
            menu_open: Initial menu open (selected) state, or an observable.
            disabled: Whether the button is disabled.
        """
        self._style = style
        self._on_menu_toggle = on_menu_toggle

        # Interaction state
        self._own_hovered: bool = False
        self._own_pressed: bool = False

        # Selected state (menu open)
        self._selected_external: "Optional[ObservableProtocol[bool]]" = None
        if hasattr(menu_open, "subscribe") and hasattr(menu_open, "value"):
            self._selected_external = menu_open  # type: ignore[assignment]
            ext_obs: "ObservableProtocol[bool]" = self._selected_external  # type: ignore[assignment]
            self._selected: bool = bool(ext_obs.value)
        else:
            self._selected = bool(menu_open)

        outer = style.outer_corner_radius
        inner = style.inner_corner_radius
        initial_corners: Tuple[float, float, float, float] = (inner, outer, outer, inner)

        self._corner_anim: "Animatable[Tuple[float, float, float, float]]" = Animatable.vector(
            initial_value=initial_corners,
            converter=_CORNER_CONVERTER,
            motion=None,
        )

        # Icon rotation animation: 0.0 (closed) → 180.0 (open).
        self._rotation_anim: "Animatable[float]" = Animatable(
            0.0 if not self._selected else 180.0,
        )

        content = self._build_content()

        padding = (style.trailing_leading_space, 0, style.trailing_trailing_space, 0)

        super().__init__(
            child=content,
            on_click=self._handle_click,
            on_press=self._handle_press_down,
            on_release=self._handle_press_up,
            disabled=disabled,
            height=style.container_height,
            padding=padding,
            background_color=style.background,
            border_color=style.border_color,
            border_width=style.border_width,
            corner_radius=initial_corners,
            state_layer_color=style.overlay_color or ColorRole.ON_SURFACE,
            on_hover=self._handle_hover_change,
        )
        self._HOVER_OPACITY = style.overlay_alpha * 2 / 3
        self._PRESS_OPACITY = style.overlay_alpha

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Subscribe to animations and external selected observable."""
        super().on_mount()
        self.bind(self._corner_anim.subscribe(self._on_corner_value_changed))
        self.bind(self._rotation_anim.subscribe(lambda _: self.invalidate()))

        idle = self._compute_target_corners()
        _snap_anim(self._corner_anim, idle)
        self._corner_anim._motion = EXPRESSIVE_FAST_SPATIAL  # type: ignore[attr-defined]
        v0 = _CORNER_CONVERTER.to_vector(idle)
        self._corner_anim._state = EXPRESSIVE_FAST_SPATIAL.create_state(v0, v0)  # type: ignore[attr-defined]
        self.corner_radius = idle

        # Arm rotation animation
        self._rotation_anim._motion = EXPRESSIVE_DEFAULT_SPATIAL  # type: ignore[attr-defined]
        rot_v = [self._rotation_anim.value]
        self._rotation_anim._state = EXPRESSIVE_DEFAULT_SPATIAL.create_state(rot_v, rot_v)  # type: ignore[attr-defined]

        # Subscribe to external menu_open observable
        if self._selected_external is not None:
            sub = self._selected_external.subscribe(lambda v: self._set_selected(bool(v)))
            self.bind(sub)

    # ------------------------------------------------------------------
    # Interaction handlers
    # ------------------------------------------------------------------

    def _handle_hover_change(self, hovered: bool) -> None:
        """React to own hover state changes."""
        self._own_hovered = hovered
        self._update_corner_target()

    def _handle_press_down(self, event: PointerEvent) -> None:
        """Start press animation."""
        self._own_pressed = True
        self._update_corner_target()

    def _handle_press_up(self, event: PointerEvent) -> None:
        """Restore shape on release."""
        self._own_pressed = False
        self._update_corner_target()

    def _handle_click(self) -> None:
        """Toggle menu open state and fire on_menu_toggle callback."""
        if self.disabled:
            return
        new_selected = not self._selected
        self._set_selected(new_selected)
        if self._on_menu_toggle is not None:
            invoke_event_handler(
                self._on_menu_toggle,
                new_selected,
                error_key="split_button_trailing_on_menu_toggle",
                error_msg="SplitButton on_menu_toggle raised",
                owner_name=type(self).__name__,
            )

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _set_selected(self, value: bool) -> None:
        """Update the selected (menu open) state and trigger animations.

        Args:
            value: New selected state.
        """
        self._selected = bool(value)

        # Write back to external observable if mutable
        ext = self._selected_external
        if ext is not None and hasattr(ext, "value"):
            from nuiitivet.observable import ReadOnlyObservableProtocol

            if not isinstance(ext, ReadOnlyObservableProtocol):
                try:
                    ext.value = bool(value)  # type: ignore[assignment]
                except AttributeError:
                    pass

        self.state.selected = bool(value)
        self._update_corner_target()
        # Animate icon rotation: 0° closed, 180° open.
        self._rotation_anim.target = 180.0 if self._selected else 0.0
        self.invalidate()

    # ------------------------------------------------------------------
    # Corner animation helpers
    # ------------------------------------------------------------------

    def _update_corner_target(self) -> None:
        """Recompute and apply the corner animation target."""
        self._corner_anim.target = self._compute_target_corners()

    def _compute_target_corners(self) -> Tuple[float, float, float, float]:
        """Compute the (tl, tr, br, bl) corner-radius tuple for the current state.

        When selected the trailing button becomes a fully-rounded pill
        (all corners = outer_corner_radius).

        Returns:
            Target corner radii in logical pixels.
        """
        outer = self._style.outer_corner_radius
        if self._selected:
            # Trailing button selected: inner corners become fully rounded (50%).
            return (outer, outer, outer, outer)
        inner = self._compute_active_inner_radius()
        return (inner, outer, outer, inner)

    def _compute_active_inner_radius(self) -> float:
        """Return the currently active inner corner radius.

        Priority: pressed > hovered > idle.

        Returns:
            Inner corner radius in logical pixels.
        """
        if self._own_pressed:
            return self._style.inner_corner_pressed_radius
        if self._own_hovered:
            return self._style.inner_corner_hovered_radius
        return self._style.inner_corner_radius

    def _on_corner_value_changed(self, v: Tuple[float, float, float, float]) -> None:
        """Animation tick: apply animated corners to the Box."""
        self.corner_radius = v
        self.invalidate()

    # ------------------------------------------------------------------
    # Paint: icon rotation
    # ------------------------------------------------------------------

    def draw_children(self, canvas: Any, x: int, y: int, width: int, height: int) -> None:
        """Draw children with icon rotation applied.

        Rotates the canvas around the button centre by the current
        rotation animation value.  The rotation is 0° when the menu is
        closed and 180° when the menu is open.

        Args:
            canvas: Skia canvas.
            x: Left edge in logical pixels.
            y: Top edge in logical pixels.
            width: Width in logical pixels.
            height: Height in logical pixels.
        """
        angle = self._rotation_anim.value
        if canvas is None:
            super().draw_children(canvas, x, y, width, height)
            return

        cx = x + width / 2.0
        cy = y + height / 2.0

        if abs(angle) < 0.01:
            super().draw_children(canvas, x, y, width, height)
            return

        try:
            canvas.save()
            canvas.translate(cx, cy)
            canvas.rotate(angle)
            canvas.translate(-cx, -cy)
            super().draw_children(canvas, x, y, width, height)
        finally:
            canvas.restore()

    # ------------------------------------------------------------------
    # Content builder
    # ------------------------------------------------------------------

    def _build_content(self) -> "Widget":
        """Build the trailing button's icon content.

        Returns:
            An :class:`Icon` widget for the expand/collapse indicator.
        """
        from nuiitivet.material.icon import Icon
        from nuiitivet.material.styles.icon_style import IconStyle

        fg = self._style.foreground or ColorRole.ON_SURFACE
        return Icon(
            "expand_more",
            size=self._style.trailing_icon_size,
            style=IconStyle(color=fg),
        )


# ---------------------------------------------------------------------------
# SplitButton
# ---------------------------------------------------------------------------


class SplitButton(Box):
    """Material Design 3 Expressive Split Button.

    Combines a leading button (main action) with a trailing button (menu
    trigger).  The two halves share an animated inner corner junction that
    morphs on hover and press.  The trailing button's icon rotates 180°
    when the menu is opened.

    Spec: https://m3.material.io/components/split-button/specs

    Example::

        SplitButton(
            "Start",
            icon="play_arrow",
            on_click=lambda: start_action(),
            on_menu_toggle=lambda open: handle_menu(open),
            style=SplitButtonStyle.filled("s"),
        )
    """

    def __init__(
        self,
        label: "str | Any | None" = None,
        icon: "Symbol | str | Any | None" = None,
        *,
        on_click: Optional[VoidCallback] = None,
        on_menu_toggle: Optional[BoolCallback] = None,
        menu_open: "bool | ObservableProtocol[bool]" = False,
        disabled: "bool | ObservableProtocol[bool]" = False,
        width: SizingLike = None,
        style: "Optional[SplitButtonStyle]" = None,
    ) -> None:
        """Initialize SplitButton.

        Args:
            label: Text label for the leading button.  Either ``label`` or
                ``icon`` (or both) must be provided.
            icon: Leading icon for the leading button.  Accepts a
                :class:`Symbol`, a symbol name string, or a
                :class:`ReadOnlyObservableProtocol`.
            on_click: Callback invoked when the leading button is clicked.
            on_menu_toggle: Callback invoked with the new ``bool`` menu open
                state when the trailing button is clicked.
            menu_open: Initial menu open (selected) state of the trailing
                button.  Pass an :class:`ObservableProtocol` to bind
                externally.
            disabled: Disables both button halves when ``True``.
            width: Optional width sizing for the overall widget.
            style: Visual style.  Defaults to ``SplitButtonStyle.filled("s")``.
        """
        if label is None and icon is None:
            raise ValueError("SplitButton requires at least one of label or icon")

        from nuiitivet.material.styles.split_button_style import SplitButtonStyle as _Style

        resolved_style: "SplitButtonStyle" = style or _Style.filled("s")

        leading_child = self._build_leading_content(label, icon, resolved_style)

        self._leading_btn = _SplitLeadingButton(
            child=leading_child,
            style=resolved_style,
            on_click=on_click,
            disabled=disabled,
        )
        self._trailing_btn = _SplitTrailingButton(
            style=resolved_style,
            on_menu_toggle=on_menu_toggle,
            menu_open=menu_open,
            disabled=disabled,
        )

        from nuiitivet.layout.row import Row

        row = Row(
            [self._leading_btn, self._trailing_btn],
            gap=resolved_style.between_space,
            cross_alignment="center",
        )

        super().__init__(child=row, width=width)

    # ------------------------------------------------------------------
    # Content builder (leading button)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_leading_content(
        label: Any,
        icon: Any,
        style: "SplitButtonStyle",
    ) -> "Widget":
        """Build the leading button content from label and/or icon.

        Args:
            label: Text label, or ``None``.
            icon: Icon symbol / name, or ``None``.
            style: Resolved :class:`SplitButtonStyle`.

        Returns:
            A widget representing the leading button content.
        """
        from nuiitivet.material.icon import Icon
        from nuiitivet.material.text import Text
        from nuiitivet.material.styles.icon_style import IconStyle
        from nuiitivet.material.styles.text_style import TextStyle
        from nuiitivet.layout.row import Row

        fg: ColorSpec = style.foreground or ColorRole.ON_SURFACE

        icon_w: Optional["Widget"] = None
        text_w: Optional["Widget"] = None

        if icon is not None:
            icon_w = Icon(icon, size=style.icon_size, style=IconStyle(color=fg))

        if label is not None:
            text_w = Text(
                label,
                style=TextStyle(color=fg, font_size=style.label_font_size, text_alignment="center"),
            )

        if icon_w is not None and text_w is None:
            return icon_w
        if text_w is not None and icon_w is None:
            return text_w
        assert icon_w is not None and text_w is not None
        return Row([icon_w, text_w], gap=8, cross_alignment="center")

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def menu_open(self) -> bool:
        """Whether the menu is currently open (trailing button selected).

        Returns:
            ``True`` when the menu is open.
        """
        return self._trailing_btn._selected


__all__ = ["SplitButton"]
