from __future__ import annotations

from typing import Any, Callable, Optional, Sequence, Tuple, Union, cast
import logging

from nuiitivet.widgeting.widget import Widget
from nuiitivet.common.logging_once import exception_once, warning_once
from nuiitivet.rendering.sizing import SizingLike, Sizing, parse_sizing
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.observable.protocols import MutableObservableBase, ObservableBase, ReadOnlyObservableProtocol
from nuiitivet.animation import Animatable, Rect, lerp, lerp_rect
from nuiitivet.material.text import Text, LabelLike
from nuiitivet.material.icon import Icon, IconLike
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import (
    FocusNode,
    FocusNodePolicy,
    FocusScope,
    InteractionHostMixin,
    InteractionState,
)
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.styles.navigation_rail_style import NavigationRailStyle
from nuiitivet.material.styles.icon_style import IconStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.theme.type_scale import TypeScale
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.rendering.skia import make_paint, make_rect, draw_round_rect
from nuiitivet.theme.types import ColorSpec
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.material.badge import LargeBadge, SmallBadge
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_SPATIAL, EXPRESSIVE_DEFAULT_EFFECTS
from nuiitivet.modifiers.transform import rotate

logger = logging.getLogger(__name__)


def _reject_readonly_observable(value: Any, param: str) -> None:
    """Guard a two-way input against a read-only observable.

    ``index`` and ``expanded`` are two-way: the rail writes back to them on user
    interaction (item selection, the menu toggle). A read-only/computed
    observable (e.g. from ``.map(...)``) cannot be written back, so it is
    rejected up front rather than silently mishandled. Mirror the derived value
    into a plain ``Observable`` and pass that instead.
    """

    if isinstance(value, ObservableBase) and not isinstance(value, MutableObservableBase):
        raise TypeError(
            f"NavigationRail.{param} is two-way (the rail writes back to it on user "
            f"interaction), so it needs a mutable Observable; a read-only/computed "
            f"observable cannot be used. Mirror it into an Observable and update that."
        )


def _resolve_expanded_width(
    width: Union[SizingLike, ReadOnlyObservableProtocol, None],
    style: NavigationRailStyle,
) -> Tuple[float, Optional[Tuple[str, str]]]:
    """Resolve the effective expanded rail width from the ``width`` argument.

    Only a *fixed* width is interpreted as the expanded width (clamped into the
    MD3 range ``[min, max]``). ``None`` silently falls back to the minimum
    expanded width. Any other value (weight/auto/observable) cannot be
    interpreted as an expanded width, so the minimum is used and a warning is
    returned so the caller can surface it.

    Returns ``(effective_width, warning)`` where ``warning`` is either ``None``
    or a ``(log_once_key, message)`` pair for :func:`warning_once`.
    """
    lo = style.container_width_expanded_min
    hi = style.container_width_expanded_max
    if width is None:
        # No width provided: default to the minimum expanded width, silently.
        return style.clamp_expanded_width(lo), None
    if isinstance(width, (Sizing, int, float, str)):
        sizing = parse_sizing(width)
        if sizing.kind == "fixed":
            requested = float(sizing.value)
            effective = style.clamp_expanded_width(requested)
            if effective != requested:
                return effective, (
                    f"navigation_rail_width_clamped:{requested:g}:{lo:g}:{hi:g}",
                    f"NavigationRail width {requested:g}dp is outside the MD3 "
                    f"expanded range [{lo:g}, {hi:g}]; clamped to {effective:g}dp. "
                    f"Raise NavigationRailStyle.container_width_expanded_max to "
                    f"allow wider rails.",
                )
            return effective, None
        # A non-fixed sizing (weight/auto) cannot be an expanded width.
        return style.clamp_expanded_width(lo), (
            f"navigation_rail_width_non_fixed:{sizing.kind}",
            f"NavigationRail width is not a fixed size ({sizing.kind}); the "
            f"expanded width defaulted to {lo:g}dp. Pass a fixed width "
            f"(e.g. width=280) to set the expanded width.",
        )
    # Observable or otherwise non-interpretable width.
    return style.clamp_expanded_width(lo), (
        "navigation_rail_width_observable",
        "NavigationRail width must be a fixed size to set the expanded width; "
        f"the expanded width defaulted to {lo:g}dp.",
    )


class RailItem(Widget):
    """Navigation rail destination item.

    A widget representing a single destination in NavigationRail.
    Displays an icon and optional label (when rail is expanded).
    """

    def __init__(
        self,
        icon: IconLike,
        label: LabelLike,
        *,
        small_badge: Optional[ReadOnlyObservableProtocol[bool]] = None,
        large_badge: Optional[ReadOnlyObservableProtocol[Optional[str]]] = None,
        style: Optional[NavigationRailStyle] = None,
        key: Optional[str] = None,
    ) -> None:
        """Initialize RailItem.

        Args:
            icon: The icon to display. May be a :class:`Symbol`, a ligature
                string, or an observable of either (mirroring ``IconButton``).
            label: The label to display. May be a string or an observable string.
            small_badge: Optional Observable controlling small dot badge visibility.
            large_badge: Optional Observable with badge text. ``None`` or ``""`` hides the badge.
                When both ``small_badge`` and ``large_badge`` are provided,
                ``large_badge`` takes precedence.
            style: Optional style override for this item.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(key=key)

        self.icon_spec = icon
        self.label_spec = label
        self._small_badge_observable: Optional[ReadOnlyObservableProtocol[bool]] = small_badge
        self._large_badge_observable: Optional[ReadOnlyObservableProtocol[Optional[str]]] = large_badge
        self._style = style

        self._icon_widget: Widget
        self._label_widget: Widget

        eff_style = style or NavigationRailStyle()
        icon_color = eff_style.icon_color or ColorRole.ON_SURFACE
        icon_size = eff_style.icon_size
        self._icon_widget = Icon(icon, size=icon_size, style=IconStyle(color=icon_color))

        label_color = eff_style.label_color or ColorRole.ON_SURFACE_VARIANT
        if eff_style.label_text_style is not None:
            text_style = eff_style.label_text_style.copy_with(color=label_color)
        else:
            text_style = TextStyle(color=label_color)

        self._label_widget = Text(
            label,
            style=text_style,
            type_scale=TypeScale.LABEL_MEDIUM,
            alignment="center",
            width=Sizing.fixed(eff_style.container_width_collapsed),
            max_lines=1,
            overflow="ellipsis",
            soft_wrap=False,
        )

    @property
    def style(self) -> Optional[NavigationRailStyle]:
        """Get the style override."""
        return self._style

    @property
    def icon_widget(self) -> Widget:
        """Get the icon widget."""
        return self._icon_widget

    @property
    def label_widget(self) -> Widget:
        """Get the label widget."""
        return self._label_widget

    @property
    def small_badge_observable(self) -> Optional[ReadOnlyObservableProtocol[bool]]:
        """Get the optional small badge observable."""
        return self._small_badge_observable

    @property
    def large_badge_observable(self) -> Optional[ReadOnlyObservableProtocol[Optional[str]]]:
        """Get the optional large badge observable."""
        return self._large_badge_observable


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class _RailItemButton(InteractiveWidget):
    """Internal button widget for NavigationRail items."""

    def __init__(
        self,
        rail_item: RailItem,
        selected: bool,
        expand_animation: Animatable,
        label_animation: Animatable,
        rail_style: Optional[NavigationRailStyle] = None,
        expanded_width: float = NavigationRailStyle().container_width_expanded_min,
        on_click: Optional[Callable[[], None]] = None,
    ) -> None:
        self._expand_animation = expand_animation
        self._label_animation = label_animation
        # Resolve effective style: item style > rail style > defaults
        eff_style = rail_item.style or rail_style or NavigationRailStyle()
        self._eff_style = eff_style
        # Effective expanded rail width used to size the pill and label.
        self._expanded_width = expanded_width
        self._selected = bool(selected)
        self._indicator_color: Optional[ColorSpec] = None
        self._indicator_rect: Optional[Tuple[int, int, int, int]] = None
        self._indicator_radius: float = 0.0

        # Core widgets
        self._icon_widget = rail_item.icon_widget

        base_label_style = eff_style.label_text_style or TextStyle(
            color=ColorRole.ON_SURFACE_VARIANT,
        )

        # Inset the collapsed label so long labels never touch the rail edges.
        # 96dp rail - 2 * 8dp = 80dp label box (M3 collapsed container width).
        collapsed_label_width = max(
            0.0,
            eff_style.container_width_collapsed - 2.0 * eff_style.label_horizontal_inset,
        )
        # Expanded label width scales with the container so it fills the pill at
        # any container width in the M3 expanded range (220-360dp).
        expanded_label_width = eff_style.expanded_label_width(expanded_width)

        self._vertical_label = Text(
            rail_item.label_spec,
            style=base_label_style,
            type_scale=TypeScale.LABEL_MEDIUM,
            alignment="center",
            width=Sizing.fixed(collapsed_label_width),
            max_lines=1,
            overflow="ellipsis",
            # Single-line label: fill the width and truncate mid-word instead of
            # word-wrapping (which would drop everything after the first word).
            soft_wrap=False,
        )
        self._horizontal_label = Text(
            rail_item.label_spec,
            style=base_label_style,
            type_scale=TypeScale.LABEL_LARGE,
            alignment="start",
            width=Sizing.fixed(expanded_label_width),
            max_lines=1,
            overflow="ellipsis",
            soft_wrap=False,
        )

        # Fixed content size with animated clip window.
        # Inset content box (centered in the full-width container below), which
        # keeps the 8dp margin on each side while the outer container stays at
        # the full rail width for layout/animation.
        self._vertical_content = Box(
            child=self._vertical_label,
            width=Sizing.fixed(collapsed_label_width),
            height=Sizing.fixed(eff_style.label_height),
            alignment="center",
        )
        self._vertical_label_container = Box(
            child=self._vertical_content,
            width=Sizing.fixed(eff_style.container_width_collapsed),
            height=Sizing.fixed(eff_style.label_height),
            alignment="top-center",
        )
        self._vertical_label_container.clip_content = True

        self._horizontal_content = Box(
            child=self._horizontal_label,
            width=Sizing.fixed(expanded_label_width),
            height=Sizing.fixed(eff_style.label_height),
            alignment="center-left",
        )
        self._horizontal_label_container = Box(
            child=self._horizontal_content,
            width=Sizing.fixed(expanded_label_width),
            height=Sizing.fixed(eff_style.label_height),
            alignment="center-left",
        )
        self._horizontal_label_container.clip_content = True

        # Badge state
        self._badge_widget: Optional[Widget] = None
        self._badge_rect: Optional[Tuple[int, int, int, int]] = None
        self._small_badge_value: bool = False
        self._large_badge_value: Optional[str] = None
        self._small_badge_subscription = None
        self._large_badge_subscription = None

        # The item can hold the focus, but the rail is the Tab stop: its
        # FocusScope hands the focus to an item and the arrow keys rove it.
        super().__init__(
            child=None,
            on_click=on_click,
            width=Sizing.weight(1),
            height=Sizing.fixed(eff_style.item_height),
            padding=0,
            focusable=True,
            traversable=False,
        )

        # Add children manually; draw_children is overridden.
        self.add_child(self._icon_widget)
        self.add_child(self._horizontal_label_container)
        self.add_child(self._vertical_label_container)

        self._apply_colors(selected=self._selected, rail_style=rail_style)

        # Sync interaction state
        self.state.selected = selected

        # Subscribe to badge observables if provided.
        small_badge_obs = rail_item.small_badge_observable
        large_badge_obs = rail_item.large_badge_observable
        if small_badge_obs is not None:
            self._small_badge_value = small_badge_obs.value
            self._small_badge_subscription = small_badge_obs.subscribe(self._on_small_badge_changed)
        if large_badge_obs is not None:
            self._large_badge_value = large_badge_obs.value
            self._large_badge_subscription = large_badge_obs.subscribe(self._on_large_badge_changed)
        self._refresh_badge_widget()

        self.on_dispose(self._dispose_badge)

    # Bindings are automatically disposed by BindingHostMixin/observe.

    def _dispose_badge(self) -> None:
        if self._small_badge_subscription is not None:
            self._small_badge_subscription.dispose()
            self._small_badge_subscription = None
        if self._large_badge_subscription is not None:
            self._large_badge_subscription.dispose()
            self._large_badge_subscription = None

    def _on_small_badge_changed(self, value: bool) -> None:
        """React to small_badge observable changes."""
        self._small_badge_value = value
        self._refresh_badge_widget()
        self.mark_needs_layout()
        self.invalidate()

    def _on_large_badge_changed(self, value: Optional[str]) -> None:
        """React to large_badge observable changes."""
        self._large_badge_value = value
        self._refresh_badge_widget()
        self.mark_needs_layout()
        self.invalidate()

    def _refresh_badge_widget(self) -> None:
        """Compute current badge widget. large_badge takes precedence over small_badge."""
        if self._large_badge_value:
            self._badge_widget = LargeBadge(self._large_badge_value)
        elif self._small_badge_value:
            self._badge_widget = SmallBadge()
        else:
            self._badge_widget = None
        self._badge_rect = None

        # The badge is drawn by this widget rather than added as a child, so it
        # never gets mounted; give it the upward link itself, which is all
        # Theme.of() needs to reach the AppScope and resolve ColorRole.ERROR.
        # Nothing further is required: the badge's paint-time read registers it
        # as a theme reader on its own.
        if self._badge_widget is not None:
            self._badge_widget._parent = self

    def _apply_colors(self, *, selected: bool, rail_style: Optional[NavigationRailStyle] = None) -> None:
        eff_style = self._eff_style or rail_style or NavigationRailStyle()
        if selected:
            icon_color = eff_style.selected_icon_color or ColorRole.ON_SECONDARY_CONTAINER
            label_color = eff_style.selected_label_color or ColorRole.ON_SURFACE
            indicator_color = eff_style.indicator_color or ColorRole.SECONDARY_CONTAINER
        else:
            icon_color = eff_style.icon_color or ColorRole.ON_SURFACE_VARIANT
            label_color = eff_style.label_color or ColorRole.ON_SURFACE_VARIANT
            indicator_color = None

        if isinstance(self._icon_widget, Icon):
            self._icon_widget._style = IconStyle(color=icon_color)
            self._icon_widget.invalidate()

        if isinstance(self._vertical_label, Text):
            current_style = getattr(self._vertical_label, "_style", None) or TextStyle()
            self._vertical_label._style = current_style.copy_with(color=label_color)
            self._vertical_label.invalidate()

        if isinstance(self._horizontal_label, Text):
            current_style = getattr(self._horizontal_label, "_style", None) or TextStyle()
            self._horizontal_label._style = current_style.copy_with(color=label_color)
            self._horizontal_label.invalidate()

        self._indicator_color = indicator_color

    def set_selected(self, selected: bool, rail_style: Optional[NavigationRailStyle] = None) -> None:
        self._selected = bool(selected)
        self._apply_colors(selected=self._selected, rail_style=rail_style)
        self.state.selected = bool(selected)
        self.invalidate()

    def layout(self, width: int, height: int) -> None:
        Widget.layout(self, width, height)

        t_layout = _clamp01(self._expand_animation.value)
        t_label = _clamp01(self._label_animation.value)

        collapsed_width = float(self._eff_style.container_width_collapsed)
        margin = max(0.0, (collapsed_width - self._eff_style.indicator_width_collapsed) / 2.0)

        gap_collapsed = float(self._eff_style.gap_collapsed)
        gap_expanded = float(self._eff_style.gap_expanded)

        # Indicator rect interpolation
        indicator_rect = lerp_rect(
            Rect(
                x=margin,
                y=0.0,
                width=float(self._eff_style.indicator_width_collapsed),
                height=float(self._eff_style.indicator_height_collapsed),
            ),
            Rect(
                x=margin,
                y=0.0,
                width=self._eff_style.expanded_indicator_width(self._expanded_width),
                height=float(self._eff_style.item_height),
            ),
            t_layout,
        )
        ind_x_i, ind_y_i, ind_w_i, ind_h_i = indicator_rect.to_int_tuple()

        self._indicator_rect = (ind_x_i, ind_y_i, ind_w_i, ind_h_i)
        self._indicator_radius = float(ind_h_i) / 2.0

        # Icon rect interpolation
        icon_size = float(self._eff_style.icon_size)
        icon_x = margin + float(self._eff_style.indicator_horizontal_padding)
        icon_rect = lerp_rect(
            Rect(
                x=icon_x,
                y=(float(self._eff_style.indicator_height_collapsed) - icon_size) / 2.0,
                width=icon_size,
                height=icon_size,
            ),
            Rect(
                x=icon_x,
                y=(float(self._eff_style.item_height) - icon_size) / 2.0,
                width=icon_size,
                height=icon_size,
            ),
            t_layout,
        )
        icon_rect_i = icon_rect.to_int_tuple()
        self._icon_widget.layout(icon_rect_i[2], icon_rect_i[3])
        self._icon_widget.set_layout_rect(icon_rect_i[0], icon_rect_i[1], icon_rect_i[2], icon_rect_i[3])

        # Badge layout: compute and store badge rect relative to this item.
        self._place_badge()

        # Horizontal label window rect interpolation
        label_x_collapsed = icon_x + icon_size + gap_collapsed
        label_x_expanded = icon_x + icon_size + float(self._eff_style.label_gap_expanded)
        label_height = float(self._eff_style.label_height)
        label_y_collapsed = (float(self._eff_style.indicator_height_collapsed) - label_height) / 2.0
        label_y_expanded = (float(self._eff_style.item_height) - label_height) / 2.0

        label_rect = lerp_rect(
            Rect(x=label_x_collapsed, y=label_y_collapsed, width=0.0, height=label_height),
            Rect(
                x=label_x_expanded,
                y=label_y_expanded,
                width=self._eff_style.expanded_label_width(self._expanded_width),
                height=label_height,
            ),
            t_label,
        )
        label_rect_i = label_rect.to_int_tuple()
        self._horizontal_label_container.layout(label_rect_i[2], label_rect_i[3])
        self._horizontal_label_container.set_layout_rect(
            label_rect_i[0], label_rect_i[1], label_rect_i[2], label_rect_i[3]
        )

        # Vertical label window rect interpolation
        vertical_y_collapsed = float(self._eff_style.indicator_height_collapsed) + gap_collapsed
        vertical_y_expanded = float(self._eff_style.item_height) + gap_expanded
        vertical_rect = lerp_rect(
            Rect(x=0.0, y=vertical_y_collapsed, width=collapsed_width, height=label_height),
            Rect(x=0.0, y=vertical_y_expanded, width=collapsed_width, height=0.0),
            t_label,
        )
        vertical_rect_i = vertical_rect.to_int_tuple()
        self._vertical_label_container.layout(vertical_rect_i[2], vertical_rect_i[3])
        self._vertical_label_container.set_layout_rect(
            vertical_rect_i[0],
            vertical_rect_i[1],
            vertical_rect_i[2],
            vertical_rect_i[3],
        )

    def _place_badge(self) -> None:
        """Compute and cache badge rect from the current icon rect."""
        if self._badge_widget is None:
            self._badge_rect = None
            return

        icon_lr = self._icon_widget.layout_rect
        if icon_lr is None:
            self._badge_rect = None
            return

        bw, bh = self._badge_widget.preferred_size()
        if bw <= 0 or bh <= 0:
            self._badge_rect = None
            return

        ix, iy, iw, _ih = icon_lr
        if isinstance(self._badge_widget, LargeBadge):
            # stick(target_anchor="top-right", content_anchor="bottom-left", offset=(-12, 14))
            bx = int(round(ix + iw - 12.0))
            by = int(round(iy + 14.0 - bh))
        else:
            # SmallBadge: stick(target_anchor="top-right", content_anchor="bottom-left", offset=(-6, 6))
            bx = int(round(ix + iw - 6.0))
            by = int(round(iy + 6.0 - bh))

        self._badge_widget.layout(bw, bh)
        self._badge_widget.set_layout_rect(bx, by, bw, bh)
        self._badge_rect = (bx, by, bw, bh)

    def draw_background(self, canvas, x: int, y: int, width: int, height: int) -> None:
        if canvas is None or self._indicator_rect is None:
            return

        if not self._selected or self._indicator_color is None:
            return

        from nuiitivet.theme.theme import Theme

        color = resolve_color_to_rgba(self._indicator_color, theme=Theme.of(self))
        if color is None:
            return
        r, g, b, a = color
        paint = make_paint(color=(r, g, b, a), style="fill")

        ind_x, ind_y, ind_w, ind_h = self._indicator_rect
        rect = make_rect(x + ind_x, y + ind_y, ind_w, ind_h)
        radius = float(self._indicator_radius)
        radii = [radius, radius, radius, radius]
        draw_round_rect(canvas, rect, radii, paint)

    def draw_focus_indicator(self, canvas, x: int, y: int, width: int, height: int):
        """Draw the focus ring inset within the active-indicator shape.

        Rail items sit too close together vertically for the standard outer
        ring: offset outside one indicator it would overlap the neighbouring
        indicators. The ring is drawn just inside the indicator outline instead
        (the inset focus ring Jetpack Compose's Material 3 ripple uses), so it
        can never collide.
        """
        if self._indicator_rect is None:
            return
        try:
            from nuiitivet.theme.theme import Theme

            color = resolve_color_to_rgba(self._FOCUS_RING_COLOR, theme=Theme.of(self))
            if color is None:
                return

            thickness = self._FOCUS_RING_THICKNESS
            inset = self._FOCUS_RING_OFFSET + thickness / 2.0

            ind_x, ind_y, ind_w, ind_h = self._indicator_rect
            if ind_w <= 2 * inset or ind_h <= 2 * inset:
                return

            paint = make_paint(color=color, style="stroke", stroke_width=thickness)
            rect = make_rect(x + ind_x + inset, y + ind_y + inset, ind_w - 2 * inset, ind_h - 2 * inset)
            radius = max(0.0, float(self._indicator_radius) - inset)
            draw_round_rect(canvas, rect, [radius, radius, radius, radius], paint)
        except Exception:
            exception_once(logger, "rail_item_focus_ring_exc", "Failed to draw focus indicator")

    def draw_state_layer(self, canvas, x: int, y: int, width: int, height: int):
        """Draw state layer matching the indicator shape."""
        if self._indicator_rect is None:
            return

        ind_x, ind_y, ind_w, ind_h = self._indicator_rect
        abs_x = x + ind_x
        abs_y = y + ind_y

        # Draw state layer.
        opacity = self._get_active_state_layer_opacity()
        if opacity <= 0:
            return

        from nuiitivet.theme.theme import Theme

        color = resolve_color_to_rgba(self.state_layer_color, theme=Theme.of(self))
        if color is None:
            return
        r, g, b, a = color
        final_alpha = a * opacity
        paint = make_paint(color=(r, g, b, final_alpha), style="fill")

        rect = make_rect(abs_x, abs_y, ind_w, ind_h)
        radius = float(self._indicator_radius)
        radii = [radius, radius, radius, radius]

        draw_round_rect(canvas, rect, radii, paint)

    def draw_children(self, canvas, x: int, y: int, width: int, height: int):
        if not self.children:
            return

        if any(child.layout_rect is None for child in self.children):
            return

        for child in self.children_snapshot():
            rect = child.layout_rect
            if rect is None:
                continue
            rel_x, rel_y, child_w, child_h = rect
            cx = x + rel_x
            cy = y + rel_y
            child.set_last_rect(cx, cy, child_w, child_h)
            child.paint(canvas, cx, cy, child_w, child_h)

        # Paint badge on top of all other children.
        if self._badge_widget is not None and self._badge_rect is not None:
            bx, by, bw, bh = self._badge_rect
            self._badge_widget.set_last_rect(x + bx, y + by, bw, bh)
            self._badge_widget.paint(canvas, x + bx, y + by, bw, bh)


class _NavigationRailLayout(Widget):
    """Custom deterministic layout for NavigationRail."""

    def __init__(
        self,
        *,
        menu_button: Optional[Widget],
        item_buttons: Sequence[_RailItemButton],
        animation: Animatable,
        style: NavigationRailStyle,
    ) -> None:
        """Initialize layout controller.

        Args:
            menu_button: Optional menu button widget.
            item_buttons: Rail item button widgets.
            animation: Expand animation controller.
            style: Effective navigation rail style.
        """
        super().__init__(width=Sizing.weight(1), height=Sizing.weight(1), padding=0)
        self._menu_button = menu_button
        self._item_buttons = list(item_buttons)
        self._animation = animation
        self._style = style
        self._expand_subscription = animation.subscribe(self._on_animation_tick)

        if menu_button is not None:
            self.add_child(menu_button)
        for item in self._item_buttons:
            self.add_child(item)

        self.on_dispose(self.dispose)

    def _on_animation_tick(self, _: float) -> None:
        self.mark_needs_layout()
        self.invalidate()

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return the intrinsic content size using the collapsed metrics.

        Mirrors the running cursor used in :meth:`layout` so that ``auto`` height
        sizes the rail to its content instead of collapsing to zero (which would
        leave it painted but invisible to hit-testing).
        """
        gap = float(self._style.gap_collapsed)

        height = float(self._style.top_padding)
        if self._menu_button is not None:
            height += float(self._style.menu_button_size) + gap

        item_count = len(self._item_buttons)
        if item_count > 0:
            height += item_count * float(self._style.item_height)
            height += (item_count - 1) * gap

        width = float(self._style.container_width_collapsed)

        pref_w = int(width)
        pref_h = int(height)
        if max_width is not None:
            pref_w = min(pref_w, int(max_width))
        if max_height is not None:
            pref_h = min(pref_h, int(max_height))
        return (pref_w, pref_h)

    def layout(self, width: int, height: int) -> None:
        Widget.layout(self, width, height)

        t = _clamp01(self._animation.value)
        gap_collapsed = float(self._style.gap_collapsed)
        gap_expanded = float(self._style.gap_expanded)
        collapsed_width = float(self._style.container_width_collapsed)
        margin = max(0.0, (collapsed_width - self._style.indicator_width_collapsed) / 2.0)

        cursor_collapsed = float(self._style.top_padding)
        cursor_expanded = float(self._style.top_padding)

        if self._menu_button is not None:
            menu_size = float(self._style.menu_button_size)
            menu_rect = lerp_rect(
                Rect(x=margin, y=cursor_collapsed, width=menu_size, height=menu_size),
                Rect(x=margin, y=cursor_expanded, width=menu_size, height=menu_size),
                t,
            )
            menu_rect_i = menu_rect.to_int_tuple()
            self._menu_button.layout(menu_rect_i[2], menu_rect_i[3])
            self._menu_button.set_layout_rect(menu_rect_i[0], menu_rect_i[1], menu_rect_i[2], menu_rect_i[3])
            cursor_collapsed += menu_size + gap_collapsed
            cursor_expanded += menu_size + gap_expanded

        for item in self._item_buttons:
            item_rect = lerp_rect(
                Rect(x=0.0, y=cursor_collapsed, width=float(width), height=float(self._style.item_height)),
                Rect(x=0.0, y=cursor_expanded, width=float(width), height=float(self._style.item_height)),
                t,
            )
            item_rect_i = item_rect.to_int_tuple()
            item.layout(item_rect_i[2], item_rect_i[3])
            item.set_layout_rect(item_rect_i[0], item_rect_i[1], item_rect_i[2], item_rect_i[3])
            cursor_collapsed += float(self._style.item_height) + gap_collapsed
            cursor_expanded += float(self._style.item_height) + gap_expanded

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)

        if any(child.layout_rect is None for child in self.children):
            return

        for child in self.children_snapshot():
            rect = child.layout_rect
            if rect is None:
                continue
            rel_x, rel_y, child_w, child_h = rect
            cx = x + rel_x
            cy = y + rel_y
            child.set_last_rect(cx, cy, child_w, child_h)
            child.paint(canvas, cx, cy, child_w, child_h)

    def dispose(self) -> None:
        if self._expand_subscription is not None:
            self._expand_subscription.dispose()
            self._expand_subscription = None


class _RailTraversalPolicy(FocusNodePolicy):
    """Traversal over the rail's items, entered at the selected one.

    Like a radio group, the selected destination is the rail's stop in the Tab
    sequence: Tab lands where the app currently is, and the arrow keys rove
    from there.
    """

    def __init__(self, rail: "NavigationRail") -> None:
        super().__init__(rail._item_focus_nodes)
        self._rail = rail

    def entry_index(self, backwards: bool) -> int:
        index = self._rail.current_index
        if 0 <= index < len(self.members()):
            return index
        return super().entry_index(backwards)


class NavigationRail(InteractionHostMixin, Widget):
    """Vertical navigation bar for desktop applications.

    Material Design 3 component for persistent side navigation.
    Replaces NavigationDrawer for desktop/tablet layouts.

    Display modes:
    - Collapsed (expanded=False): Icon above label (vertical), 96px wide
    - Expanded (expanded=True): Icon + label (horizontal), 220-360px wide
      (the expanded width is set via the ``width`` argument; see ``__init__``)

    Both modes show labels. The active indicator (selection background) wraps:
    - Collapsed: Only the icon (56×32dp)
    - Expanded: Both icon and label

    Users can toggle between modes with optional menu button.

    For type-safe index, use IntEnum:
        class Section(IntEnum):
            HOME = 0
            SEARCH = 1
        NavigationRail(children=[...], index=Section.HOME)
    """

    def __init__(
        self,
        children: Sequence[RailItem],
        *,
        index: Union[int, MutableObservableBase[int]] = 0,
        on_select: Optional[Callable[[int], None]] = None,
        expanded: Union[bool, MutableObservableBase[bool]] = False,
        show_menu_button: bool = True,
        width: Union[SizingLike, ReadOnlyObservableProtocol] = None,
        height: Union[SizingLike, ReadOnlyObservableProtocol] = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        style: Optional[NavigationRailStyle] = None,
        key: Optional[str] = None,
    ) -> None:
        """Initialize NavigationRail.

        Args:
            children: The rail items to display.
            index: The currently selected index. ``int`` or a **mutable**
                ``Observable[int]`` — the rail writes the selection back, so a
                read-only/computed observable is rejected.
            on_select: Callback when an item is selected.
            expanded: Whether the rail is expanded. ``bool`` or a **mutable**
                ``Observable[bool]`` — the menu button writes it back, so a
                read-only/computed observable is rejected. To drive expansion
                from derived state (e.g. window size), mirror it into an
                ``Observable`` and update that.
            show_menu_button: Whether to show the menu toggle button.
            width: Expanded rail width. A *fixed* value (e.g. ``280`` or
                ``Sizing.fixed(280)``) sets the expanded width, clamped into the
                MD3 range ``[220, 360]`` (see ``NavigationRailStyle``). The rail
                always animates between the collapsed width and this expanded
                width; the collapsed width is never overridden here. Any
                non-fixed value (or ``None``) uses the minimum expanded width;
                non-fixed values also emit a warning.
            height: Height specification.
            padding: Padding specification.
            style: Custom NavigationRailStyle.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        _reject_readonly_observable(index, "index")
        _reject_readonly_observable(expanded, "expanded")

        self._is_expanded = expanded.value if isinstance(expanded, MutableObservableBase) else bool(expanded)
        self._style = style
        self._menu_icon_name: Optional[_ObservableValue[str]] = None
        eff_style = style or NavigationRailStyle()

        # Animation setup
        initial_expanded_value = 1.0 if self._is_expanded else 0.0
        self._expand_motion = EXPRESSIVE_DEFAULT_SPATIAL
        self._expand_animation: Animatable[float] = Animatable(initial_expanded_value, motion=self._expand_motion)
        self._label_animation: Animatable[float] = Animatable(initial_expanded_value, motion=EXPRESSIVE_DEFAULT_EFFECTS)
        self._menu_rotation_anim: Animatable[float] = Animatable(
            initial_expanded_value,
            motion=EXPRESSIVE_DEFAULT_EFFECTS,
        )
        self._menu_rotation = self._menu_rotation_anim.map(lambda progress: lerp(180.0, 360.0, progress))
        self._log_instance_id = id(self)
        logger.debug("NavigationRail init id=%s", self._log_instance_id)

        # Resolve the expanded width from `width` (only a fixed value sets it),
        # then always drive the outer width via the collapse animation so the
        # rail animates 96dp <-> expanded width regardless of what was passed.
        self._expanded_width, width_warning = _resolve_expanded_width(width, eff_style)
        collapsed_width = float(eff_style.container_width_collapsed)
        expanded_width = self._expanded_width
        animated_width = self._expand_animation.map(
            lambda progress: Sizing.fixed(
                int(lerp(collapsed_width, expanded_width, progress))
            )
        )

        super().__init__(width=animated_width, height=height, padding=padding, key=key)

        if width_warning is not None:
            warning_once(logger, width_warning[0], width_warning[1])

        # The rail is one focus traversal group (WAI-ARIA tabs, manual
        # activation): a single Tab stop entered at the selected item, with
        # Up/Down roving the focus between the items — wrapping at the ends —
        # and Enter/Space selecting the focused one. Roving deliberately does
        # not move the selection: selecting a destination navigates, which is
        # too heavy an action to fire on every arrow press.
        self._focus_node = FocusNode(on_key=self.on_key_event)
        self.add_node(self._focus_node)
        self._focus_scope = FocusScope(_RailTraversalPolicy(self), tab_roves=False)
        self.add_node(self._focus_scope)

        self._item_buttons: list[_RailItemButton] = []

        self._rail_items: Sequence[RailItem] = list(children)
        self.on_select = on_select
        self.show_menu_button = show_menu_button

        # Handle index.
        self._index_observable: Optional[MutableObservableBase[int]] = None
        self._index_subscription = None
        if isinstance(index, MutableObservableBase):
            self._index_observable = index
            self._current_index = self._validate_index(index.value)
            self._index_subscription = index.subscribe(self._on_index_changed)
        else:
            self._current_index = self._validate_index(int(index))

        # Handle expanded state.
        self._expanded_observable: Optional[MutableObservableBase[bool]] = None
        self._expanded_subscription = None
        if isinstance(expanded, MutableObservableBase):
            self._expanded_observable = expanded
            # _is_expanded already set above
            self._expanded_subscription = expanded.subscribe(self._on_expanded_changed)
        # else: _is_expanded already set above

        # Ensure subscriptions are released when removed from the tree.
        self.on_dispose(self.dispose)

        # Build UI.
        self._rebuild_ui()

    def _item_focus_nodes(self) -> list[FocusNode]:
        """Return the FocusNodes of the item buttons, in tree order."""
        return [cast(FocusNode, item.get_node(FocusNode)) for item in self._item_buttons]

    def on_key_event(self, key: str, modifier_keys: int = 0) -> bool:
        """Rove the items with Up/Down, wrapping; Enter/Space acts on the focused item.

        Only the vertical axis roves — a rail is always a column. Enter/Space
        are handled by the focused item itself, so they never reach here.
        """
        key_name = str(key).lower()

        if key_name == "down":
            return self._focus_scope.move(1, wrap=True)

        if key_name == "up":
            return self._focus_scope.move(-1, wrap=True)

        return False

    def _on_index_changed(self, new_index: int) -> None:
        """Handle Observable index changes."""
        old_index = self._current_index
        self._current_index = self._validate_index(new_index)
        if old_index != self._current_index:
            self._update_selected(old_index, self._current_index)

    def _update_selected(self, old_index: int, new_index: int) -> None:
        if not self._item_buttons:
            self._rebuild_ui()
            return
        if 0 <= old_index < len(self._item_buttons):
            self._item_buttons[old_index].set_selected(False, self.style)
        if 0 <= new_index < len(self._item_buttons):
            self._item_buttons[new_index].set_selected(True, self.style)
        self.invalidate()

    def _on_expanded_changed(self, new_expanded: bool) -> None:
        """Handle Observable expanded changes."""
        # Drive animation instead of immediate rebuild.
        should_expand = bool(new_expanded)
        target_value = 1.0 if should_expand else 0.0
        self._expand_animation.target = target_value
        self._label_animation.target = target_value
        self._menu_rotation_anim.target = target_value

        self._is_expanded = should_expand
        if self._menu_icon_name is not None:
            self._menu_icon_name.value = "menu_open" if should_expand else "menu"
        # Keep structure static; animate properties only.

    def _validate_index(self, index: int) -> int:
        """Ensure index is within valid range."""
        if not self._rail_items:
            return 0
        return max(0, min(index, len(self._rail_items) - 1))

    def _rebuild_ui(self) -> None:
        """Rebuild the navigation rail UI."""
        # Clear existing children.
        self.clear_children()

        # Build menu button if enabled.
        menu_button = None
        eff_style = self.style or NavigationRailStyle()
        if self.show_menu_button:
            menu_button = self._build_menu_button()

        # Build rail items.
        item_buttons = []
        for idx, rail_item in enumerate(self._rail_items):
            selected = idx == self._current_index

            def _on_click(i: int = idx) -> None:
                self._handle_item_click(i)

            button = _RailItemButton(
                rail_item=rail_item,
                selected=selected,
                expand_animation=self._expand_animation,
                label_animation=self._label_animation,
                rail_style=self.style,
                expanded_width=self._expanded_width,
                on_click=_on_click,
            )
            item_buttons.append(button)
        self._item_buttons = item_buttons

        rail_layout = _NavigationRailLayout(
            menu_button=menu_button,
            item_buttons=item_buttons,
            animation=self._expand_animation,
            style=eff_style,
        )

        # Add background.
        bg_color = eff_style.background or ColorRole.SURFACE
        rail_bg = Box(
            child=rail_layout,
            background_color=bg_color,
            width=Sizing.weight(1),
            height=Sizing.weight(1),
            alignment="top-left",
        )

        self.add_child(rail_bg)

    def _calculate_width(self) -> int:
        """Calculate rail width based on expanded state.

        The outer width animates between the collapsed width and the resolved
        expanded width (:attr:`_expanded_width`), so this returns the target for
        the current state.
        """
        eff_style = self.style or NavigationRailStyle()
        if self._is_expanded:
            return int(self._expanded_width)
        return int(eff_style.container_width_collapsed)

    def _build_menu_button(self) -> Widget:
        """Build the menu toggle button."""
        if self._menu_icon_name is None:
            self._menu_icon_name = _ObservableValue("menu_open" if self._is_expanded else "menu")

        eff_style = self.style or NavigationRailStyle()
        color = eff_style.menu_icon_color or ColorRole.ON_SURFACE
        icon_size = eff_style.icon_size
        icon = Icon(self._menu_icon_name, size=icon_size, style=IconStyle(color=color)).modifier(
            rotate(self._menu_rotation)
        )

        # Wrap with InteractionHostMixin for click handling.
        class MenuButton(InteractionHostMixin, Box):
            def __init__(self, child: Widget, on_click: Callable[[], None]):
                super().__init__(
                    child=child,
                    width=Sizing.fixed(eff_style.menu_button_size),
                    height=Sizing.fixed(eff_style.menu_button_size),
                    alignment="center",
                )
                self._state = InteractionState(disabled=False)
                self.enable_hover()
                self.enable_click(on_click=on_click)

        return MenuButton(icon, self._toggle_expanded)

    def _toggle_expanded(self) -> None:
        """Toggle expanded state."""
        new_state = not self._is_expanded

        if self._expanded_observable is not None:
            # Update Observable (triggers subscription).
            self._expanded_observable.value = new_state
        else:
            # Update local state directly.
            self._on_expanded_changed(new_state)

    def _handle_item_click(self, index: int) -> None:
        """Handle item selection."""
        if self._index_observable is not None:
            # Update Observable.
            self._index_observable.value = index
        else:
            # Update local state.
            old_index = self._current_index
            self._current_index = index
            if old_index != self._current_index:
                self._update_selected(old_index, self._current_index)

        # Fire callback.
        if self.on_select is not None:
            self.on_select(index)

    @property
    def style(self) -> Optional[NavigationRailStyle]:
        """Get the navigation rail style."""
        return self._style

    @property
    def current_index(self) -> int:
        """Get the currently selected item index."""
        return self._current_index

    @property
    def is_expanded(self) -> bool:
        """Get the current expanded state."""
        return self._is_expanded

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Calculate preferred size for the navigation rail."""
        rail_width = self._calculate_width()

        # Get height from child if present.
        children = self.children_snapshot()
        if children:
            child = children[0]
            child_w, child_height = child.preferred_size(max_width=rail_width, max_height=max_height)
            preferred_w = max(int(rail_width), int(child_w))
            preferred_h = int(child_height)

            if max_width is not None:
                preferred_w = min(int(preferred_w), int(max_width))
            if max_height is not None:
                preferred_h = min(int(preferred_h), int(max_height))

            return (int(preferred_w), int(preferred_h))

        # Default minimum height.
        preferred_w = int(rail_width)
        preferred_h = 400
        if max_width is not None:
            preferred_w = min(int(preferred_w), int(max_width))
        if max_height is not None:
            preferred_h = min(int(preferred_h), int(max_height))
        return (int(preferred_w), int(preferred_h))

    def layout(self, width: int, height: int) -> None:
        """Layout the navigation rail and its child."""
        super().layout(width, height)

        children = self.children_snapshot()
        if not children:
            return

        # Layout the single child (Box containing Column).
        child = children[0]
        # Use provided dimensions minus padding.
        l, t, r, b = self.padding
        cw = max(0, width - l - r)
        ch = max(0, height - t - b)

        child.layout(cw, ch)
        child.set_layout_rect(l, t, cw, ch)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint the NavigationRail."""
        children = self.children_snapshot()
        if not children:
            return

        # Layout not yet complete; skip this frame.
        if any(c.layout_rect is None for c in children):
            return

        # Paint the child.
        child = children[0]
        rect = child.layout_rect
        if rect is None:
            return

        rel_x, rel_y, w, h = rect
        abs_x = x + rel_x
        abs_y = y + rel_y

        child.set_last_rect(abs_x, abs_y, w, h)
        child.paint(canvas, abs_x, abs_y, w, h)

    def dispose(self) -> None:
        """Clean up subscriptions."""
        logger.debug("NavigationRail dispose id=%s", self._log_instance_id)
        if self._index_subscription is not None:
            self._index_subscription.dispose()
            self._index_subscription = None
        if self._expanded_subscription is not None:
            self._expanded_subscription.dispose()
            self._expanded_subscription = None
        self._expand_animation.stop()  # Ensure ticker stopped
        self._label_animation.stop()
        self._menu_rotation_anim.stop()
