from nuiitivet.layout.stack import Stack
from nuiitivet.layout.container import Container
from nuiitivet.layout.column import Column
from nuiitivet.layout.spacer import Spacer
from nuiitivet.rendering.sizing import Sizing


def test_stack_union_sizing():
    # Child 1: Large fixed size
    child1 = Container(width=100, height=100)
    # Child 2: Small fixed size
    child2 = Container(width=50, height=50)

    stack = Stack(children=[child1, child2])

    # Layout with unconstrained parent
    # (simulated by large size or preferred_size check)
    # preferred_size should be union (max) of children
    w, h = stack.preferred_size()
    assert w == 100
    assert h == 100

    # Layout with specific size
    stack.layout(100, 100)

    # Check children layout rects
    # child1 should be at 0,0 with 100x100
    assert child1.layout_rect == (0, 0, 100, 100)
    # child2 should be at 0,0 with 50x50 (default alignment top-left)
    assert child2.layout_rect == (0, 0, 50, 50)


def test_stack_alignment():
    child = Container(width=50, height=50)
    stack = Stack(children=[child], alignment="center", width=100, height=100)

    stack.layout(100, 100)

    # Center of 100x100 is 50,50. Child is 50x50.
    # Top-left of child should be at (100-50)/2 = 25
    assert child.layout_rect == (25, 25, 50, 50)


def test_stack_alignment_bottom_right():
    child = Container(width=10, height=10)
    # Align bottom-right
    stack = Stack(children=[child], alignment="bottom-right", width=100, height=100)
    stack.layout(100, 100)

    # Child width/height is 10 (preferred).
    # x = 100 - 10 = 90
    # y = 100 - 10 = 90
    assert child.layout_rect == (90, 90, 10, 10)


def test_stack_preferred_size_respects_fixed_sizing():
    child = Container(width=10, height=10)
    stack = Stack(children=[child], width=300, height=200)

    w, h = stack.preferred_size()
    assert w == 300
    assert h == 200


def test_stack_column_spacer_expansion():
    # Requirement: Union mode, Child A is large. Child B is Column with Spacer.
    # Spacer should push button to bottom of Stack.
    # We use explicit size on Column to ensure it matches stack size.

    # Child A: 100x200
    child_a = Container(width=100, height=200)

    # Child B: Column with Spacer and Button (Container)
    button = Container(width=50, height=20)
    col = Column(children=[Spacer(width=Sizing.flex(1), height=Sizing.flex(1)), button], width=100, height=200)

    # Stack
    stack = Stack(children=[child_a, col])

    # Preferred size should be 100x200 (determined by child_a)
    w, h = stack.preferred_size()
    assert w == 100
    assert h == 200

    # Layout
    stack.layout(100, 200)

    # Check Child B (Column) rect
    # It should be 100x200
    assert col.layout_rect == (0, 0, 100, 200)

    # Check Button position
    # Column height is 200. Button height 20. Spacer takes 180.
    # Button y should be 180.
    # But Column layout sets children rects relative to Column.
    # Column is at 0,0 of Stack.
    # So Button absolute y (relative to Stack) should be 180.
    # We need to check button.layout_rect relative to Column.
    # Column is at 0,0 of Stack.
    # Button should be at (0, 180, 50, 20) relative to Column.
    assert button.layout_rect == (0, 180, 50, 20)


def test_stack_percentage_sizing():
    # Child: Container width="50%", height="50%"
    child = Container(width="50%", height="50%")
    stack = Stack(children=[child], width=200, height=200)
    stack.layout(200, 200)

    assert child.layout_rect == (0, 0, 100, 100)


def test_stack_spacer_with_percentage_container():
    # Requirement: Container with width/height="100%" should fill Stack,
    # allowing Spacer inside to work.

    spacer = Spacer(width=Sizing.flex(1), height=Sizing.flex(1))
    icon = Container(width=10, height=10)
    # Column needs to fill Container for Spacer to work
    col = Column(children=[spacer, icon], height="100%")

    # Container filling the stack
    container = Container(width="100%", height="100%", child=col)

    stack = Stack(children=[container], width=200, height=200)
    stack.layout(200, 200)

    # Container should be 200x200
    assert container.layout_rect == (0, 0, 200, 200)

    # Icon should be pushed to bottom
    # Column height 200. Icon 10. Spacer 190.
    # Icon y should be 190.
    assert icon.layout_rect == (0, 190, 10, 10)
