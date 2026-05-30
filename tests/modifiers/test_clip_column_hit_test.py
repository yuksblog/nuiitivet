from nuiitivet.layout.column import Column
from nuiitivet.widgets.box import Box
from nuiitivet.modifiers import clip
from nuiitivet.rendering.sizing import Sizing


def test_clip_modifier_on_column_prevents_hit_test_outside():
    """
    Verify that applying .clip() to a Column (which gets wrapped in ModifierBox)
    correctly clips hit testing for overflowing children.
    """
    # Child: 100x100 Box
    child = Box(width=Sizing.fixed(100), height=Sizing.fixed(100))
    child.name = "child_box"

    # Column: Fixed 50x50, containing the large child.
    # Column defaults to overflow='visible', so child will extend beyond 50x50.
    col = Column(children=[child], width=Sizing.fixed(50), height=Sizing.fixed(50)).modifier(clip())

    # Wrap in a parent that respects preferred size (e.g. Box with alignment)
    # If we just called col.layout(100, 100), the ModifierBox would be forced to 100x100.
    # We want to verify that layout respects the inner fixed size.
    root = Box(child=col, width=Sizing.fixed(100), height=Sizing.fixed(100), alignment=("start", "start"))

    # Layout root
    root.layout(100, 100)

    # Paint to establish geometry
    try:
        import skia

        surface = skia.Surface(100, 100)
        canvas = surface.getCanvas()
    except Exception:
        canvas = None

    root.paint(canvas, 0, 0, 100, 100)

    # Verify geometry
    # Root is 100x100
    assert root.last_rect == (0, 0, 100, 100)

    # Col (ModifierBox) should be 50x50 because it wraps a fixed-size Column
    # and the parent Box aligns it (doesn't stretch it).
    assert col.last_rect == (0, 0, 50, 50)

    # The child inside Column should be laid out.
    # Accessing the child through the wrapper
    # col is ModifierBox -> child is Column -> child is Box
    inner_col = col.children[0]
    inner_child = inner_col.children[0]

    # Hit test inside clip (25, 25) -> Should hit child
    # Coordinates are relative to root (0,0)
    hit = root.hit_test(25, 25)
    assert hit == inner_child, f"Expected hit at (25, 25) to be inner_child, got {hit}"

    # Hit test outside clip (25, 75) -> Should NOT hit child
    # Child exists there (y=0 to 100), but clip is 50 high.
    hit_outside = root.hit_test(25, 75)
    # Should hit root (background) or None, but definitely NOT inner_child
    assert hit_outside != inner_child, f"Expected hit at (25, 75) NOT to be inner_child, got {hit_outside}"
