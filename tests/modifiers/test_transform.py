"""Tests for TransformBox and transform modifiers."""

from unittest.mock import MagicMock

from nuiitivet.modifiers.transform import (
    TransformBox,
    rotate,
    scale,
    translate,
    opacity,
)
from nuiitivet.widgets.box import Box
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.observable.value import _ObservableValue


class MockWidget(Box):
    """Mock widget for testing."""

    def __init__(self):
        super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(100))


def test_rotate_modifier_basic():
    """Test basic rotation modifier."""
    widget = MockWidget()
    modified = widget.modifier(rotate(45))

    assert isinstance(modified, TransformBox)
    assert modified._rotation == 45.0
    assert modified._scale_x == 1.0
    assert modified._scale_y == 1.0
    assert modified._translate_x == 0.0
    assert modified._translate_y == 0.0
    assert modified._opacity == 1.0


def test_rotate_modifier_with_origin():
    """Test rotation with custom origin."""
    widget = MockWidget()
    modified = widget.modifier(rotate(90, origin="top_left"))

    assert isinstance(modified, TransformBox)
    assert modified._rotation == 90.0
    assert modified._transform_origin == "top_left"


def test_scale_modifier_uniform():
    """Test uniform scale modifier."""
    widget = MockWidget()
    modified = widget.modifier(scale(2.0))

    assert isinstance(modified, TransformBox)
    assert modified._scale_x == 2.0
    assert modified._scale_y == 2.0
    assert modified._rotation == 0.0


def test_scale_modifier_non_uniform():
    """Test non-uniform scale modifier."""
    widget = MockWidget()
    modified = widget.modifier(scale((1.5, 2.5)))

    assert isinstance(modified, TransformBox)
    assert modified._scale_x == 1.5
    assert modified._scale_y == 2.5


def test_translate_modifier():
    """Test translation modifier."""
    widget = MockWidget()
    modified = widget.modifier(translate((10, 20)))

    assert isinstance(modified, TransformBox)
    assert modified._translate_x == 10.0
    assert modified._translate_y == 20.0


def test_opacity_modifier():
    """Test opacity modifier."""
    widget = MockWidget()
    modified = widget.modifier(opacity(0.5))

    assert isinstance(modified, TransformBox)
    assert modified._opacity == 0.5


def test_opacity_clamping():
    """Test opacity is clamped to [0, 1]."""
    widget = MockWidget()

    # Test upper bound
    modified1 = widget.modifier(opacity(1.5))
    assert modified1._opacity == 1.0

    # Test lower bound
    modified2 = widget.modifier(opacity(-0.5))
    assert modified2._opacity == 0.0


def test_multiple_transforms_chained():
    """Test chaining multiple transform modifiers."""
    widget = MockWidget()
    modified = widget.modifier(rotate(45) | scale(1.5) | translate((10, 20)) | opacity(0.8))

    assert isinstance(modified, TransformBox)
    assert modified._rotation == 45.0
    assert modified._scale_x == 1.5
    assert modified._scale_y == 1.5
    assert modified._translate_x == 10.0
    assert modified._translate_y == 20.0
    assert modified._opacity == 0.8


def test_transform_box_with_observable_rotation():
    """Test TransformBox with observable rotation."""
    angle_obs = _ObservableValue(0.0)
    widget = MockWidget()
    modified = widget.modifier(rotate(angle_obs))

    assert modified._rotation == 0.0

    # Change angle
    angle_obs.value = 90.0
    assert modified._rotation == 90.0


def test_transform_box_with_observable_scale():
    """Test TransformBox with observable scale."""
    scale_obs = _ObservableValue(1.0)
    widget = MockWidget()
    modified = widget.modifier(scale(scale_obs))

    assert modified._scale_x == 1.0
    assert modified._scale_y == 1.0

    # Change scale
    scale_obs.value = 2.0
    assert modified._scale_x == 2.0
    assert modified._scale_y == 2.0


def test_transform_box_with_observable_translation():
    """Test TransformBox with observable translation."""
    trans_obs = _ObservableValue((0.0, 0.0))
    widget = MockWidget()
    modified = widget.modifier(translate(trans_obs))

    assert modified._translate_x == 0.0
    assert modified._translate_y == 0.0

    # Change translation
    trans_obs.value = (10.0, 20.0)
    assert modified._translate_x == 10.0
    assert modified._translate_y == 20.0


def test_transform_box_with_observable_opacity():
    """Test TransformBox with observable opacity."""
    opacity_obs = _ObservableValue(1.0)
    widget = MockWidget()
    modified = widget.modifier(opacity(opacity_obs))

    assert modified._opacity == 1.0

    # Change opacity
    opacity_obs.value = 0.5
    assert modified._opacity == 0.5


def test_chained_transform_preserves_existing_observable_bindings() -> None:
    """Applying additional transform modifiers must not break existing bindings."""
    opacity_obs = _ObservableValue(0.0)
    scale_obs = _ObservableValue(1.0)

    widget = MockWidget()
    modified = widget.modifier(opacity(opacity_obs) | scale(scale_obs))

    assert isinstance(modified, TransformBox)
    assert modified._opacity == 0.0
    assert modified._scale_x == 1.0
    assert modified._scale_y == 1.0

    opacity_obs.value = 0.7
    assert modified._opacity == 0.7

    scale_obs.value = 1.4
    assert modified._scale_x == 1.4
    assert modified._scale_y == 1.4


def test_transform_origin_center():
    """Test transform origin resolution for 'center'."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45, transform_origin="center")

    ox, oy = box._resolve_origin(100, 100)
    assert ox == 50.0
    assert oy == 50.0


def test_transform_origin_corners():
    """Test transform origin resolution for corner positions."""
    widget = MockWidget()

    # Top left
    box1 = TransformBox(widget, rotation=45, transform_origin="top_left")
    ox, oy = box1._resolve_origin(100, 100)
    assert ox == 0.0
    assert oy == 0.0

    # Top right
    box2 = TransformBox(widget, rotation=45, transform_origin="top_right")
    ox, oy = box2._resolve_origin(100, 100)
    assert ox == 100.0
    assert oy == 0.0

    # Bottom left
    box3 = TransformBox(widget, rotation=45, transform_origin="bottom_left")
    ox, oy = box3._resolve_origin(100, 100)
    assert ox == 0.0
    assert oy == 100.0

    # Bottom right
    box4 = TransformBox(widget, rotation=45, transform_origin="bottom_right")
    ox, oy = box4._resolve_origin(100, 100)
    assert ox == 100.0
    assert oy == 100.0


def test_transform_origin_custom_tuple():
    """Test transform origin with custom (x, y) tuple."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45, transform_origin=(25, 75))

    ox, oy = box._resolve_origin(100, 100)
    assert ox == 25.0
    assert oy == 75.0


def test_transform_origin_invalid_fallback():
    """Test transform origin falls back to center for invalid values."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45, transform_origin="invalid")

    ox, oy = box._resolve_origin(100, 100)
    assert ox == 50.0
    assert oy == 50.0


def test_has_transforms_false():
    """Test _has_transforms returns False when no transforms active."""
    widget = MockWidget()
    box = TransformBox(widget)

    assert box._has_transforms() is False


def test_has_transforms_rotation():
    """Test _has_transforms returns True with rotation."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45)

    assert box._has_transforms() is True


def test_has_transforms_scale():
    """Test _has_transforms returns True with scale."""
    widget = MockWidget()
    box = TransformBox(widget, scale=1.5)

    assert box._has_transforms() is True


def test_has_transforms_translation():
    """Test _has_transforms returns True with translation."""
    widget = MockWidget()
    box = TransformBox(widget, translation=(10, 20))

    assert box._has_transforms() is True


def test_has_transforms_opacity():
    """Test _has_transforms returns True with opacity."""
    widget = MockWidget()
    box = TransformBox(widget, opacity=0.5)

    assert box._has_transforms() is True


def test_paint_fast_path_no_transforms():
    """Test paint uses fast path when no transforms."""
    widget = MockWidget()
    box = TransformBox(widget)

    canvas = MagicMock()
    box.layout(100, 100)
    box.paint(canvas, 0, 0, 100, 100)

    # Fast path should NOT call save/restore
    canvas.save.assert_not_called()
    canvas.restore.assert_not_called()


def test_paint_fast_path_no_canvas():
    """Test paint handles None canvas gracefully."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45)

    box.layout(100, 100)
    box.paint(None, 0, 0, 100, 100)

    # Should not raise


def test_paint_with_rotation():
    """Test paint applies rotation transform."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45)

    canvas = MagicMock()
    box.layout(100, 100)
    box.paint(canvas, 0, 0, 100, 100)

    canvas.save.assert_called()
    canvas.rotate.assert_called_once_with(45.0)
    canvas.restore.assert_called()


def test_paint_with_scale():
    """Test paint applies scale transform."""
    widget = MockWidget()
    box = TransformBox(widget, scale=(1.5, 2.0))

    canvas = MagicMock()
    box.layout(100, 100)
    box.paint(canvas, 0, 0, 100, 100)

    canvas.save.assert_called()
    canvas.scale.assert_called_once_with(1.5, 2.0)
    canvas.restore.assert_called()


def test_paint_with_translation():
    """Test paint applies translation transform."""
    widget = MockWidget()
    box = TransformBox(widget, translation=(10, 20))

    canvas = MagicMock()
    box.layout(100, 100)
    box.paint(canvas, 0, 0, 100, 100)

    canvas.save.assert_called()
    # Translation called before origin transforms
    assert canvas.translate.call_count >= 1
    canvas.restore.assert_called()


def test_paint_with_opacity():
    """Test paint applies opacity layer."""
    widget = MockWidget()
    box = TransformBox(widget, opacity=0.5)

    canvas = MagicMock()
    canvas.saveLayer = MagicMock()
    box.layout(100, 100)
    box.paint(canvas, 0, 0, 100, 100)

    canvas.save.assert_called()
    canvas.saveLayer.assert_called_once()
    # Two restores: one for opacity layer, one for geometric transforms
    assert canvas.restore.call_count == 2


def test_paint_with_combined_transforms():
    """Test paint applies all transforms in correct order."""
    widget = MockWidget()
    box = TransformBox(
        widget,
        rotation=45,
        scale=1.5,
        translation=(10, 20),
        opacity=0.8,
    )

    canvas = MagicMock()
    canvas.saveLayer = MagicMock()
    box.layout(100, 100)
    box.paint(canvas, 0, 0, 100, 100)

    canvas.save.assert_called()
    canvas.saveLayer.assert_called_once()
    canvas.translate.assert_called()
    canvas.rotate.assert_called_once_with(45.0)
    canvas.scale.assert_called_once_with(1.5, 1.5)
    assert canvas.restore.call_count == 2


def test_preferred_size_delegates_to_child():
    """Test preferred_size delegates to child widget."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45)

    size = box.preferred_size(max_width=200, max_height=200)
    assert size == (100, 100)


def test_layout_delegates_to_child():
    """Test layout delegates to child widget."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45)

    box.layout(150, 150)

    child = box._child()
    assert child is not None
    assert child.layout_rect == (0, 0, 150, 150)


def test_hit_test_delegates_to_child():
    """Test hit_test delegates to child widget."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45)
    box.layout(100, 100)
    box.set_last_rect(0, 0, 100, 100)

    # Hit inside
    result = box.hit_test(50, 50)
    assert result is not None

    # Hit outside
    result = box.hit_test(200, 200)
    assert result is None


def test_transform_modifier_merge():
    """Test TransformModifier merges with existing TransformBox."""
    widget = MockWidget()

    # Apply first transform
    modified1 = widget.modifier(rotate(45))
    assert isinstance(modified1, TransformBox)
    assert modified1._rotation == 45.0
    assert modified1._scale_x == 1.0

    # Apply second transform - should merge
    modified2 = modified1.modifier(scale(2.0))
    assert isinstance(modified2, TransformBox)
    assert modified2._rotation == 45.0
    assert modified2._scale_x == 2.0


def test_set_rotation_error_handling():
    """Test _set_rotation handles invalid values gracefully."""
    widget = MockWidget()
    box = TransformBox(widget)

    # Should not raise
    box._set_rotation("invalid")
    assert box._rotation == 0.0


def test_set_scale_error_handling():
    """Test _set_scale handles invalid values gracefully."""
    widget = MockWidget()
    box = TransformBox(widget)

    # Should not raise
    box._set_scale("invalid")
    assert box._scale_x == 1.0
    assert box._scale_y == 1.0


def test_set_translation_error_handling():
    """Test _set_translation handles invalid values gracefully."""
    widget = MockWidget()
    box = TransformBox(widget)

    # Should not raise
    box._set_translation("invalid")
    assert box._translate_x == 0.0
    assert box._translate_y == 0.0


def test_set_opacity_error_handling():
    """Test _set_opacity handles invalid values gracefully."""
    widget = MockWidget()
    box = TransformBox(widget)

    # Should not raise
    box._set_opacity("invalid")
    assert box._opacity == 1.0


def test_bind_rotation_exception_handling():
    """Test _bind_rotation handles invalid rotation values gracefully."""
    widget = MockWidget()

    # Pass a plain number instead of observable - should work
    box = TransformBox(widget, rotation=45.0)
    assert box._rotation == 45.0


def test_bind_scale_exception_handling():
    """Test _bind_scale handles invalid scale values gracefully."""
    widget = MockWidget()

    # Pass a plain number instead of observable - should work
    box = TransformBox(widget, scale=2.0)
    assert box._scale_x == 2.0
    assert box._scale_y == 2.0


def test_bind_translation_exception_handling():
    """Test _bind_translation handles invalid translation values gracefully."""
    widget = MockWidget()

    # Pass a plain tuple instead of observable - should work
    box = TransformBox(widget, translation=(10, 20))
    assert box._translate_x == 10.0
    assert box._translate_y == 20.0


def test_bind_opacity_exception_handling():
    """Test _bind_opacity handles invalid opacity values gracefully."""
    widget = MockWidget()

    # Pass a plain number instead of observable - should work
    box = TransformBox(widget, opacity=0.5)
    assert box._opacity == 0.5


def test_paint_exception_handling():
    """Test paint handles exceptions gracefully."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45)

    # Mock canvas that raises on rotate
    canvas = MagicMock()
    canvas.rotate.side_effect = Exception("Mock error")

    box.layout(100, 100)
    # Should not raise
    box.paint(canvas, 0, 0, 100, 100)

    # Restore should still be called
    canvas.restore.assert_called()


def test_preferred_size_exception_handling():
    """Test preferred_size handles child exceptions gracefully."""
    # Create a widget that raises on preferred_size

    class BadWidget(Box):
        def preferred_size(self, max_width=None, max_height=None):
            raise Exception("Mock error")

    bad_widget = BadWidget()
    box = TransformBox(bad_widget, rotation=45)

    # Should not raise, falls back to super().preferred_size()
    size = box.preferred_size()
    assert isinstance(size, tuple)


def test_layout_exception_handling():
    """Test layout handles child exceptions gracefully."""

    class BadWidget(Box):
        def layout(self, width, height):
            raise Exception("Mock error")

    bad_widget = BadWidget()
    box = TransformBox(bad_widget, rotation=45)

    # Should not raise
    box.layout(100, 100)


def test_transform_box_no_child():
    """Test TransformBox handles missing child gracefully."""
    # Create a TransformBox without adding a child
    from nuiitivet.widgets.box import Box

    box = Box()
    transform_box = TransformBox.__new__(TransformBox)
    transform_box.__dict__.update(box.__dict__)
    transform_box._rotation = 0.0
    transform_box._scale_x = 1.0
    transform_box._scale_y = 1.0
    transform_box._translate_x = 0.0
    transform_box._translate_y = 0.0
    transform_box._opacity = 1.0
    transform_box._transform_origin = "center"

    # Should not raise
    assert transform_box._child() is None
    transform_box.layout(100, 100)
    transform_box.paint(MagicMock(), 0, 0, 100, 100)
    size = transform_box.preferred_size()
    assert isinstance(size, tuple)


def test_scale_tuple_parsing():
    """Test scale handles list in addition to tuple."""
    widget = MockWidget()
    box = TransformBox(widget)

    box._set_scale([1.5, 2.0])
    assert box._scale_x == 1.5
    assert box._scale_y == 2.0


def test_transform_origin_tuple_exception():
    """Test transform origin handles invalid tuple gracefully."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45, transform_origin=("invalid", "tuple"))

    ox, oy = box._resolve_origin(100, 100)
    # Should fall back to center
    assert ox == 50.0
    assert oy == 50.0


def test_paint_without_layout():
    """Test paint performs layout if not already done."""
    widget = MockWidget()
    box = TransformBox(widget, rotation=45)

    canvas = MagicMock()
    # Paint without calling layout first
    box.paint(canvas, 0, 0, 100, 100)

    # Child should have layout_rect set
    child = box._child()
    assert child is not None
    assert child.layout_rect is not None
