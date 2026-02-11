import math
import logging
from typing import Callable, Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from ..rendering.skia.paint_cache import CachedPaintMixin
from ..widgeting.widget import Widget
from ..theme.types import ColorSpec
from ..theme.manager import manager as theme_manager
from ..rendering.background_renderer import BackgroundRenderer
from ..rendering.skia.geometry import clip_round_rect, make_rect
from ..rendering.sizing import SizingLike
from ..layout.layout_engine import LayoutEngine
from ..layout.alignment import normalize_alignment
from ..layout.measure import preferred_size as measure_preferred_size
from ..widgeting.modifier import Modifier
from nuiitivet.observable.protocols import ReadOnlyObservableProtocol


_logger = logging.getLogger(__name__)


class Box(CachedPaintMixin, Widget):
    """(Advanced) Low-level drawing primitive.

    Note:
        Prefer using Modifiers (e.g. `.background()`, `.border()`, `.shadow()`)
        on a `Container` or other widgets. This widget is used internally
        to implement those modifiers.

    A widget that draws a box with optional background, border, and shadow.
    """

    def __init__(
        self,
        child: Optional[Widget] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        # Visual properties
        background_color: Optional[ColorSpec] = None,
        border_width: float = 0,
        border_color: Optional[ColorSpec] = None,
        corner_radius: Union[float, Tuple[float, float, float, float]] = 0,
        shadow_blur: float = 0,
        shadow_color: Optional[ColorSpec] = None,
        shadow_offset: Tuple[float, float] = (0, 0),
        # Alignment for the child (if present)
        alignment: Union[str, Tuple[str, str]] = "center",
    ):
        super().__init__(width=width, height=height, padding=padding)
        self._theme_state_ready = False
        self._bgcolor: Optional[ColorSpec] = None
        self._border_color: Optional[ColorSpec] = None
        self._shadow_color: Optional[ColorSpec] = None
        self._box_theme_subscription: Optional[Callable[[object], None]] = None
        if child:
            self.add_child(child)

        self.bgcolor = background_color
        self.border_width = border_width
        self.border_color = border_color
        self.corner_radius = corner_radius
        self.shadow_blur = shadow_blur
        self.shadow_color = shadow_color
        self.shadow_offset = shadow_offset
        self.alignment = alignment
        self.clip_content = False

        self._theme_state_ready = True
        self._sync_theme_subscription()

        self._renderer = BackgroundRenderer(self)
        self._layout = LayoutEngine(self)

    @property
    def bgcolor(self) -> Optional[ColorSpec]:
        return self._bgcolor

    @bgcolor.setter
    def bgcolor(self, value: Union[Optional[ColorSpec], ReadOnlyObservableProtocol]) -> None:
        if isinstance(value, ReadOnlyObservableProtocol):
            self.observe(value, lambda v: setattr(self, "bgcolor", v))
            return
        self._bgcolor = value
        self._handle_visual_state_change()

    @property
    def border_color(self) -> Optional[ColorSpec]:
        return self._border_color

    @border_color.setter
    def border_color(self, value: Union[Optional[ColorSpec], ReadOnlyObservableProtocol]) -> None:
        if isinstance(value, ReadOnlyObservableProtocol):
            self.observe(value, lambda v: setattr(self, "border_color", v))
            return
        self._border_color = value
        self._handle_visual_state_change()

    @property
    def shadow_color(self) -> Optional[ColorSpec]:
        return self._shadow_color

    @shadow_color.setter
    def shadow_color(self, value: Union[Optional[ColorSpec], ReadOnlyObservableProtocol]) -> None:
        if isinstance(value, ReadOnlyObservableProtocol):
            self.observe(value, lambda v: setattr(self, "shadow_color", v))
            return
        self._shadow_color = value
        self._handle_visual_state_change()

    @property
    def corner_radius(self) -> Union[float, Tuple[float, float, float, float]]:
        return getattr(self, "_corner_radius", 0)

    @corner_radius.setter
    def corner_radius(self, value: Union[float, Tuple[float, float, float, float], ReadOnlyObservableProtocol]) -> None:
        if isinstance(value, ReadOnlyObservableProtocol):
            self.observe(value, lambda v: setattr(self, "corner_radius", v))
            return
        self._corner_radius = value
        self._handle_visual_state_change()

    @property
    def border_width(self) -> float:
        return getattr(self, "_border_width", 0.0)

    @border_width.setter
    def border_width(self, value: Union[float, ReadOnlyObservableProtocol]) -> None:
        if isinstance(value, ReadOnlyObservableProtocol):
            self.observe(value, lambda v: setattr(self, "border_width", v))
            return
        self._border_width = float(value) if value is not None else 0.0
        self._handle_visual_state_change()

    @property
    def shadow_blur(self) -> float:
        return getattr(self, "_shadow_blur", 0.0)

    @shadow_blur.setter
    def shadow_blur(self, value: Union[float, ReadOnlyObservableProtocol]) -> None:
        if isinstance(value, ReadOnlyObservableProtocol):
            self.observe(value, lambda v: setattr(self, "shadow_blur", v))
            return
        self._shadow_blur = float(value) if value is not None else 0.0
        self._handle_visual_state_change()

    @property
    def shadow_offset(self) -> Tuple[float, float]:
        return getattr(self, "_shadow_offset", (0.0, 0.0))

    @shadow_offset.setter
    def shadow_offset(self, value: Union[Tuple[float, float], ReadOnlyObservableProtocol]) -> None:
        if isinstance(value, ReadOnlyObservableProtocol):
            self.observe(value, lambda v: setattr(self, "shadow_offset", v))
            return
        self._shadow_offset = value if value is not None else (0.0, 0.0)
        self._handle_visual_state_change()

    @property
    def corner_radii(self) -> Tuple[float, float, float, float]:
        cr = self.corner_radius
        try:
            if isinstance(cr, (list, tuple)):
                if len(cr) == 4:
                    return (float(cr[0]), float(cr[1]), float(cr[2]), float(cr[3]))
                else:
                    return (0.0, 0.0, 0.0, 0.0)
            else:
                v = float(cr or 0.0)
                return (v, v, v, v)
        except Exception:
            exception_once(_logger, "box_corner_radii_exc", "Failed to normalize corner radii")
            return (0.0, 0.0, 0.0, 0.0)

    @property
    def alignment(self) -> Union[str, Tuple[str, str]]:
        return getattr(self, "_align_raw", "center")

    @alignment.setter
    def alignment(self, value: Union[str, Tuple[str, str]]):
        self._align_raw = value
        self._align = normalize_alignment(value, default=("start", "start"))
        try:
            self._invalidate_layout_cache()
        except Exception:
            exception_once(_logger, "box_invalidate_layout_cache_exc", "Box layout cache invalidation failed")

    def on_mount(self) -> None:
        try:
            super().on_mount()
        except Exception:
            exception_once(_logger, "box_on_mount_super_exc", "Box on_mount super call failed")
        self._sync_theme_subscription()

    def on_unmount(self) -> None:
        self._remove_box_theme_subscription()
        try:
            super().on_unmount()
        except Exception:
            exception_once(_logger, "box_on_unmount_super_exc", "Box on_unmount super call failed")

    def hit_test(self, x: int, y: int):
        if self.clip_content:
            rect = self.last_rect
            if rect is None:
                return None
            rx, ry, rw, rh = rect
            if not (rx <= x <= rx + rw and ry <= y <= ry + rh):
                return None
        return super().hit_test(x, y)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        if not self.children:
            return

        child = self.children[0]
        # Calculate layout relative to self (0, 0)
        ix, iy, iw, ih = self._layout.compute_inner_rect(0, 0, width, height)
        cx, cy, child_w, child_h = self._layout.resolve_child_geometry(child, ix, iy, iw, ih)

        child.layout(child_w, child_h)
        child.set_layout_rect(cx, cy, child_w, child_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        self.set_last_rect(x, y, width, height)
        self.draw_background(canvas, x, y, width, height)
        self.draw_children(canvas, x, y, width, height)
        self.draw_border(canvas, x, y, width, height)

    def draw_background(self, canvas, x: int, y: int, width: int, height: int):
        if canvas is None:
            return
        with self.paint_cache(canvas, x, y, width, height) as target:
            if target is self.PAINT_CACHE_SKIP or target is None:
                return
            self._renderer.paint_shadow_and_background(target, x, y, width, height)

    def draw_border(self, canvas, x: int, y: int, width: int, height: int):
        if canvas is None:
            return
        self._renderer.paint_border(canvas, x, y, width, height)

    def draw_children(self, canvas, x: int, y: int, width: int, height: int):
        if self.children and not getattr(self, "_suppress_child_paint", False):
            child = self.children[0]

            # Auto-layout fallback for tests or direct paint calls
            if child.layout_rect is None:
                self.layout(width, height)

            rect = child.layout_rect
            if rect:
                rel_x, rel_y, child_w, child_h = rect
                cx = x + rel_x
                cy = y + rel_y
            else:
                # Fallback if layout failed (should not happen)
                ix, iy, iw, ih = self._layout.compute_inner_rect(x, y, width, height)
                cx, cy, child_w, child_h = self._layout.resolve_child_geometry(child, ix, iy, iw, ih)

            child.set_last_rect(cx, cy, child_w, child_h)

            clip_saved = False
            if self.clip_content and canvas is not None:
                rect = make_rect(x, y, width, height)
                radii = list(self.corner_radii_pixels(width, height))
                try:
                    canvas.save()
                    if rect is not None and clip_round_rect(canvas, rect, radii, True):
                        clip_saved = True
                    else:
                        canvas.restore()
                except Exception:
                    try:
                        if not clip_saved:
                            canvas.restore()
                    except Exception:
                        exception_once(_logger, "box_clip_restore_exc", "Box clip save/restore failed")

            try:
                child.paint(canvas, cx, cy, child_w, child_h)
            finally:
                if clip_saved:
                    try:
                        canvas.restore()
                    except Exception:
                        exception_once(_logger, "box_clip_restore_exc", "Box clip save/restore failed")

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        child_max_w: Optional[int] = None
        child_max_h: Optional[int] = None

        w_dim = self.width_sizing
        h_dim = self.height_sizing

        if w_dim.kind == "fixed":
            resolved_w = int(w_dim.value)
            child_max_w = resolved_w
        elif max_width is not None:
            child_max_w = int(max_width)

        if h_dim.kind == "fixed":
            resolved_h = int(h_dim.value)
            child_max_h = resolved_h
        elif max_height is not None:
            child_max_h = int(max_height)

        if child_max_w is not None or child_max_h is not None:
            pad = self.padding
            border_w = int(getattr(self, "border_width", 0) or 0)
            if child_max_w is not None:
                child_max_w = max(0, int(child_max_w) - int(pad[0]) - int(pad[2]) - border_w * 2)
            if child_max_h is not None:
                child_max_h = max(0, int(child_max_h) - int(pad[1]) - int(pad[3]) - border_w * 2)

        if self.children:
            cw, ch = measure_preferred_size(self.children[0], max_width=child_max_w, max_height=child_max_h)
        else:
            cw, ch = 0, 0

        # Calculate natural size based on child + padding/border
        layout_w, layout_h = self._layout.preferred_size(cw, ch)

        if w_dim.kind == "fixed":
            w = int(w_dim.value)
        else:
            w = int(layout_w)
            if max_width is not None:
                w = min(w, int(max_width))

        if h_dim.kind == "fixed":
            h = int(h_dim.value)
        else:
            h = int(layout_h)
            if max_height is not None:
                h = min(h, int(max_height))

        return w, h

    def corner_radii_pixels(self, width: int, height: int) -> Tuple[float, float, float, float]:
        """Return the resolved corner radii in pixels for the given size."""
        return self._renderer.corner_radii_pixels(width, height)

    def paint_outsets(self) -> Tuple[int, int, int, int]:
        base_left, base_top, base_right, base_bottom = super().paint_outsets()
        shadow_left, shadow_top, shadow_right, shadow_bottom = self._shadow_paint_outsets()
        return (
            base_left + shadow_left,
            base_top + shadow_top,
            base_right + shadow_right,
            base_bottom + shadow_bottom,
        )

    def _shadow_paint_outsets(self) -> Tuple[int, int, int, int]:
        color = getattr(self, "shadow_color", None)
        if color is None:
            return (0, 0, 0, 0)
        try:
            blur = float(getattr(self, "shadow_blur", 0.0) or 0.0)
        except Exception:
            exception_once(_logger, "box_shadow_blur_float_exc", "Failed to coerce shadow_blur to float")
            blur = 0.0
        try:
            dx, dy = getattr(self, "shadow_offset", (0.0, 0.0))
        except Exception:
            exception_once(_logger, "box_shadow_offset_unpack_exc", "Failed to read shadow_offset")
            dx = dy = 0.0

        def _component(val: float) -> int:
            return int(math.ceil(max(0.0, val)))

        blur_pad = 0.0
        if blur > 0.0:
            blur_pad = float(max(4.0, blur * 3.0))

        left = blur_pad + max(0.0, -float(dx))
        right = blur_pad + max(0.0, float(dx))
        top = blur_pad + max(0.0, -float(dy))
        bottom = blur_pad + max(0.0, float(dy))
        return (_component(left), _component(top), _component(right), _component(bottom))

    def _handle_visual_state_change(self) -> None:
        if not getattr(self, "_theme_state_ready", False):
            return
        self._sync_theme_subscription()
        try:
            self.invalidate_paint_cache()
        except Exception:
            exception_once(_logger, "box_invalidate_paint_cache_exc", "invalidate_paint_cache failed")

    def _uses_theme_colors(self) -> bool:
        return any(
            self._value_uses_theme_color(value) for value in (self._bgcolor, self._border_color, self._shadow_color)
        )

    @staticmethod
    def _value_uses_theme_color(value: Optional[ColorSpec]) -> bool:
        if value is None:
            return False
        # Check if value is a primitive color type (str, int, tuple of int/float)
        if isinstance(value, (str, int)):
            return False
        if isinstance(value, tuple):
            # Check if it's a tuple of primitives (RGB, RGBA, Hex+Alpha)
            if all(isinstance(v, (int, float, str)) for v in value):
                return False
            # If tuple contains non-primitives (like ColorRole), it's a theme color
            return True
        # If it's not a primitive type, assume it's a theme color (e.g. ColorRole enum)
        return True

    def _sync_theme_subscription(self) -> None:
        if not getattr(self, "_theme_state_ready", False):
            return
        if not self._uses_theme_colors():
            self._remove_box_theme_subscription()
            return
        self._ensure_box_theme_subscription()

    def _ensure_box_theme_subscription(self) -> None:
        if self._box_theme_subscription is not None:
            return

        def _callback(theme) -> None:
            self._handle_theme_change(theme)

        try:
            theme_manager.subscribe(_callback)
            self._box_theme_subscription = _callback
        except Exception:
            exception_once(_logger, "box_theme_subscribe_exc", "Theme subscribe failed")
            self._box_theme_subscription = None

    def _remove_box_theme_subscription(self) -> None:
        callback = self._box_theme_subscription
        if callback is None:
            return
        try:
            theme_manager.unsubscribe(callback)
        except Exception:
            exception_once(_logger, "box_theme_unsubscribe_exc", "Theme unsubscribe failed")
        self._box_theme_subscription = None

    def _handle_theme_change(self, _theme) -> None:
        try:
            self.invalidate_paint_cache()
        except Exception:
            exception_once(_logger, "box_theme_change_invalidate_paint_cache_exc", "invalidate_paint_cache failed")


class ModifierBox(Box):
    """A specialized Box used by Modifiers to allow property merging.

    If a Modifier is applied to a ModifierBox, it can safely merge its properties
    instead of wrapping it in a new Box, because ModifierBox is known to be
    a purely decorative wrapper created by the framework, not a user-defined widget.
    """

    def __init__(self, *args, modifier: Optional[Modifier] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._modifier_chain = modifier or Modifier()

        # Preserve cross-axis alignment override across modifier wrapping.
        child = self.children[0] if self.children else None
        if child is not None:
            try:
                self.cross_align = child.cross_align
            except Exception:
                exception_once(_logger, "modifier_box_cross_align_copy_exc", "Failed to copy child.cross_align")
