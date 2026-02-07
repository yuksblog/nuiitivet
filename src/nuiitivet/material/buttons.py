"""Material Design 3 Buttons.

This module contains the implementation of various Material Design 3 buttons:
- FilledButton
- OutlinedButton
- TextButton
- ElevatedButton
- FilledTonalButton
- FloatingActionButton
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Tuple, Type, Union, TYPE_CHECKING

from nuiitivet.common.logging_once import debug_once, exception_once
from nuiitivet.observable import ObservableProtocol, ReadOnlyObservableProtocol
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.theme.types import ColorSpec
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia.color import make_opacity_paint
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.material.symbols import Symbol

logger = logging.getLogger(__name__)


_Symbol: Optional[Type["Symbol"]] = None
_Widget: Optional[Type["Widget"]] = None
try:
    from nuiitivet.material.symbols import Symbol as _ImportedSymbol

    _Symbol = _ImportedSymbol
except Exception:
    debug_once(logger, "button_helpers_import_symbol_exc", "Failed to import nuiitivet.symbols.Symbol")
    _Symbol = None
try:
    from nuiitivet.widgeting.widget import Widget as _Widget
except Exception:
    debug_once(logger, "button_helpers_import_widget_exc", "Failed to import nuiitivet.widgeting.widget.Widget")
    _Widget = None


# --- Helpers ---


def _m3_icon_size_for_height(height: Optional[Union[int, float]]) -> int:
    """Return a sensible icon pixel size per M3-like heuristics."""
    try:
        if height is None:
            return 20
        h = int(height)
    except Exception:
        exception_once(logger, "button_m3_icon_size_exc", "Failed to coerce button height to int")
        return 20
    if h >= 56:
        return 24
    if h >= 40:
        return 20
    return 20


def _coerce_fixed_height_px(height: SizingLike) -> Optional[int]:
    """Return a fixed pixel height if it can be determined."""
    if height is None:
        return None
    try:
        from nuiitivet.rendering.sizing import parse_sizing

        parsed = parse_sizing(height, default=None)
        if getattr(parsed, "kind", None) == "fixed":
            return int(parsed.value)
    except Exception:
        pass
    if isinstance(height, (int, float)):
        return int(height)
    return None


def make_child_from_label(label: Any, foreground: ColorSpec = ColorRole.ON_SURFACE) -> Any:
    """Return a child widget for the given label."""
    # Local import to avoid circular imports at module import time.
    from nuiitivet.material.text import Text
    from nuiitivet.material.styles.text_style import TextStyle

    # Material button label is always rendered via Material Text.
    return Text(label, style=TextStyle(color=foreground, font_size=14, text_alignment="center"))


def build_button_child(
    label: str | ReadOnlyObservableProtocol[str] | None,
    icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None,
    foreground: ColorSpec = ColorRole.ON_SURFACE,
    button_height: Optional[Union[int, float]] = None,
    icon_position: str = "leading",
    spacing: Optional[int] = None,
    style: Optional[ButtonStyle] = None,
) -> Any:
    """Compose a child widget for a button from label/icon."""
    # Local import to avoid circular imports at module import time.
    from nuiitivet.material.icon import Icon

    icon_widget: Any = None
    base_height = button_height
    if style is not None:
        try:
            container_h = int(getattr(style, "container_height", 0) or 0)
        except Exception:
            container_h = 0
        if container_h > 0:
            base_height = container_h
    if icon is not None:
        # Accept plain strings, Symbol instances, or ReadOnlyObservableProtocol sources.
        ok = (
            isinstance(icon, str)
            or (_Symbol is not None and isinstance(icon, _Symbol))
            or (hasattr(icon, "subscribe") and hasattr(icon, "value"))
        )
        if not ok:
            raise TypeError("icon must be a Symbol, string, or ReadOnlyObservableProtocol")

        from nuiitivet.material.styles.icon_style import IconStyle

        size_px = _m3_icon_size_for_height(base_height)
        icon_widget = Icon(icon, size=size_px, style=IconStyle(color=foreground))
    text_widget: Any = None
    if label is not None:
        text_widget = make_child_from_label(label, foreground)
    if icon_widget is None and text_widget is None:
        raise ValueError("Button requires one of label or icon")
    if icon_widget is not None and text_widget is None:
        return icon_widget
    if icon_widget is None and text_widget is not None:
        return text_widget
    assert icon_widget is not None and text_widget is not None

    children = [icon_widget, text_widget] if icon_position == "leading" else [text_widget, icon_widget]
    if spacing is None:
        try:
            spacing_val = int(getattr(style, "spacing", 8) or 8)
        except Exception:
            spacing_val = 8
    else:
        try:
            spacing_val = int(spacing)
        except Exception:
            spacing_val = 8
    from nuiitivet.layout.row import Row

    row: Any = Row(children, gap=spacing_val, cross_alignment="center")
    return row


def resolve_button_style_params(
    style: Optional[ButtonStyle],
    padding: Optional[Union[int, Tuple[int, int, int, int]]],
    height: SizingLike,
    disabled: bool | ObservableProtocol[bool],
) -> dict[str, Any]:
    """Resolve style parameters for ButtonBase."""

    # Defaults
    pad = padding
    h = height

    # Style defaults
    bg = None
    cr = None
    bc = None
    bw = 0.0

    if style is not None:
        bg = style.background
        if pad is None:
            pad = style.padding
        cr = style.corner_radius
        bc = getattr(style, "border_color", None)
        bw = getattr(style, "border_width", 0.0) or 0.0

    if pad is None:
        pad = 0

    # Keep height auto by default.
    # Minimum touch target is enforced by MaterialButtonBase.preferred_size.

    # Elevation -> Shadow
    shadow_color = None
    shadow_blur = 0.0
    shadow_offset = (0, 0)

    elevation_val = None
    if style and getattr(style, "elevation", None) is not None:
        try:
            elevation_val = float(style.elevation)
        except Exception as e:
            exception_once(
                logger,
                f"button_resolve_elevation_value_exc_{type(e).__name__}",
                "Failed to resolve button elevation",
            )

    if elevation_val is not None and elevation_val > 0.0:
        try:
            from nuiitivet.rendering.elevation import Elevation

            elev = Elevation.from_level(elevation_val)
            shadow_color = (ColorRole.SHADOW, elev.alpha)
            shadow_offset = elev.offset
            shadow_blur = elev.blur
        except Exception as exc:
            exception_once(
                logger,
                f"button_resolve_elevation_shadow_exc_{type(exc).__name__}",
                "Failed to resolve button shadow",
            )

    # Overlay
    overlay_color = None
    hover_opacity = 0.08
    pressed_opacity = 0.12

    if style:
        ov_entry = getattr(style, "overlay", None)
        if ov_entry:
            base_token, base_alpha = ov_entry
            overlay_color = base_token
            hover_opacity = float(base_alpha) * 0.5
            pressed_opacity = float(base_alpha)
        else:
            # Try direct attributes (ButtonStyle dataclass)
            oc = getattr(style, "overlay_color", None)
            oa = getattr(style, "overlay_alpha", None)
            if oc is not None:
                overlay_color = oc
                if oa is not None:
                    base_alpha = float(oa)
                    hover_opacity = base_alpha * 0.5
                    pressed_opacity = base_alpha

    return {
        "height": h,
        "background_color": bg,
        "padding": pad,
        "corner_radius": cr,
        "border_color": bc,
        "border_width": bw,
        "shadow_color": shadow_color,
        "shadow_blur": shadow_blur,
        "shadow_offset": shadow_offset,
        "state_layer_color": overlay_color,
        "hover_opacity": hover_opacity,
        "pressed_opacity": pressed_opacity,
        "drag_opacity": 0.16,
    }


# --- Material Base Class ---


class MaterialButtonBase(InteractiveWidget):
    """
    Base class for Material Design buttons.
    Uses InteractiveWidget for state layer handling.
    """

    @property
    def style(self) -> ButtonStyle:
        if hasattr(self, "_user_style") and self._user_style is not None:
            return self._user_style

        from nuiitivet.theme.manager import manager
        from nuiitivet.material.styles.button_style import ButtonStyle

        variant = getattr(self, "_variant", "filled")
        return ButtonStyle.from_theme(manager.current, variant)

    def __init__(
        self,
        child: Widget,
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int, int, int]] = 0,
        # Overlay / Feedback configuration
        state_layer_color: ColorSpec = None,
        overlay_color: ColorSpec = None,  # Backward compatibility
        hover_opacity: float = 0.08,
        pressed_opacity: float = 0.12,
        drag_opacity: float = 0.16,
        disabled_opacity: float = 0.38,
        **kwargs,
    ):
        """Initialize MaterialButtonBase.

        Args:
            child: The child widget to display inside the button.
            on_click: Callback to be invoked when the button is clicked.
            disabled: Whether the button is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding specification.
            state_layer_color: Color of the state layer (overlay).
            hover_opacity: Opacity of the overlay when hovered.
            pressed_opacity: Opacity of the overlay when pressed.
            drag_opacity: Opacity of the overlay when dragged.
            disabled_opacity: Opacity of the content when disabled.
            **kwargs: Additional arguments passed to the base class.
        """
        # Support old `overlay_color` arg by mapping to `state_layer_color`
        if state_layer_color is None and overlay_color is not None:
            state_layer_color = overlay_color

        super().__init__(
            child=child,
            on_click=on_click,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
            state_layer_color=state_layer_color,
            **kwargs,
        )

        # Instance-level customization of opacities for InteractiveWidget
        self._HOVER_OPACITY = hover_opacity
        self._PRESS_OPACITY = pressed_opacity
        self._DRAG_OPACITY = drag_opacity

        self.disabled_opacity = disabled_opacity

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        # Handle disabled state opacity (logic ported from ButtonBase)
        layer_count = 0
        if self.disabled and self.disabled_opacity < 1.0:
            try:
                opacity_paint = make_opacity_paint(self.disabled_opacity)
                if opacity_paint is not None:
                    canvas.saveLayer(None, opacity_paint)
                    layer_count += 1
            except Exception:
                exception_once(logger, "button_apply_disabled_layer_exc", "Failed to apply disabled opacity layer")

        try:
            super().paint(canvas, x, y, width, height)
        finally:
            if layer_count > 0:
                try:
                    canvas.restore()
                except Exception:
                    exception_once(logger, "button_restore_layer_exc", "Failed to restore disabled opacity layer")

    def _container_height_pixels(self, allocated_height: int) -> int:
        try:
            style = self.style
            raw = int(getattr(style, "container_height", 40) or 40)
        except Exception:
            raw = 40
        return max(0, min(int(raw), int(allocated_height)))

    def _container_rect(self, x: int, y: int, width: int, height: int) -> Tuple[int, int, int, int]:
        ch = self._container_height_pixels(height)
        cy = y + max(0, (int(height) - ch) // 2)
        return (int(x), int(cy), int(width), int(ch))

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        if not self.children:
            return

        child = self.children[0]
        ch = self._container_height_pixels(height)
        offset_y = max(0, (int(height) - ch) // 2)

        ix, iy, iw, ih = self._layout.compute_inner_rect(0, offset_y, width, ch)
        cx, cy, child_w, child_h = self._layout.resolve_child_geometry(child, ix, iy, iw, ih)

        child.layout(child_w, child_h)
        child.set_layout_rect(cx, cy, child_w, child_h)

    def draw_background(self, canvas, x: int, y: int, width: int, height: int):
        cx, cy, cw, ch = self._container_rect(x, y, width, height)
        return super().draw_background(canvas, cx, cy, cw, ch)

    def draw_border(self, canvas, x: int, y: int, width: int, height: int):
        cx, cy, cw, ch = self._container_rect(x, y, width, height)
        return super().draw_border(canvas, cx, cy, cw, ch)

    def draw_state_layer(self, canvas, x: int, y: int, width: int, height: int):
        cx, cy, cw, ch = self._container_rect(x, y, width, height)
        super().draw_state_layer(canvas, cx, cy, cw, ch)

    def draw_focus_indicator(self, canvas, x: int, y: int, width: int, height: int):
        cx, cy, cw, ch = self._container_rect(x, y, width, height)
        super().draw_focus_indicator(canvas, cx, cy, cw, ch)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        w, h = super().preferred_size(max_width=max_width, max_height=max_height)

        try:
            style = self.style
        except Exception as e:
            exception_once(
                logger,
                f"material_button_preferred_size_style_exc_{type(e).__name__}",
                "Failed to resolve Material button style",
            )
            return w, h

        if getattr(self.width_sizing, "kind", None) != "fixed":
            try:
                w = max(w, int(getattr(style, "min_width", 0) or 0))
            except Exception as e:
                exception_once(
                    logger,
                    f"material_button_preferred_size_min_width_exc_{type(e).__name__}",
                    "Failed to clamp Material button min_width",
                )

        if getattr(self.height_sizing, "kind", None) != "fixed":
            try:
                h = max(h, int(getattr(style, "min_height", 0) or 0))
            except Exception as e:
                exception_once(
                    logger,
                    f"material_button_preferred_size_min_height_exc_{type(e).__name__}",
                    "Failed to clamp Material button min_height",
                )

        if max_width is not None:
            w = min(int(w), int(max_width))
        if max_height is not None:
            h = min(int(h), int(max_height))

        return int(w), int(h)


# --- Concrete Implementations ---


class FilledButton(MaterialButtonBase):
    """Filled button built on ButtonBase. Delegates interaction and painting."""

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None = None,
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
        style: Optional[ButtonStyle] = None,
    ):
        """Initialize FilledButton.

        Args:
            label: Text label for the button.
            icon: Icon for the button.
            on_click: Callback to be invoked when the button is clicked.
            disabled: Whether the button is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding specification.
            style: Custom ButtonStyle.
        """
        self._variant = "filled"
        self._user_style = style
        self._user_padding = padding
        self._user_height = height

        effective_style = self.style
        text_color = effective_style.foreground if effective_style else ColorRole.ON_PRIMARY

        height_px = _coerce_fixed_height_px(height)

        child_widget = build_button_child(
            label=label,
            icon=icon,
            foreground=text_color,
            button_height=height_px,
            style=effective_style,
        )

        params = resolve_button_style_params(effective_style, padding, height, disabled)

        super().__init__(
            child=child_widget,
            on_click=on_click,
            width=width,
            disabled=disabled,
            **params,
        )

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.theme.manager import manager

        manager.subscribe(self._on_theme_change)

    def on_unmount(self) -> None:
        from nuiitivet.theme.manager import manager

        manager.unsubscribe(self._on_theme_change)
        super().on_unmount()

    def _on_theme_change(self, theme) -> None:
        params = resolve_button_style_params(
            self.style,
            self._user_padding,
            self._user_height,
            self.disabled,
        )

        # Update properties
        self.bgcolor = params["background_color"]
        self.padding = params["padding"]
        self.corner_radius = params["corner_radius"]
        self.shadow_color = params["shadow_color"]
        self.shadow_blur = params["shadow_blur"]
        self.shadow_offset = params["shadow_offset"]

        self.state_layer_color = params["state_layer_color"]
        self._HOVER_OPACITY = params["hover_opacity"]
        self._PRESS_OPACITY = params["pressed_opacity"]
        self.invalidate()


class OutlinedButton(MaterialButtonBase):
    """Outlined button: transparent background with an outline stroke."""

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None = None,
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
        style: Optional[ButtonStyle] = None,
    ):
        """Initialize OutlinedButton.

        Args:
            label: Text label for the button.
            icon: Icon for the button.
            on_click: Callback to be invoked when the button is clicked.
            disabled: Whether the button is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding specification.
            style: Custom ButtonStyle.
        """
        self._variant = "outlined"
        self._user_style = style
        self._user_padding = padding
        self._user_height = height

        effective_style = self.style
        text_color = effective_style.foreground if effective_style else ColorRole.PRIMARY

        height_px = _coerce_fixed_height_px(height)

        child_widget = build_button_child(
            label=label,
            icon=icon,
            foreground=text_color,
            button_height=height_px,
            style=effective_style,
        )

        params = resolve_button_style_params(
            effective_style,
            padding,
            height,
            disabled,
        )

        super().__init__(
            child=child_widget,
            on_click=on_click,
            width=width,
            disabled=disabled,
            **params,
        )

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.theme.manager import manager

        manager.subscribe(self._on_theme_change)

    def on_unmount(self) -> None:
        from nuiitivet.theme.manager import manager

        manager.unsubscribe(self._on_theme_change)
        super().on_unmount()

    def _on_theme_change(self, theme) -> None:
        params = resolve_button_style_params(
            self.style,
            self._user_padding,
            self._user_height,
            self.disabled,
        )

        # Update properties
        self.bgcolor = params["background_color"]
        self.padding = params["padding"]
        self.corner_radius = params["corner_radius"]
        self.shadow_color = params["shadow_color"]
        self.shadow_blur = params["shadow_blur"]
        self.shadow_offset = params["shadow_offset"]

        self.state_layer_color = params["state_layer_color"]
        self._HOVER_OPACITY = params["hover_opacity"]
        self._PRESS_OPACITY = params["pressed_opacity"]
        self.border_color = params["border_color"]
        self.invalidate()


class TextButton(MaterialButtonBase):
    """Text button: no background, minimal padding, only overlay on press."""

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None = None,
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
        alignment: Union[str, Tuple[str, str]] = "center",
        style: Optional[ButtonStyle] = None,
    ):
        """Initialize TextButton.

        Args:
            label: Text label for the button.
            icon: Icon for the button.
            on_click: Callback to be invoked when the button is clicked.
            disabled: Whether the button is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding specification.
            alignment: Content alignment.
            style: Custom ButtonStyle.
        """
        self._variant = "text"
        self._user_style = style
        self._user_padding = padding
        self._user_height = height

        effective_style = self.style
        text_color = effective_style.foreground if effective_style else ColorRole.PRIMARY

        height_px = _coerce_fixed_height_px(height)

        child_widget = build_button_child(
            label=label,
            icon=icon,
            foreground=text_color,
            button_height=height_px,
            style=effective_style,
        )

        params = resolve_button_style_params(effective_style, padding, height, disabled)

        super().__init__(
            child=child_widget,
            on_click=on_click,
            width=width,
            disabled=disabled,
            alignment=alignment,
            **params,
        )

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.theme.manager import manager

        manager.subscribe(self._on_theme_change)

    def on_unmount(self) -> None:
        from nuiitivet.theme.manager import manager

        manager.unsubscribe(self._on_theme_change)
        super().on_unmount()

    def _on_theme_change(self, theme) -> None:
        params = resolve_button_style_params(
            self.style,
            self._user_padding,
            self._user_height,
            self.disabled,
        )

        # Update properties
        self.bgcolor = params["background_color"]
        self.padding = params["padding"]
        self.corner_radius = params["corner_radius"]
        self.shadow_color = params["shadow_color"]
        self.shadow_blur = params["shadow_blur"]
        self.shadow_offset = params["shadow_offset"]

        self.state_layer_color = params["state_layer_color"]
        self._HOVER_OPACITY = params["hover_opacity"]
        self._PRESS_OPACITY = params["pressed_opacity"]

        self.invalidate()


class ElevatedButton(MaterialButtonBase):
    """Elevated button: has surface background and elevation (shadow)."""

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None = None,
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
        style: Optional[ButtonStyle] = None,
    ):
        """Initialize ElevatedButton.

        Args:
            label: Text label for the button.
            icon: Icon for the button.
            on_click: Callback to be invoked when the button is clicked.
            disabled: Whether the button is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding specification.
            style: Custom ButtonStyle.
        """
        self._variant = "elevated"
        self._user_style = style
        self._user_padding = padding
        self._user_height = height

        effective_style = self.style
        text_color = effective_style.foreground if effective_style else ColorRole.ON_SURFACE

        height_px = _coerce_fixed_height_px(height)

        child_widget = build_button_child(
            label=label,
            icon=icon,
            foreground=text_color,
            button_height=height_px,
            style=effective_style,
        )

        params = resolve_button_style_params(effective_style, padding, height, disabled)

        super().__init__(
            child=child_widget,
            on_click=on_click,
            width=width,
            disabled=disabled,
            **params,
        )

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.theme.manager import manager

        manager.subscribe(self._on_theme_change)

    def on_unmount(self) -> None:
        from nuiitivet.theme.manager import manager

        manager.unsubscribe(self._on_theme_change)
        super().on_unmount()

    def _on_theme_change(self, theme) -> None:
        params = resolve_button_style_params(
            self.style,
            self._user_padding,
            self._user_height,
            self.disabled,
        )

        # Update properties
        self.bgcolor = params["background_color"]
        self.padding = params["padding"]
        self.corner_radius = params["corner_radius"]
        self.shadow_color = params["shadow_color"]
        self.shadow_blur = params["shadow_blur"]
        self.shadow_offset = params["shadow_offset"]

        self.state_layer_color = params["state_layer_color"]
        self._HOVER_OPACITY = params["hover_opacity"]
        self._PRESS_OPACITY = params["pressed_opacity"]
        self.invalidate()


class FilledTonalButton(MaterialButtonBase):
    """Filled tonal button: uses surfaceVariant background and onSurfaceVariant text."""

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None = None,
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
        style: Optional[ButtonStyle] = None,
    ):
        """Initialize FilledTonalButton.

        Args:
            label: Text label for the button.
            icon: Icon for the button.
            on_click: Callback to be invoked when the button is clicked.
            disabled: Whether the button is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding specification.
            style: Custom ButtonStyle.
        """
        self._variant = "tonal"
        self._user_style = style
        self._user_padding = padding
        self._user_height = height

        effective_style = self.style
        text_color = effective_style.foreground if effective_style else ColorRole.ON_SURFACE_VARIANT

        height_px = _coerce_fixed_height_px(height)

        child_widget = build_button_child(
            label=label,
            icon=icon,
            foreground=text_color,
            button_height=height_px,
            style=effective_style,
        )

        params = resolve_button_style_params(effective_style, padding, height, disabled)

        super().__init__(
            child=child_widget,
            on_click=on_click,
            width=width,
            disabled=disabled,
            **params,
        )

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.theme.manager import manager

        manager.subscribe(self._on_theme_change)

    def on_unmount(self) -> None:
        from nuiitivet.theme.manager import manager

        manager.unsubscribe(self._on_theme_change)
        super().on_unmount()

    def _on_theme_change(self, theme) -> None:
        params = resolve_button_style_params(
            self.style,
            self._user_padding,
            self._user_height,
            self.disabled,
        )

        # Update properties
        self.bgcolor = params["background_color"]
        self.padding = params["padding"]
        self.corner_radius = params["corner_radius"]
        self.shadow_color = params["shadow_color"]
        self.shadow_blur = params["shadow_blur"]
        self.shadow_offset = params["shadow_offset"]

        self.state_layer_color = params["state_layer_color"]
        self._HOVER_OPACITY = params["hover_opacity"]
        self._PRESS_OPACITY = params["pressed_opacity"]
        self.invalidate()


class FloatingActionButton(MaterialButtonBase):
    """Minimal Floating Action Button (rectangular for now)."""

    def __init__(
        self,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str],
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        size: int = 56,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
        style: Optional[ButtonStyle] = None,
    ):
        """Initialize FloatingActionButton.

        Args:
            icon: Icon for the button.
            on_click: Callback to be invoked when the button is clicked.
            disabled: Whether the button is disabled.
            size: Size of the FAB (width and height).
            padding: Padding specification.
            style: Custom ButtonStyle.
        """
        self._variant = "fab"
        self._user_style = style
        self._user_padding = padding
        self._user_height = size

        effective_style = self.style
        text_color = effective_style.foreground if effective_style else ColorRole.ON_PRIMARY

        child_widget = build_button_child(
            None,
            icon,
            foreground=text_color,
            button_height=size,
            style=effective_style,
        )

        params = resolve_button_style_params(effective_style, padding, size, disabled)

        super().__init__(
            child=child_widget,
            on_click=on_click,
            width=size,
            disabled=disabled,
            **params,
        )

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.theme.manager import manager

        manager.subscribe(self._on_theme_change)

    def on_unmount(self) -> None:
        from nuiitivet.theme.manager import manager

        manager.unsubscribe(self._on_theme_change)
        super().on_unmount()

    def _on_theme_change(self, theme) -> None:
        params = resolve_button_style_params(
            self.style,
            self._user_padding,
            self._user_height,
            self.disabled,
        )

        # Update properties
        self.bgcolor = params["background_color"]
        self.padding = params["padding"]
        self.corner_radius = params["corner_radius"]
        self.shadow_color = params["shadow_color"]
        self.shadow_blur = params["shadow_blur"]
        self.shadow_offset = params["shadow_offset"]

        self.state_layer_color = params["state_layer_color"]
        self._HOVER_OPACITY = params["hover_opacity"]
        self._PRESS_OPACITY = params["pressed_opacity"]
        self.invalidate()
