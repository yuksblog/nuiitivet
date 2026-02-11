"""Tests for RectTween."""

from nuiitivet.animation.tween import Rect, RectTween


def test_rect_creation():
    """Test Rect creation and properties."""
    rect = Rect(x=10.0, y=20.0, width=100.0, height=50.0)
    assert rect.x == 10.0
    assert rect.y == 20.0
    assert rect.width == 100.0
    assert rect.height == 50.0


def test_rect_to_tuple():
    """Test Rect to tuple conversion."""
    rect = Rect(x=10.5, y=20.5, width=100.5, height=50.5)
    assert rect.to_tuple() == (10.5, 20.5, 100.5, 50.5)


def test_rect_to_int_tuple():
    """Test Rect to integer tuple conversion."""
    rect = Rect(x=10.4, y=20.6, width=100.5, height=50.5)
    # Python's round() uses banker's rounding (round to even)
    # 10.4 -> 10, 20.6 -> 21, 100.5 -> 100, 50.5 -> 50
    assert rect.to_int_tuple() == (10, 21, 100, 50)


def test_rect_round():
    """Test Rect rounding."""
    rect = Rect(x=10.4, y=20.6, width=100.5, height=50.5)
    rounded = rect.round()
    # Python's round() uses banker's rounding (round to even)
    # 10.4 -> 10, 20.6 -> 21, 100.5 -> 100, 50.5 -> 50
    assert rounded.x == 10
    assert rounded.y == 21
    assert rounded.width == 100
    assert rounded.height == 50


def test_rect_from_tuple():
    """Test Rect creation from tuple."""
    rect = Rect.from_tuple((10.0, 20.0, 100.0, 50.0))
    assert rect.x == 10.0
    assert rect.y == 20.0
    assert rect.width == 100.0
    assert rect.height == 50.0


def test_rect_tween_interpolation():
    """Test RectTween linear interpolation."""
    begin = Rect(x=0.0, y=0.0, width=100.0, height=50.0)
    end = Rect(x=100.0, y=50.0, width=200.0, height=100.0)
    tween = RectTween(begin, end)

    # At t=0.0, should return begin
    result = tween.transform(0.0)
    assert result.x == 0.0
    assert result.y == 0.0
    assert result.width == 100.0
    assert result.height == 50.0

    # At t=1.0, should return end
    result = tween.transform(1.0)
    assert result.x == 100.0
    assert result.y == 50.0
    assert result.width == 200.0
    assert result.height == 100.0

    # At t=0.5, should return midpoint
    result = tween.transform(0.5)
    assert result.x == 50.0
    assert result.y == 25.0
    assert result.width == 150.0
    assert result.height == 75.0


def test_rect_tween_with_to_int_tuple():
    """Test RectTween with to_int_tuple conversion."""
    begin = Rect(x=0.0, y=0.0, width=96.0, height=32.0)
    end = Rect(x=0.0, y=0.0, width=220.0, height=56.0)
    tween = RectTween(begin, end)

    result = tween.transform(0.5).to_int_tuple()
    assert result == (0, 0, 158, 44)


def test_rect_immutability():
    """Test that Rect is immutable."""
    rect = Rect(x=10.0, y=20.0, width=100.0, height=50.0)
    try:
        rect.x = 15.0  # type: ignore
        assert False, "Rect should be immutable"
    except AttributeError:
        pass  # Expected


def test_rect_tween_quarter_interpolation():
    """Test RectTween at quarter points."""
    begin = Rect(x=0.0, y=0.0, width=100.0, height=100.0)
    end = Rect(x=100.0, y=100.0, width=200.0, height=200.0)
    tween = RectTween(begin, end)

    result = tween.transform(0.25)
    assert result.x == 25.0
    assert result.y == 25.0
    assert result.width == 125.0
    assert result.height == 125.0

    result = tween.transform(0.75)
    assert result.x == 75.0
    assert result.y == 75.0
    assert result.width == 175.0
    assert result.height == 175.0
