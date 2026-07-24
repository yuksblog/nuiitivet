"""Hit-test ``auto`` default: the paper / glass model (issue #448).

A widget catches a pointer on its own rect only when it paints a visible
surface or is interactive; transparent layout wrappers and non-interactive
ink defer to their children so clicks reach whatever is behind.
"""

from nuiitivet.input.pointer import PointerEvent
from nuiitivet.layout.container import Container
from nuiitivet.layout.stack import Stack
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box


def _canvas() -> Box:
    return Box(width="100%", height="100%", background_color=(10, 20, 30, 255))


def _toolbar() -> Box:
    return Box(width=Sizing.fixed(200), height=Sizing.fixed(40), background_color=(200, 200, 200, 255))


def test_full_size_container_over_canvas_defers_to_canvas():
    """The motivating bug: a full-size alignment Container must not steal clicks.

    ``Stack([canvas, Container(toolbar, 100%x100%, bottom-center)])`` — the empty
    area of the alignment box lets clicks through to the canvas, while the
    toolbar strip still catches.
    """
    canvas = _canvas()
    toolbar = _toolbar()
    align_box = Container(toolbar, width="100%", height="100%", alignment="bottom-center")
    stack = Stack(children=[canvas, align_box])

    stack.layout(400, 300)

    # Empty area above the toolbar: the transparent Container defers, so the
    # canvas behind it receives the hit.
    assert stack.hit_test(200, 50) is canvas

    # Over the toolbar strip (bottom-center, 200x40 at x=100, y=260): the painted
    # toolbar catches.
    assert stack.hit_test(200, 280) is toolbar


def test_painted_box_catches_bare_box_defers():
    painted = Box(width=Sizing.fixed(100), height=Sizing.fixed(100), background_color=(1, 2, 3, 255))
    painted.layout(100, 100)
    assert painted.hit_test(50, 50) is painted

    bare = Box(width=Sizing.fixed(100), height=Sizing.fixed(100))
    bare.layout(100, 100)
    assert bare.hit_test(50, 50) is None


def test_border_only_box_catches():
    bordered = Box(width=Sizing.fixed(100), height=Sizing.fixed(100), border_width=2)
    bordered.layout(100, 100)
    assert bordered.hit_test(50, 50) is bordered


def test_bare_container_defers():
    container = Container(width=Sizing.fixed(100), height=Sizing.fixed(100))
    container.layout(100, 100)
    assert container.hit_test(50, 50) is None


def test_pointer_handling_widget_catches():
    """A widget that handles pointer input catches even when it paints nothing."""

    class PointerWidget(Widget):
        def __init__(self) -> None:
            super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(100))

        def on_pointer_event(self, event: PointerEvent) -> bool:
            return True

    widget = PointerWidget()
    widget.layout(100, 100)
    assert widget.hit_test(50, 50) is widget
