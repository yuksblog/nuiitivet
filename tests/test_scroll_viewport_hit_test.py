from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.widgets.box import Box
from nuiitivet.rendering.sizing import Sizing


def test_scroll_viewport_hit_test_clips_content():
    """
    Verify that ScrollViewport clips hit testing to the viewport area.
    """
    # Viewport size: 100x100
    # Content size: 100x200
    # Scroll offset: 0

    child = Box(width=Sizing.fixed(100), height=Sizing.fixed(200))
    child.name = "child_box"

    controller = ScrollController()
    viewport = ScrollViewport(
        child=child,
        controller=controller,
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
    )

    # Layout
    viewport.layout(100, 100)

    # Paint to establish geometry and viewport_rect
    try:
        import skia

        surface = skia.Surface(100, 100)
        canvas = surface.getCanvas()
    except Exception:
        canvas = None

    viewport.paint(canvas, 0, 0, 100, 100)

    # Check viewport rect
    assert viewport._viewport_rect == (0, 0, 100, 100)

    # Hit test inside viewport (e.g., 50, 50) -> Should hit child
    hit = viewport.hit_test(50, 50)
    assert hit == child, f"Expected hit at (50, 50) to be child, got {hit}"

    # Hit test outside viewport (e.g., 50, 150) -> Should NOT hit child
    # Even though child extends to 200, viewport is only 100 high
    hit_outside = viewport.hit_test(50, 150)
    assert hit_outside is None, f"Expected hit at (50, 150) to be None, got {hit_outside}"


def test_scroll_viewport_hit_test_with_scroll():
    """
    Verify hit testing works correctly when scrolled.
    """
    child = Box(width=Sizing.fixed(100), height=Sizing.fixed(200))
    controller = ScrollController()
    viewport = ScrollViewport(
        child=child,
        controller=controller,
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
    )

    viewport.layout(100, 100)

    # Scroll down by 50 pixels
    controller.scroll_to(50)

    try:
        import skia

        surface = skia.Surface(100, 100)
        canvas = surface.getCanvas()
    except Exception:
        canvas = None

    viewport.paint(canvas, 0, 0, 100, 100)

    # Child should be shifted up by 50px
    # Child rect in global coords: (0, -50, 100, 200)
    # Visible part of child: y=0 to y=100 (corresponding to child local y=50 to y=150)

    # Hit test at (50, 10) -> Should hit child (child local y = 60)
    hit = viewport.hit_test(50, 10)
    assert hit == child

    # Hit test at (50, 150) -> Outside viewport, should be None
    hit_outside = viewport.hit_test(50, 150)
    assert hit_outside is None
