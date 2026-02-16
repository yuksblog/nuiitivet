from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import ReadOnlyObservableProtocol
from ..rendering.sizing import SizingLike
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget


logger = logging.getLogger(__name__)


AngleLike = Union[float, ReadOnlyObservableProtocol[float]]
ScaleLike = Union[float, Tuple[float, float], ReadOnlyObservableProtocol[float]]
TranslateLike = Union[Tuple[float, float], ReadOnlyObservableProtocol[Tuple[float, float]]]
OpacityLike = Union[float, ReadOnlyObservableProtocol[float]]
OriginLike = Union[str, Tuple[float, float]]


class TransformBox(Widget):
    """A wrapper widget that applies paint-only transforms to its child.

    Supports rotation, scale, translation, and opacity transforms.
    All transforms are paint-only: layout and hit-testing remain untransformed.

    This widget consolidates multiple transform operations into a single
    save/restore cycle for better performance.
    """

    _paint_dependencies = ("rotation", "scale_x", "scale_y", "translate_x", "translate_y", "opacity")

    def __init__(
        self,
        child: Widget,
        *,
        rotation: Optional[AngleLike] = None,
        scale: Optional[ScaleLike] = None,
        translation: Optional[TranslateLike] = None,
        opacity: Optional[OpacityLike] = None,
        transform_origin: OriginLike = "center",
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        super().__init__(width=width, height=height, max_children=1, overflow_policy="replace_last")
        self._transform_origin = transform_origin
        self._rotation: float = 0.0
        self._scale_x: float = 1.0
        self._scale_y: float = 1.0
        self._translate_x: float = 0.0
        self._translate_y: float = 0.0
        self._opacity: float = 1.0
        self._rotation_source: Optional[AngleLike] = None
        self._scale_source: Optional[ScaleLike] = None
        self._translation_source: Optional[TranslateLike] = None
        self._opacity_source: Optional[OpacityLike] = None
        self.add_child(child)

        if rotation is not None:
            self._bind_rotation(rotation)
        if scale is not None:
            self._bind_scale(scale)
        if translation is not None:
            self._bind_translation(translation)
        if opacity is not None:
            self._bind_opacity(opacity)

    def _child(self) -> Optional[Widget]:
        if not self.children:
            return None
        child = self.children[0]
        if isinstance(child, Widget):
            return child
        return None

    def _bind_rotation(self, rotation: AngleLike) -> None:
        self._rotation_source = rotation
        if isinstance(rotation, ReadOnlyObservableProtocol):
            try:
                self.observe(rotation, self._set_rotation)
                return
            except Exception:
                exception_once(
                    logger,
                    "transform_box_bind_rotation_exc",
                    "TransformBox failed to bind to rotation observable",
                )
        self._set_rotation(rotation)  # type: ignore[arg-type]

    def _set_rotation(self, value: float) -> None:
        try:
            self._rotation = float(value)
        except Exception:
            self._rotation = 0.0
        self.invalidate()

    def _bind_scale(self, scale: ScaleLike) -> None:
        self._scale_source = scale
        if isinstance(scale, ReadOnlyObservableProtocol):
            try:
                self.observe(scale, self._set_scale)
                return
            except Exception:
                exception_once(
                    logger,
                    "transform_box_bind_scale_exc",
                    "TransformBox failed to bind to scale observable",
                )
        self._set_scale(scale)  # type: ignore[arg-type]

    def _set_scale(self, value: Union[float, Tuple[float, float]]) -> None:
        try:
            if isinstance(value, (tuple, list)):
                sx, sy = value
                self._scale_x = float(sx)
                self._scale_y = float(sy)
            else:
                self._scale_x = self._scale_y = float(value)
        except Exception:
            self._scale_x = self._scale_y = 1.0
        self.invalidate()

    def _bind_translation(self, translation: TranslateLike) -> None:
        self._translation_source = translation
        if isinstance(translation, ReadOnlyObservableProtocol):
            try:
                self.observe(translation, self._set_translation)
                return
            except Exception:
                exception_once(
                    logger,
                    "transform_box_bind_translation_exc",
                    "TransformBox failed to bind to translation observable",
                )
        self._set_translation(translation)  # type: ignore[arg-type]

    def _set_translation(self, value: Tuple[float, float]) -> None:
        try:
            dx, dy = value
            self._translate_x = float(dx)
            self._translate_y = float(dy)
        except Exception:
            self._translate_x = self._translate_y = 0.0
        self.invalidate()

    def _bind_opacity(self, opacity: OpacityLike) -> None:
        self._opacity_source = opacity
        if isinstance(opacity, ReadOnlyObservableProtocol):
            try:
                self.observe(opacity, self._set_opacity)
                return
            except Exception:
                exception_once(
                    logger,
                    "transform_box_bind_opacity_exc",
                    "TransformBox failed to bind to opacity observable",
                )
        self._set_opacity(opacity)  # type: ignore[arg-type]

    def _set_opacity(self, value: float) -> None:
        try:
            self._opacity = max(0.0, min(1.0, float(value)))
        except Exception:
            self._opacity = 1.0
        self.invalidate()

    def on_mount(self) -> None:
        super().on_mount()
        bindings = getattr(self, "_bindings", None)
        if isinstance(bindings, list) and len(bindings) > 0:
            return

        if self._rotation_source is not None:
            self._bind_rotation(self._rotation_source)
        if self._scale_source is not None:
            self._bind_scale(self._scale_source)
        if self._translation_source is not None:
            self._bind_translation(self._translation_source)
        if self._opacity_source is not None:
            self._bind_opacity(self._opacity_source)

    def _resolve_origin(self, width: int, height: int) -> Tuple[float, float]:
        if isinstance(self._transform_origin, str):
            if self._transform_origin == "center":
                return (float(width) / 2.0, float(height) / 2.0)
            if self._transform_origin == "top_left":
                return (0.0, 0.0)
            if self._transform_origin == "top_right":
                return (float(width), 0.0)
            if self._transform_origin == "bottom_left":
                return (0.0, float(height))
            if self._transform_origin == "bottom_right":
                return (float(width), float(height))
            return (float(width) / 2.0, float(height) / 2.0)
        try:
            ox, oy = self._transform_origin
            return (float(ox), float(oy))
        except Exception:
            return (float(width) / 2.0, float(height) / 2.0)

    def _has_transforms(self) -> bool:
        """Check if any transforms are active."""
        return (
            self._rotation != 0.0
            or self._scale_x != 1.0
            or self._scale_y != 1.0
            or self._translate_x != 0.0
            or self._translate_y != 0.0
            or self._opacity != 1.0
        )

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        child = self._child()
        if child is None:
            return super().preferred_size(max_width=max_width, max_height=max_height)
        try:
            return child.preferred_size(max_width=max_width, max_height=max_height)
        except Exception:
            exception_once(logger, "transform_box_preferred_size_exc", "Child preferred_size raised")
            return super().preferred_size(max_width=max_width, max_height=max_height)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        child = self._child()
        if child is None:
            return
        try:
            child.layout(width, height)
            child.set_layout_rect(0, 0, width, height)
        except Exception:
            exception_once(logger, "transform_box_layout_exc", "Child layout/set_layout_rect raised")

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        child = self._child()
        if child is None:
            return

        if child.layout_rect is None:
            self.layout(width, height)

        # Fast path: no transforms
        if canvas is None or not self._has_transforms():
            try:
                child.set_last_rect(x, y, width, height)
                child.paint(canvas, x, y, width, height)
            except Exception:
                exception_once(logger, "transform_box_paint_no_transform_exc", "Child paint raised")
            return

        # Apply transforms
        ox, oy = self._resolve_origin(width, height)
        needs_opacity = self._opacity < 1.0
        try:
            canvas.save()
            # Apply opacity as a layer if needed
            if needs_opacity:
                try:
                    from ..rendering.skia.color import make_opacity_paint

                    layer_paint = make_opacity_paint(self._opacity)
                    if layer_paint is not None:
                        canvas.saveLayer(None, layer_paint)
                except Exception:
                    exception_once(logger, "transform_box_opacity_exc", "Failed to apply opacity layer")

            # Apply geometric transforms relative to origin
            if self._translate_x != 0.0 or self._translate_y != 0.0:
                canvas.translate(self._translate_x, self._translate_y)

            if self._rotation != 0.0 or self._scale_x != 1.0 or self._scale_y != 1.0:
                canvas.translate(x + ox, y + oy)
                if self._rotation != 0.0:
                    canvas.rotate(self._rotation)
                if self._scale_x != 1.0 or self._scale_y != 1.0:
                    canvas.scale(self._scale_x, self._scale_y)
                canvas.translate(-(x + ox), -(y + oy))

            child.set_last_rect(x, y, width, height)
            child.paint(canvas, x, y, width, height)
        except Exception:
            exception_once(logger, "transform_box_paint_exc", "TransformBox paint raised")
        finally:
            try:
                if needs_opacity:
                    canvas.restore()  # Restore opacity layer
                canvas.restore()  # Restore geometric transforms
            except Exception:
                exception_once(logger, "transform_box_restore_exc", "TransformBox canvas.restore failed")

    def hit_test(self, x: int, y: int):
        child = self._child()
        if child is not None:
            hit = child.hit_test(x, y)
            if hit is not None:
                return hit
        return super().hit_test(x, y)


@dataclass(slots=True)
class TransformModifier(ModifierElement):
    """Apply paint-only transforms (rotation, scale, translation, opacity)."""

    rotation: Optional[AngleLike] = None
    scale: Optional[ScaleLike] = None
    translation: Optional[TranslateLike] = None
    opacity: Optional[OpacityLike] = None
    transform_origin: OriginLike = "center"

    def apply(self, widget: Widget) -> Widget:
        # Merge with existing TransformBox in-place to preserve active observable
        # bindings from previously applied transform modifiers.
        if isinstance(widget, TransformBox):
            widget._transform_origin = self.transform_origin
            if self.rotation is not None:
                widget._bind_rotation(self.rotation)
            if self.scale is not None:
                widget._bind_scale(self.scale)
            if self.translation is not None:
                widget._bind_translation(self.translation)
            if self.opacity is not None:
                widget._bind_opacity(self.opacity)
            return widget
        return TransformBox(
            widget,
            rotation=self.rotation,
            scale=self.scale,
            translation=self.translation,
            opacity=self.opacity,
            transform_origin=self.transform_origin,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )


def rotate(angle: AngleLike, origin: OriginLike = "center") -> TransformModifier:
    """Return a modifier that rotates a widget during paint.

    Args:
        angle: Rotation angle in degrees, or an observable providing degrees.
        origin: Rotation origin. Supported: "center", "top_left", "top_right",
            "bottom_left", "bottom_right", or a (x, y) tuple in local coords.

    Note:
        Rotation is paint-only. Layout and hit-testing remain untransformed.
    """
    return TransformModifier(rotation=angle, transform_origin=origin)


def scale(factor: ScaleLike, origin: OriginLike = "center") -> TransformModifier:
    """Return a modifier that scales a widget during paint.

    Args:
        factor: Scale factor (uniform) or (sx, sy) tuple, or an observable.
        origin: Scale origin. Supported: "center", "top_left", "top_right",
            "bottom_left", "bottom_right", or a (x, y) tuple in local coords.

    Note:
        Scale is paint-only. Layout and hit-testing remain untransformed.
    """
    return TransformModifier(scale=factor, transform_origin=origin)


def translate(offset: TranslateLike) -> TransformModifier:
    """Return a modifier that translates a widget during paint.

    Args:
        offset: Translation offset as (dx, dy) tuple, or an observable.

    Note:
        Translation is paint-only. Layout and hit-testing remain untransformed.
    """
    return TransformModifier(translation=offset)


def opacity(value: OpacityLike) -> TransformModifier:
    """Return a modifier that applies opacity to a widget during paint.

    Args:
        value: Opacity value between 0.0 (transparent) and 1.0 (opaque),
            or an observable providing opacity.

    Note:
        Opacity is paint-only. Layout and hit-testing remain unchanged.
    """
    return TransformModifier(opacity=value)
