from __future__ import annotations

from typing import Callable, Optional, Sequence, Tuple, Union
import logging

from nuiitivet.widgeting.widget import Widget
from nuiitivet.rendering.sizing import SizingLike, Sizing
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.observable.protocols import ReadOnlyObservableProtocol
from nuiitivet.animation import Animatable, Rect, lerp, lerp_rect
from nuiitivet.material.text import Text
from nuiitivet.material.icon import Icon
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import InteractionHostMixin, InteractionState
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.styles.navigation_rail_style import NavigationRailStyle
from nuiitivet.material.styles.icon_style import IconStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.rendering.skia import make_paint, make_rect, draw_round_rect
from nuiitivet.theme.types import ColorSpec
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.material.badge import BadgeValue, LargeBadge
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_SPATIAL, EXPRESSIVE_DEFAULT_EFFECTS
from nuiitivet.modifiers.transform import rotate


logger = logging.getLogger(__name__)


class RailItem(Widget):
    """Navigation rail destination item.

    A widget representing a single destination in NavigationRail.
    Displays an icon and optional label (when rail is expanded).
    """

    def __init__(
        self,
        icon: str,
        label: str,
        *,
        badge: Optional[ReadOnlyObservableProtocol[BadgeValue]] = None,
        style: Optional[NavigationRailStyle] = None,
    ) -> None:
        """Initialize RailItem.

        Args:
            icon: The icon name to display.
            label: The label text to display.
            badge: Optional Observable badge value. Use ``BadgeValue.small()``,
                ``BadgeValue.large(count)`` or ``BadgeValue.none()``.
            style: Optional style override for this item.
        """
        super().__init__()

        if not isinstance(icon, str):
            raise TypeError(f"icon must be str, got {type(icon)}")
        if not isinstance(label, str):
            raise TypeError(f"label must be str, got {type(label)}")

        self.icon_spec = icon
        self.label_spec = label
        self._badge_observable: Optional[ReadOnlyObservableProtocol[BadgeValue]] = badge
        self._style = style

        self._icon_widget: Widget
        self._label_widget: Widget

        eff_style = style or NavigationRailStyle()
        icon_color = eff_style.icon_color or ColorRole.ON_SURFACE
        icon_size = eff_style.icon_size
        self._icon_widget = Icon(icon, size=icon_size, style=IconStyle(color=icon_color))

        if eff_style.label_text_style is not None:
            text_style = eff_style.label_text_style.copy_with(
                color=eff_style.label_color or ColorRole.ON_SURFACE_VARIANT,
                font_size=12,
                text_alignment="center",
                overflow="ellipsis",
            )
        else:
            text_style = TextStyle(
                color=eff_style.label_color or ColorRole.ON_SURFACE_VARIANT,
                font_size=12,
                text_alignment="center",
                overflow="ellipsis",
            )

        self._label_widget = Text(
            label,
            style=text_style,
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
    def badge_observable(self) -> Optional[ReadOnlyObservableProtocol[BadgeValue]]:
        """Get the optional badge observable."""
        return self._badge_observable


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
        on_click: Optional[Callable[[], None]] = None,
    ) -> None:
        self._expand_animation = expand_animation
        self._label_animation = label_animation
        # Resolve effective style: item style > rail style > defaults
        eff_style = rail_item.style or rail_style or NavigationRailStyle()
        self._eff_style = eff_style
        self._selected = bool(selected)
        self._indicator_color: Optional[ColorSpec] = None
        self._indicator_rect: Optional[Tuple[int, int, int, int]] = None
        self._indicator_radius: float = 0.0

        # Core widgets
        self._icon_widget = rail_item.icon_widget

        base_label_style = eff_style.label_text_style or TextStyle(
            color=ColorRole.ON_SURFACE_VARIANT,
            font_size=14,
            text_alignment="start",
            overflow="clip",
        )

        self._vertical_label = Text(
            rail_item.label_spec,
            style=base_label_style.copy_with(font_size=12, text_alignment="center"),
        )
        self._horizontal_label = Text(
            rail_item.label_spec,
            style=base_label_style.copy_with(font_size=14, text_alignment="start"),
        )

        # Fixed content size with animated clip window.
        self._vertical_content = Box(
            child=self._vertical_label,
            width=Sizing.fixed(eff_style.container_width_collapsed),
            height=Sizing.fixed(eff_style.label_height),
            alignment="center",
        )
        self._vertical_label_container = Box(
            child=self._vertical_content,
            width=Sizing.fixed(eff_style.container_width_collapsed),
            height=Sizing.fixed(eff_style.label_height),
            alignment="top_center",
        )
        self._vertical_label_container.clip_content = True

        self._horizontal_content = Box(
            child=self._horizontal_label,
            width=Sizing.fixed(eff_style.horizontal_label_width),
            height=Sizing.fixed(eff_style.label_height),
            alignment="center_left",
        )
        self._horizontal_label_container = Box(
            child=self._horizontal_content,
            width=Sizing.fixed(eff_style.horizontal_label_width),
            height=Sizing.fixed(eff_style.label_height),
            alignment="center_left",
        )
        self._horizontal_label_container.clip_content = True

        # Badge state
        self._badge_widget: Optional[Widget] = None
        self._badge_rect: Optional[Tuple[int, int, int, int]] = None
        self._badge_subscription = None

        super().__init__(
            child=None,
            on_click=on_click,
            width=Sizing.flex(1),
            height=Sizing.fixed(eff_style.item_height),
            padding=0,
            focusable=False,
        )

        # Add children manually; draw_children is overridden.
        self.add_child(self._icon_widget)
        self.add_child(self._horizontal_label_container)
        self.add_child(self._vertical_label_container)

        self._apply_colors(selected=self._selected, rail_style=rail_style)

        # Sync interaction state
        self.state.selected = selected

        # Subscribe to badge observable if provided.
        badge_observable = rail_item.badge_observable
        if badge_observable is not None:
            self._update_badge_widget(badge_observable.value)
            self._badge_subscription = badge_observable.subscribe(self._on_badge_changed)

        self.on_dispose(self._dispose_badge)

    # Bindings are automatically disposed by BindingHostMixin/observe.

    def _dispose_badge(self) -> None:
        if self._badge_subscription is not None:
            self._badge_subscription.dispose()
            self._badge_subscription = None

    def _on_badge_changed(self, value: BadgeValue) -> None:
        """React to badge observable changes."""
        self._update_badge_widget(value)
        # Keep animation flow intact; repaint is enough after badge swap.
        self.invalidate()

    def _update_badge_widget(self, value: BadgeValue) -> None:
        """Create or clear the badge widget from a BadgeValue."""
        self._badge_widget = value.to_widget()
        self._badge_rect = None

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
            self._vertical_label._style = current_style.copy_with(color=label_color, text_alignment="center")
            self._vertical_label.invalidate()

        if isinstance(self._horizontal_label, Text):
            current_style = getattr(self._horizontal_label, "_style", None) or TextStyle()
            self._horizontal_label._style = current_style.copy_with(color=label_color, text_alignment="start")
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
                width=float(self._eff_style.indicator_width_expanded),
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
                width=float(self._eff_style.horizontal_label_width),
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
            # stick(alignment="top-right", anchor="bottom-left", offset=(-12, 14))
            bx = int(round(ix + iw - 12.0))
            by = int(round(iy + 14.0 - bh))
        else:
            # SmallBadge: stick(alignment="top-right", anchor="bottom-left", offset=(-6, 6))
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

        color = resolve_color_to_rgba(self._indicator_color, self)
        if color is None:
            return
        r, g, b, a = color
        paint = make_paint(color=(r, g, b, a), style="fill")

        ind_x, ind_y, ind_w, ind_h = self._indicator_rect
        rect = make_rect(x + ind_x, y + ind_y, ind_w, ind_h)
        radius = float(self._indicator_radius)
        radii = [radius, radius, radius, radius]
        draw_round_rect(canvas, rect, radii, paint)

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

        color = resolve_color_to_rgba(self.state_layer_color, self)
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
            self.layout(width, height)

        # Recompute badge placement lazily when badge content changed.
        if self._badge_widget is not None and self._badge_rect is None:
            self._place_badge()

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
        super().__init__(width=Sizing.flex(1), height=Sizing.flex(1), padding=0)
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
            self.layout(width, height)

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


class NavigationRail(Widget):
    """Vertical navigation bar for desktop applications.

    Material Design 3 component for persistent side navigation.
    Replaces NavigationDrawer for desktop/tablet layouts.

    Display modes:
    - Collapsed (expanded=False): Icon above label (vertical), 96px wide
    - Expanded (expanded=True): Icon + label (horizontal), 220px wide

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
        index: Union[int, _ObservableValue[int]] = 0,
        on_select: Optional[Callable[[int], None]] = None,
        expanded: Union[bool, _ObservableValue[bool]] = False,
        show_menu_button: bool = True,
        width: Union[SizingLike, ReadOnlyObservableProtocol] = None,
        height: Union[SizingLike, ReadOnlyObservableProtocol] = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        style: Optional[NavigationRailStyle] = None,
    ) -> None:
        """Initialize NavigationRail.

        Args:
            children: The rail items to display.
            index: The currently selected index (int or Observable).
            on_select: Callback when an item is selected.
            expanded: Whether the rail is expanded (bool or Observable).
            show_menu_button: Whether to show the menu toggle button.
            width: Width specification.
            height: Height specification.
            padding: Padding specification.
            style: Custom NavigationRailStyle.
        """
        self._is_expanded = expanded.value if isinstance(expanded, _ObservableValue) else bool(expanded)
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

        # Drive width via animation if not fixed
        if width is None:
            width = self._expand_animation.map(
                lambda progress: Sizing.fixed(
                    int(
                        lerp(
                            float(eff_style.container_width_collapsed),
                            float(eff_style.container_width_expanded),
                            progress,
                        )
                    )
                )
            )

        super().__init__(width=width, height=height, padding=padding)

        self._item_buttons: list[_RailItemButton] = []

        self._rail_items: Sequence[RailItem] = list(children)
        self.on_select = on_select
        self.show_menu_button = show_menu_button

        # Handle index.
        self._index_observable: Optional[_ObservableValue[int]] = None
        self._index_subscription = None
        if isinstance(index, _ObservableValue):
            self._index_observable = index
            self._current_index = self._validate_index(index.value)
            self._index_subscription = index.subscribe(self._on_index_changed)
        else:
            self._current_index = self._validate_index(int(index))

        # Handle expanded state.
        self._expanded_observable: Optional[_ObservableValue[bool]] = None
        self._expanded_subscription = None
        if isinstance(expanded, _ObservableValue):
            self._expanded_observable = expanded
            # _is_expanded already set above
            self._expanded_subscription = expanded.subscribe(self._on_expanded_changed)
        # else: _is_expanded already set above

        # Ensure subscriptions are released when removed from the tree.
        self.on_dispose(self.dispose)

        # Build UI.
        self._rebuild_ui()

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
            width=Sizing.flex(1),
            height=Sizing.flex(1),
            alignment="top_left",
        )

        self.add_child(rail_bg)

    def _calculate_width(self) -> int:
        """Calculate rail width based on expanded state."""
        if self.width_sizing.kind == "fixed":
            # Use explicit width if provided.
            return int(self.width_sizing.value)
        # M3 defaults: 96dp collapsed, 220dp expanded.
        eff_style = self.style or NavigationRailStyle()
        return int(eff_style.container_width_expanded if self._is_expanded else eff_style.container_width_collapsed)

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

        # Auto-layout fallback.
        if any(c.layout_rect is None for c in children):
            self.layout(width, height)

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
