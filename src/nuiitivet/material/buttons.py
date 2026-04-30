"""Material Design 3 Buttons.

This module contains the unified Material Design 3 button widgets:

- :class:`Button` -- standard push button. Visual variant and size are
  driven through :class:`ButtonStyle` presets
  (``ButtonStyle.filled("s")``, ``ButtonStyle.outlined("m")`` etc.).
- :class:`ToggleButton` -- toggle variant backed by
  :class:`ToggleButtonStyle` that carries both selected and unselected
  state tokens.
- :class:`IconButton`, :class:`IconToggleButton` -- icon-only variants.
- :class:`Fab` -- Floating Action Button.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Tuple, Type, Union, TYPE_CHECKING, cast

from nuiitivet.common.logging_once import debug_once, exception_once
from nuiitivet.observable import ObservableProtocol, ReadOnlyObservableProtocol
from nuiitivet.animation import Animatable, LinearMotion, RgbaTupleConverter
from nuiitivet.material.motion import EXPRESSIVE_FAST_SPATIAL
from nuiitivet.material.styles.button_style import ButtonStyle, IconButtonStyle, IconToggleButtonStyle
from nuiitivet.material.styles.fab_style import FabStyle
from nuiitivet.material.styles.toggle_button_style import ToggleButtonStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.theme.types import ColorSpec
from nuiitivet.rendering.elevation import resolve_shadow_params
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia.color import make_opacity_paint
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.material.symbols import Symbol

logger = logging.getLogger(__name__)


_STATE_LAYER_MOTION = LinearMotion(0.1)
_COLOR_MOTION = LinearMotion(0.15)

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


def _resolve_color_rgba(value: ColorSpec) -> Tuple[int, int, int, int]:
    from nuiitivet.theme.manager import manager
    from nuiitivet.theme.resolver import resolve_color_to_rgba

    return resolve_color_to_rgba(value, theme=manager.current)


def _shadow_from_elevation(elevation_val: Optional[float]) -> tuple[ColorSpec, float, tuple[float, float]]:
    shadow_color = None
    shadow_blur = 0.0
    shadow_offset: tuple[float, float] = (0.0, 0.0)

    if elevation_val is None or elevation_val <= 0.0:
        return shadow_color, shadow_blur, shadow_offset

    shadow = resolve_shadow_params(float(elevation_val))
    shadow_color = (ColorRole.SHADOW, shadow.alpha)
    shadow_offset = shadow.offset
    shadow_blur = shadow.blur

    return shadow_color, shadow_blur, shadow_offset


_RGBA_CONVERTER = RgbaTupleConverter()


def make_child_from_label(
    label: Any,
    foreground: ColorSpec = ColorRole.ON_SURFACE,
    font_size: int = 14,
) -> Any:
    """Return a Material ``Text`` widget for the given label.

    Args:
        label: Label source (string, observable, etc.).
        foreground: Foreground colour role for the label.
        font_size: Label font size in dp (M3 size token derived).
    """
    # Local import to avoid circular imports at module import time.
    from nuiitivet.material.text import Text
    from nuiitivet.material.styles.text_style import TextStyle

    # Material button label is always rendered via Material Text.
    return Text(label, style=TextStyle(color=foreground, font_size=font_size, text_alignment="center"))


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

        if style is not None and getattr(style, "icon_size", None):
            size_px = int(style.icon_size)
        else:
            size_px = _m3_icon_size_for_height(base_height)
        icon_widget = Icon(icon, size=size_px, style=IconStyle(color=foreground))
    text_widget: Any = None
    if label is not None:
        label_font_size = 14
        if style is not None and getattr(style, "label_font_size", None):
            label_font_size = int(style.label_font_size)
        text_widget = make_child_from_label(label, foreground, font_size=label_font_size)
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
    fg = None

    if style is not None:
        bg = style.background
        if pad is None:
            pad = style.padding
        cr = style.corner_radius
        bc = getattr(style, "border_color", None)
        bw = getattr(style, "border_width", 0.0) or 0.0
        fg = getattr(style, "foreground", None)

    if pad is None:
        pad = 0

    # Keep height auto by default.
    # Minimum touch target is enforced by MaterialButtonBase.preferred_size.

    # Elevation -> Shadow
    shadow_color = None
    shadow_blur = 0.0
    shadow_offset: tuple[float, float] = (0.0, 0.0)

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
        shadow_color, shadow_blur, shadow_offset = _shadow_from_elevation(elevation_val)

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
        "foreground_color": fg,
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

        # Default fallback (no user style, no explicit variant resolution).
        return ButtonStyle.filled("s")

    def __init__(
        self,
        child: Widget,
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int, int, int]] = 0,
        background_color: ColorSpec = None,
        foreground_color: ColorSpec = None,
        border_color: ColorSpec = None,
        border_width: float = 0.0,
        corner_radius: Union[float, Tuple[float, float, float, float]] = 0.0,
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
            background_color: Button container color.
            foreground_color: Button foreground color (text/icon).
            border_color: Border color for outlined buttons.
            border_width: Border width for outlined buttons.
            corner_radius: Corner radius for the button container.
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
            background_color=background_color,
            border_color=border_color,
            border_width=border_width,
            corner_radius=corner_radius,
            state_layer_color=state_layer_color,
            **kwargs,
        )

        # Instance-level customization of opacities for InteractiveWidget
        self._HOVER_OPACITY = hover_opacity
        self._PRESS_OPACITY = pressed_opacity
        self._DRAG_OPACITY = drag_opacity

        self.disabled_opacity = disabled_opacity

        self._state_layer_anim: Animatable[float] = Animatable(0.0, motion=_STATE_LAYER_MOTION)
        self.bind(self._state_layer_anim.subscribe(lambda _: self.invalidate()))

        self._foreground_targets: list[Widget] = []
        self._bg_color_anim: Optional[Animatable[Tuple[int, int, int, int]]] = None
        self._border_color_anim: Optional[Animatable[Tuple[int, int, int, int]]] = None
        self._foreground_color_anim: Optional[Animatable[Tuple[int, int, int, int]]] = None

        self._init_foreground_targets()
        self._update_color_targets(
            background_color=background_color,
            border_color=border_color,
            foreground_color=foreground_color,
        )

    def on_unmount(self) -> None:
        self._dispose_color_animations()
        super().on_unmount()

    def _init_foreground_targets(self) -> None:
        if self._foreground_targets:
            return

        from nuiitivet.widgets.text import TextBase

        try:
            from nuiitivet.material.icon import Icon
        except Exception:
            Icon = None  # type: ignore

        def _walk(widget: Widget) -> None:
            if isinstance(widget, TextBase):
                self._foreground_targets.append(widget)
                return
            if Icon is not None and isinstance(widget, Icon):
                self._foreground_targets.append(widget)
                return
            for child in widget.children_snapshot():
                if isinstance(child, Widget):
                    _walk(child)

        for child in self.children_snapshot():
            if isinstance(child, Widget):
                _walk(child)

    def _apply_foreground_rgba(self, rgba: Tuple[int, int, int, int]) -> None:
        from nuiitivet.widgets.text import TextBase

        for widget in self._foreground_targets:
            if isinstance(widget, TextBase):
                try:
                    text_style: Any = widget._style if getattr(widget, "_style", None) is not None else widget.style
                    widget._style = text_style.copy_with(color=rgba)
                    widget.invalidate()
                except Exception:
                    continue
                continue

            try:
                from nuiitivet.material.icon import Icon
            except Exception:
                Icon = None  # type: ignore

            if Icon is not None and isinstance(widget, Icon):
                try:
                    icon_style: Any = widget._style if getattr(widget, "_style", None) is not None else widget.style
                    widget._style = icon_style.copy_with(color=rgba)
                    widget.invalidate()
                except Exception:
                    continue

    def _update_color_targets(
        self,
        *,
        background_color: ColorSpec,
        border_color: ColorSpec,
        foreground_color: ColorSpec,
    ) -> None:
        resolved_bg = _resolve_color_rgba(background_color)
        resolved_border = _resolve_color_rgba(border_color)
        resolved_fg = _resolve_color_rgba(foreground_color)

        if self._bg_color_anim is None:
            self._bg_color_anim = Animatable.vector(
                resolved_bg,
                _RGBA_CONVERTER,
                motion=_COLOR_MOTION,
            )
            self.bind(self._bg_color_anim.subscribe(lambda rgba: setattr(self, "bgcolor", rgba)))
        else:
            self._bg_color_anim.target = resolved_bg

        if self._border_color_anim is None:
            self._border_color_anim = Animatable.vector(
                resolved_border,
                _RGBA_CONVERTER,
                motion=_COLOR_MOTION,
            )
            self.bind(self._border_color_anim.subscribe(lambda rgba: setattr(self, "border_color", rgba)))
        else:
            self._border_color_anim.target = resolved_border

        if self._foreground_color_anim is None:
            self._foreground_color_anim = Animatable.vector(resolved_fg, _RGBA_CONVERTER, motion=_COLOR_MOTION)
            self.bind(self._foreground_color_anim.subscribe(self._apply_foreground_rgba))
        else:
            self._foreground_color_anim.target = resolved_fg

    def _dispose_color_animations(self) -> None:
        if self._bg_color_anim is not None:
            self._bg_color_anim = None
        if self._border_color_anim is not None:
            self._border_color_anim = None
        if self._foreground_color_anim is not None:
            self._foreground_color_anim = None

    def _apply_style_params(self, params: dict[str, Any]) -> None:
        self.padding = params["padding"]
        self.corner_radius = params["corner_radius"]
        self.border_width = params["border_width"]
        self.shadow_color = params["shadow_color"]
        self.shadow_blur = params["shadow_blur"]
        self.shadow_offset = params["shadow_offset"]

        self.state_layer_color = params["state_layer_color"]
        self._HOVER_OPACITY = params["hover_opacity"]
        self._PRESS_OPACITY = params["pressed_opacity"]
        self._DRAG_OPACITY = params["drag_opacity"]

        self._update_color_targets(
            background_color=params["background_color"],
            border_color=params["border_color"],
            foreground_color=params["foreground_color"],
        )
        self.invalidate()

    def _get_state_layer_target_opacity(self) -> float:
        state = self.state
        if state.dragging:
            return float(self._DRAG_OPACITY)
        if state.pressed:
            return float(self._PRESS_OPACITY)
        if state.hovered:
            return float(self._HOVER_OPACITY)
        return 0.0

    def _get_active_state_layer_opacity(self) -> float:
        target = self._get_state_layer_target_opacity()
        if abs(self._state_layer_anim.target - target) > 1e-6:
            self._state_layer_anim.target = target
        return float(self._state_layer_anim.value)

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


class Button(MaterialButtonBase):
    """Unified Material Design 3 button.

    The visual variant (filled, outlined, text, elevated, tonal) and the
    M3 size preset (``"xs"``..``"xl"``) are both expressed through the
    ``style`` argument, which accepts any :class:`ButtonStyle` instance.
    Use the :class:`ButtonStyle` factory methods to obtain variant presets:
    ``ButtonStyle.filled("s")``, ``ButtonStyle.outlined("m")`` and so on.

    When ``style`` is not provided, :meth:`ButtonStyle.filled` with size
    ``"s"`` is used as the default.
    """

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
        """Initialize Button.

        Args:
            label: Text label for the button.
            icon: Icon glyph for the button (Symbol, string, or observable).
            on_click: Callback invoked when the button is clicked.
            disabled: Whether the button is disabled.
            width: Width specification. Defaults to auto.
            height: Height specification. Defaults to auto.
            padding: Padding override; ``None`` delegates to ``style.padding``.
            style: Visual style preset. Defaults to ``ButtonStyle.filled("s")``.
        """
        effective_style = style if style is not None else ButtonStyle.filled("s")
        self._user_style = effective_style
        self._user_padding = padding
        self._user_height = height

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
        self._on_theme_change(manager.current)

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
        self._apply_style_params(params)


class IconButton(MaterialButtonBase):
    """Material icon-only action button driven by style presets."""

    def __init__(
        self,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str],
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        style: Optional[ButtonStyle] = None,
    ):
        """Initialize IconButton.

        Args:
            icon: Icon glyph source.
            on_click: Callback invoked when the button is clicked.
            disabled: Whether the button is disabled.
            style: Icon button style preset or custom style.  Defaults to
                :meth:`IconButtonStyle.standard` (size ``"s"``, 40dp).  Use
                size-aware factories such as ``IconButtonStyle.filled("m")``
                to control container/icon sizing.
        """
        effective_style = style if style is not None else IconButtonStyle.standard()

        self._user_style = effective_style
        self._user_padding = None
        self._user_height = effective_style.container_height

        child_widget = build_button_child(
            label=None,
            icon=icon,
            foreground=effective_style.foreground if effective_style else ColorRole.ON_SURFACE,
            button_height=effective_style.container_height,
            style=effective_style,
        )

        params = resolve_button_style_params(effective_style, None, effective_style.container_height, disabled)
        super().__init__(
            child=child_widget,
            on_click=on_click,
            width=effective_style.container_height,
            disabled=disabled,
            **params,
        )

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.theme.manager import manager

        manager.subscribe(self._on_theme_change)
        self._on_theme_change(manager.current)

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
        self._apply_style_params(params)


class ToggleButtonBase(MaterialButtonBase):
    """Internal base class for toggle buttons.

    Manages ``selected`` state (internal flag or external observable) and
    wires the widget state layer to it.  Subclasses must override
    :meth:`_resolve_style_for_selected` to supply the concrete
    :class:`ButtonStyle` for the current state.
    """

    @property
    def selected(self) -> bool:
        """Return current selected state."""
        if self._selected_external is not None:
            return bool(self._selected_external.value)
        return bool(self._selected_internal)

    @selected.setter
    def selected(self, new_value: bool) -> None:
        if self._selected_external is not None:
            try:
                self._selected_external.value = bool(new_value)
            except Exception:
                pass
            return
        self._selected_internal = bool(new_value)

    @property
    def style(self) -> ButtonStyle:
        """Return the :class:`ButtonStyle` for the current selected state."""
        return self._resolve_style_for_selected(self.selected)

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None = None,
        *,
        selected: bool | ObservableProtocol[bool] = False,
        on_change: Optional[Callable[[bool], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
    ):
        """Initialize the base toggle button.

        Args:
            label: Text label for the button.
            icon: Icon glyph for the button.
            selected: Initial selected state or external observable.
            on_change: Callback invoked with the new selected value.
            disabled: Whether the button is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding override.
        """
        self._user_padding = padding
        self._user_height = height
        self.on_change = on_change

        self._selected_external: ObservableProtocol[bool] | None = None
        if hasattr(selected, "subscribe") and hasattr(selected, "value"):
            self._selected_external = cast("ObservableProtocol[bool]", selected)
            self._selected_internal = bool(self._selected_external.value)
        else:
            self._selected_internal = bool(selected)

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

        params = resolve_button_style_params(
            effective_style,
            padding,
            height,
            disabled,
        )

        super().__init__(
            child=child_widget,
            on_click=self._handle_toggle,
            width=width,
            disabled=disabled,
            **params,
        )

        self.state.checked = self.selected

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.theme.manager import manager

        manager.subscribe(self._on_theme_change)
        self._on_theme_change(manager.current)

        if self._selected_external is not None:
            self.observe(self._selected_external, self._on_selected_external_change)
            self._sync_selected_state()

    def on_unmount(self) -> None:
        from nuiitivet.theme.manager import manager

        manager.unsubscribe(self._on_theme_change)
        super().on_unmount()

    def _resolve_style_for_selected(self, selected: bool) -> ButtonStyle:
        """Return the :class:`ButtonStyle` to apply for the given state.

        Subclasses must override this method.
        """
        raise NotImplementedError

    def _on_theme_change(self, theme) -> None:
        params = resolve_button_style_params(
            self.style,
            self._user_padding,
            self._user_height,
            self.disabled,
        )
        self._apply_style_params(params)

    def _on_selected_external_change(self, _new_value: bool) -> None:
        self._sync_selected_state()

    def _sync_selected_state(self) -> None:
        self.state.checked = self.selected
        self._on_theme_change(None)
        self.invalidate()

    def _handle_toggle(self) -> None:
        if self.disabled:
            return

        new_value = not self.selected
        self.selected = new_value
        self._sync_selected_state()

        if self.on_change is not None:
            self.on_change(new_value)


class ToggleButton(ToggleButtonBase):
    """Unified Material Design 3 toggle button.

    Visual variant and size are encoded in a :class:`ToggleButtonStyle`
    which carries both unselected- and selected-state colours.  Use
    :meth:`ToggleButtonStyle.filled`, ``.outlined``, ``.elevated`` or
    ``.tonal`` to obtain presets.  When ``style`` is ``None``, the style
    defaults to :meth:`ToggleButtonStyle.filled` at size ``"s"``.
    """

    def __init__(
        self,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str] | None = None,
        *,
        selected: bool | ObservableProtocol[bool] = False,
        on_change: Optional[Callable[[bool], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
        style: Optional[ToggleButtonStyle] = None,
    ):
        """Initialize ToggleButton.

        Args:
            label: Text label for the button.
            icon: Icon glyph for the button.
            selected: Initial selected state or external observable.
            on_change: Callback invoked with the new selected value.
            disabled: Whether the button is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding override; ``None`` uses ``style.padding``.
            style: Toggle style preset. Defaults to ``ToggleButtonStyle.filled("s")``.
        """
        self._toggle_style = style if style is not None else ToggleButtonStyle.filled("s")

        super().__init__(
            label=label,
            icon=icon,
            selected=selected,
            on_change=on_change,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
        )

    def _resolve_style_for_selected(self, selected: bool) -> ButtonStyle:
        return self._toggle_style.for_selected(selected)


class IconToggleButton(ToggleButtonBase):
    """Material icon-only toggle button driven by state-paired styles."""

    def __init__(
        self,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str],
        *,
        selected: bool | ObservableProtocol[bool] = False,
        on_change: Optional[Callable[[bool], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        style: Optional[IconToggleButtonStyle] = None,
    ):
        """Initialize IconToggleButton.

        Args:
            icon: Icon glyph source.
            selected: Selected state value or observable.
            on_change: Callback invoked with the new selected state.
            disabled: Whether the button is disabled.
            style: Toggle style pair for selected and unselected states.
                Defaults to :meth:`IconToggleButtonStyle.standard` (size
                ``"s"``).  Use size-aware factories such as
                ``IconToggleButtonStyle.filled("m")`` to control sizing.
        """
        self._icon_toggle_style = style if style is not None else IconToggleButtonStyle.standard()
        # Both selected/unselected share container_height per factory contract.
        self._icon_size = self._icon_toggle_style.unselected.container_height

        super().__init__(
            label=None,
            icon=icon,
            selected=selected,
            on_change=on_change,
            disabled=disabled,
            width=self._icon_size,
            height=self._icon_size,
            padding=0,
        )

    def _resolve_style_for_selected(self, selected: bool) -> ButtonStyle:
        return self._icon_toggle_style.selected if selected else self._icon_toggle_style.unselected


class Fab(MaterialButtonBase):
    """Material Design 3 Floating Action Button (FAB)."""

    def __init__(
        self,
        icon: "Symbol" | str | ReadOnlyObservableProtocol["Symbol"] | ReadOnlyObservableProtocol[str],
        *,
        on_click: Optional[Callable[[], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
        style: Optional[FabStyle] = None,
    ):
        """Initialize Fab.

        Args:
            icon: Icon for the button.
            on_click: Callback to be invoked when the button is clicked.
            disabled: Whether the button is disabled.
            padding: Padding specification.  When ``None``, ``style.padding``
                is used.
            style: FAB style preset.  Defaults to :meth:`FabStyle.primary`
                (size ``"s"``, 56dp).  Use ``FabStyle.primary("m")`` /
                ``FabStyle.primary("l")`` for the 80dp / 96dp variants, or
                ``FabStyle.secondary`` / ``FabStyle.tertiary`` for alternative
                tonal colour sets.
        """
        self._user_style: FabStyle = style if style is not None else FabStyle.primary()
        self._user_padding = padding
        size = self._user_style.container_height
        self._user_height = size

        effective_style = self.style
        text_color = effective_style.foreground if effective_style else ColorRole.ON_PRIMARY_CONTAINER

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
        self._sync_state_tokens()

        self._press_scale_x_anim: Animatable[float] = Animatable(1.0, motion=EXPRESSIVE_FAST_SPATIAL)
        self._press_scale_y_anim: Animatable[float] = Animatable(1.0, motion=EXPRESSIVE_FAST_SPATIAL)
        self.bind(self._press_scale_x_anim.subscribe(lambda _: self.invalidate()))
        self.bind(self._press_scale_y_anim.subscribe(lambda _: self.invalidate()))

    def on_mount(self) -> None:
        super().on_mount()
        from nuiitivet.theme.manager import manager

        manager.subscribe(self._on_theme_change)
        self._on_theme_change(manager.current)

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
        self._apply_style_params(params)
        self._sync_state_tokens()

    def _container_elevation(self) -> float:
        style = self.style
        if self.state.dragging or self.state.pressed:
            return float(getattr(style, "pressed_elevation", style.elevation) or 0.0)
        if self.state.hovered:
            return float(getattr(style, "hovered_elevation", style.elevation) or 0.0)
        if self.state.focused:
            return float(getattr(style, "focused_elevation", style.elevation) or 0.0)
        return float(getattr(style, "elevation", 0.0) or 0.0)

    def _sync_state_tokens(self) -> None:
        style = self.style

        focus_opacity = float(getattr(style, "focus_opacity", 0.1) or 0.0)
        hover_opacity = float(getattr(style, "hover_opacity", self._HOVER_OPACITY) or 0.0)
        pressed_opacity = float(getattr(style, "pressed_opacity", self._PRESS_OPACITY) or 0.0)

        self._FOCUS_OPACITY = focus_opacity
        self._HOVER_OPACITY = hover_opacity
        self._PRESS_OPACITY = pressed_opacity

        shadow_color, shadow_blur, shadow_offset = _shadow_from_elevation(self._container_elevation())
        if self.shadow_color != shadow_color:
            self.shadow_color = shadow_color
        if abs(float(self.shadow_blur) - float(shadow_blur)) > 1e-6:
            self.shadow_blur = shadow_blur
        if self.shadow_offset != shadow_offset:
            self.shadow_offset = shadow_offset

    def _get_state_layer_target_opacity(self) -> float:
        state = self.state
        if state.dragging:
            return float(self._DRAG_OPACITY)
        if state.pressed:
            return float(self._PRESS_OPACITY)
        if state.hovered:
            return float(self._HOVER_OPACITY)
        if state.focused:
            return float(self._FOCUS_OPACITY)
        return 0.0

    def _expressive_press_scale(self) -> tuple[float, float]:
        target = (0.94, 0.9) if self.state.pressed and not self.disabled else (1.0, 1.0)
        if abs(self._press_scale_x_anim.target - target[0]) > 1e-6:
            self._press_scale_x_anim.target = target[0]
        if abs(self._press_scale_y_anim.target - target[1]) > 1e-6:
            self._press_scale_y_anim.target = target[1]
        return float(self._press_scale_x_anim.value), float(self._press_scale_y_anim.value)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        self._sync_state_tokens()
        sx, sy = self._expressive_press_scale()
        if abs(sx - 1.0) < 1e-6 and abs(sy - 1.0) < 1e-6:
            super().paint(canvas, x, y, width, height)
            return

        if (
            canvas is None
            or not hasattr(canvas, "save")
            or not hasattr(canvas, "translate")
            or not hasattr(canvas, "scale")
        ):
            super().paint(canvas, x, y, width, height)
            return

        ox = float(x) + (float(width) / 2.0)
        oy = float(y) + (float(height) / 2.0)
        canvas.save()
        try:
            canvas.translate(ox, oy)
            canvas.scale(float(sx), float(sy))
            canvas.translate(-ox, -oy)
            super().paint(canvas, x, y, width, height)
        finally:
            canvas.restore()
