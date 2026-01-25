from nuiitivet.layout.container import Container
from nuiitivet.material.card import FilledCard
from nuiitivet.material.styles.card_style import CardStyle
from nuiitivet.widgets import TextBase as Text
from nuiitivet.widgeting.widget import Widget


def test_preferred_size_single_child_no_skia():
    c = Container(Text("hi"), padding=8)
    w, h = c.preferred_size()
    assert w >= 16
    assert h >= 16


def test_paint_no_skia_does_not_raise():
    c = FilledCard(
        Text("hello"),
        padding=4,
        style=CardStyle.filled().copy_with(background="#E7E0EC"),
    )
    try:
        c.paint(None, 0, 0, 200, 40)
    except Exception as e:
        raise AssertionError("Container.paint raised in no-skia env: " + str(e))


def test_add_child_replaces_existing():
    c = Container()
    a = Text("a")
    b = Text("b")
    c.add_child(a)
    assert len(c.children) == 1
    assert c.children[0] is a
    c.add_child(b)
    assert len(c.children) == 1
    assert c.children[0] is b
    assert getattr(b, "_parent", None) is c
    assert getattr(a, "_parent", None) is None


def test_container_paint_respects_padding_and_align():
    child = Text("hi")
    # padding=10, align="center"
    c = Container(child, padding=10, alignment="center")

    # Paint at 100x100
    # Inner size 80x80. Child is small (e.g. 20x20). Center means offset.
    c.paint(None, 0, 0, 100, 100)

    # Currently Container.paint just passes 0,0,100,100 to child.
    # If fixed, child.last_rect should be centered within inner rect.
    # We can't easily check exact coords without mocking Text.preferred_size,
    # but we can check it's NOT (0,0,100,100) if child is small.

    # Let's use a FixedWidget for deterministic testing
    class Fixed(Widget):
        def preferred_size(self):
            return (10, 10)

        def paint(self, canvas, x, y, w, h):
            self.set_last_rect(x, y, w, h)

    f = Fixed()
    c = Container(f, padding=10, alignment="center")
    c.paint(None, 0, 0, 100, 100)

    # Expected:
    # Inner: x=10, y=10, w=80, h=80
    # Child (10x10) centered in 80x80:
    # x = 10 + (80-10)//2 = 10 + 35 = 45
    # y = 10 + (80-10)//2 = 10 + 35 = 45
    # w = 10, h = 10

    # If Container is broken (current state), it will be (0, 0, 100, 100)
    assert f.last_rect == (45, 45, 10, 10)


def test_container_child_stretch():
    from nuiitivet.rendering.sizing import Sizing

    class Fixed(Widget):
        def preferred_size(self):
            return (10, 10)

        def paint(self, canvas, x, y, w, h):
            self.set_last_rect(x, y, w, h)

    # Child wants to stretch
    f = Fixed(width=Sizing.flex(1), height=Sizing.flex(1))
    c = Container(f, padding=0)

    # Paint at 100x100
    c.paint(None, 0, 0, 100, 100)

    # Should fill container
    assert f.last_rect == (0, 0, 100, 100)


def test_container_alignment_nine_points():
    class Fixed(Widget):
        def preferred_size(self):
            return (10, 10)

        def paint(self, canvas, x, y, w, h):
            self.set_last_rect(x, y, w, h)

    # Outer: 100x100, padding=10 -> inner: (10,10,80,80)
    # Child: 10x10
    inner_x, inner_y, inner_w, inner_h = (10, 10, 80, 80)
    child_w, child_h = (10, 10)
    center_x = inner_x + (inner_w - child_w) // 2
    center_y = inner_y + (inner_h - child_h) // 2
    end_x = inner_x + (inner_w - child_w)
    end_y = inner_y + (inner_h - child_h)

    f = Fixed()
    c = Container(f, padding=10, alignment="top-left")
    c.paint(None, 0, 0, 100, 100)
    assert f.last_rect == (inner_x, inner_y, 10, 10)

    f = Fixed()
    c = Container(f, padding=10, alignment="top-center")
    c.paint(None, 0, 0, 100, 100)
    assert f.last_rect == (center_x, inner_y, 10, 10)

    f = Fixed()
    c = Container(f, padding=10, alignment="bottom-right")
    c.paint(None, 0, 0, 100, 100)
    assert f.last_rect == (end_x, end_y, 10, 10)

    f = Fixed()
    c = Container(f, padding=10, alignment="center")
    c.paint(None, 0, 0, 100, 100)
    assert f.last_rect == (center_x, center_y, 10, 10)
