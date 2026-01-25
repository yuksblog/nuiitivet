from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box
from nuiitivet.modifiers import background, border, clip, corner_radius, shadow


class MockWidget(Widget):
    pass


def test_modifier_chaining_optimization():
    """Test that non-conflicting modifiers are merged into a single Box."""
    m1 = background("red")
    m2 = m1 | border("blue", 2)

    w = MockWidget()
    result = w.modifier(m2)

    # Optimization: Should be a SINGLE Box with both properties
    assert isinstance(result, Box)
    # With new ModifierBox implementation, it should be a ModifierBox
    from nuiitivet.widgets.box import ModifierBox

    assert isinstance(result, ModifierBox)

    assert result.border_color == "blue"
    assert result.border_width == 2
    assert result.bgcolor == "red"

    # The child should be the original widget, not another Box
    assert result.children[0] is w


def test_modifier_conflict_merge():
    """Test that conflicting modifiers are MERGED (overwritten) with ModifierBox strategy."""
    # Two backgrounds should be merged into one Box (last one wins)
    m1 = background("red")
    m2 = m1 | background("blue")

    w = MockWidget()
    result = w.modifier(m2)

    # Should be MERGED: Single ModifierBox with blue background
    from nuiitivet.widgets.box import ModifierBox

    assert isinstance(result, ModifierBox)
    assert result.bgcolor == "blue"

    # Child should be the original widget
    child = result.children[0]
    assert child is w
    # NOT nested Box
    assert not isinstance(child, Box)


def test_background_modifier():
    w = MockWidget()
    m = background("red")
    result = w.modifier(m)

    assert isinstance(result, Box)
    assert result.bgcolor == "red"
    assert result.children[0] is w


def test_border_modifier():
    w = MockWidget()
    m = border("blue", width=2)
    result = w.modifier(m)

    assert isinstance(result, Box)
    assert result.border_color == "blue"
    assert result.border_width == 2
    assert result.children[0] is w


def test_shadow_modifier():
    w = MockWidget()
    m = shadow(color="black", blur=10, offset=(2, 2))
    result = w.modifier(m)

    assert isinstance(result, Box)
    assert result.shadow_color == "black"
    assert result.shadow_blur == 10
    assert result.shadow_offset == (2, 2)
    assert result.children[0] is w


def test_corner_radius_modifier():
    w = MockWidget()
    m = corner_radius(10)
    result = w.modifier(m)

    assert isinstance(result, Box)
    assert result.corner_radius == 10
    assert result.clip_content is True
    assert result.children[0] is w


def test_clip_modifier():
    w = MockWidget()
    m = clip()
    result = w.modifier(m)
    assert isinstance(result, Box)
    assert result.clip_content is True
    assert result.children[0] is w


def test_modifier_has_no_align_self():
    assert "align_self" not in getattr(__import__("nuiitivet.modifiers", fromlist=["__all__"]), "__all__")
