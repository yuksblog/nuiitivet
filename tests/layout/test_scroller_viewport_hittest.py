"""Test that ScrollViewport correctly restricts hit_test to visible region."""

from nuiitivet.layout.column import Column
from nuiitivet.layout.scroller import Scroller
from nuiitivet.widgeting.widget import Widget


class MockCanvas:
    """Minimal canvas mock for testing."""

    def save(self):
        pass

    def restore(self):
        pass

    def clipRect(self, rect, op, antialias):
        pass

    def drawTextBlob(self, blob, x, y, paint):
        pass

    def drawRect(self, rect, paint):
        pass

    def drawRRect(self, rrect, paint):
        pass


class SimpleWidget(Widget):
    """Simple test widget that doesn't require skia."""

    def __init__(self, *, width: int = 50, height: int = 30):
        super().__init__(width=width, height=height)

    def preferred_size(self):
        return (50, 30)

    def paint(self, canvas, x, y, width, height):
        self.set_last_rect(x, y, width, height)


def test_viewport_hittest_only_in_visible_area() -> None:
    """ScrollViewport should only respond to hit_test within visible viewport."""
    widgets = [SimpleWidget() for _ in range(10)]
    col = Column(widgets, gap=10)
    scroller = Scroller(col, height=100)
    canvas = MockCanvas()
    scroller.paint(canvas, 0, 0, 200, 100)
    hit = scroller.hit_test(50, 50)
    assert hit is not None
    hit_below = scroller.hit_test(50, 150)
    assert hit_below is None
    hit_above = scroller.hit_test(50, -10)
    assert hit_above is None


def test_viewport_hittest_with_scroll_offset() -> None:
    """After scrolling, only visible content should respond to hit_test."""
    widgets = [SimpleWidget() for _ in range(20)]
    col = Column(widgets, gap=10)
    scroller = Scroller(col, height=100)
    canvas = MockCanvas()
    scroller.paint(canvas, 0, 0, 200, 100)
    scroller.scroll_to(50)
    scroller.paint(canvas, 0, 0, 200, 100)
    hit = scroller.hit_test(50, 50)
    assert hit is not None
    hit_below = scroller.hit_test(50, 150)
    assert hit_below is None
    hit_scrolled_out = scroller.hit_test(50, -40)
    assert hit_scrolled_out is None


def test_viewport_hittest_respects_padding() -> None:
    """ScrollViewport with padding should only hit inside padded viewport."""
    widgets = [SimpleWidget() for _ in range(10)]
    col = Column(widgets, gap=5)
    scroller = Scroller(col, height=100, padding=10)
    canvas = MockCanvas()
    scroller.paint(canvas, 50, 50, 200, 100)
    hit_inside = scroller.hit_test(99, 99)
    assert hit_inside is not None
    hit_outside = scroller.hit_test(30, 100)
    assert hit_outside is None
