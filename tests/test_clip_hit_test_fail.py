from nuiitivet.widgets.box import Box
from nuiitivet.modifiers import clip
from nuiitivet.rendering.sizing import Sizing


def test_clip_modifier_prevents_hit_test_outside():
    """
    Verify that a clipped container does not allow hit testing on children
    that are outside the clip region.
    """
    # Create a small container that clips its content
    # Container size: 100x50
    # Child size: 100x100 (overflows vertically)

    child = Box(width=Sizing.fixed(100), height=Sizing.fixed(100))
    # Mark child so we can identify it
    child.name = "child_box"

    container = Box(
        child=child, width=Sizing.fixed(100), height=Sizing.fixed(50), alignment=("start", "start")
    ).modifier(clip())

    # Layout and paint to establish geometry
    container.layout(100, 50)

    # Mock canvas for paint
    try:
        import skia

        surface = skia.Surface(100, 50)
        canvas = surface.getCanvas()
    except Exception:
        canvas = None

    container.paint(canvas, 0, 0, 100, 50)

    # Check geometry
    # Container rect: (0, 0, 100, 50)
    # Child rect: (0, 0, 100, 100) - established by Box layout logic

    assert container.last_rect == (0, 0, 100, 50)
    assert child.last_rect == (0, 0, 100, 100)

    # Hit test inside the clip region (e.g., 50, 25) -> Should hit child
    hit = container.hit_test(50, 25)
    assert hit == child, f"Expected hit at (50, 25) to be child, got {hit}"

    # Hit test outside the clip region but inside child rect (e.g., 50, 75) -> Should NOT hit child
    # Currently this fails because hit_test doesn't respect clip
    hit_outside = container.hit_test(50, 75)
    assert hit_outside is None, f"Expected hit at (50, 75) to be None (clipped), got {hit_outside}"
