import sys
import types

from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box


class DummyChild(Widget):
    def __init__(self):
        super().__init__()

    def paint(self, canvas, x, y, width, height):
        return None

    def preferred_size(self):
        return (0, 0)


class FakeCanvas:
    def __init__(self):
        self.saved = 0
        self.restored = 0
        self.clip_rect_calls = 0
        self.clip_rrect_calls = 0

    def save(self):
        self.saved += 1
        return self.saved

    def clipRect(self, rect, aa=False):
        self.clip_rect_calls += 1

    def clipRRect(self, rrect, aa=False):
        self.clip_rrect_calls += 1

    def restore(self):
        self.restored += 1


def test_clip_content_hit_test_uses_local_coordinates():
    """A clipped Box placed at a non-zero offset stays hit-testable.

    ``hit_test`` receives local coordinates, so the clip-bounds check must use
    the widget's own size at origin (0, 0) -- not ``last_rect``'s parent-relative
    offset.  Regression test for clipped widgets (e.g. ExtendedFab) becoming
    unclickable when laid out inside a Row/Column/Container.
    """
    box = Box(child=DummyChild(), corner_radius=8)
    box.clip_content = True
    # Simulate a layout placing the box far from the origin.
    box.set_layout_rect(200, 50, 120, 40)
    box.set_last_rect(200, 50, 120, 40)

    # Local coordinates inside the box must hit; outside must miss.
    assert box.hit_test(10, 10) is box
    assert box.hit_test(119, 39) is box
    assert box.hit_test(-1, 10) is None
    assert box.hit_test(10, 40) is None


def test_box_clip_uses_rrect_for_corner_radius():
    fake_skia = types.SimpleNamespace()

    class _Rect:
        @staticmethod
        def MakeXYWH(x, y, w, h):
            return (x, y, w, h)

    class _RRect:
        @staticmethod
        def MakeRectRadii(rect, radii):
            return (rect, tuple(radii))

    fake_skia.Rect = _Rect
    fake_skia.RRect = _RRect

    original_skia = sys.modules.get("skia")
    sys.modules["skia"] = fake_skia
    try:
        box = Box(child=DummyChild(), corner_radius=8)
        box.clip_content = True
        canvas = FakeCanvas()
        box.paint(canvas, 0, 0, 100, 40)
        assert canvas.clip_rrect_calls == 1
        assert canvas.clip_rect_calls == 0
        assert canvas.saved == canvas.restored == 1
    finally:
        if original_skia is not None:
            sys.modules["skia"] = original_skia
        else:
            sys.modules.pop("skia", None)
