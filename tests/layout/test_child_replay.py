"""A container records each child once and replays it while the child is clean."""

from __future__ import annotations

import hashlib
from typing import Any, List, Sequence, Tuple
from unittest.mock import patch

import pytest
import skia

from nuiitivet.layout import layout_utils
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.layout_utils import layout_child_if_needed
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.layout.scrollable import VerticalScrollable
from nuiitivet.layout.stack import Stack
from nuiitivet.material.selection_controls import Checkbox
from nuiitivet.material.text import Text
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.modifiers.background import background
from nuiitivet.modifiers.border import border
from nuiitivet.modifiers.corner_radius import corner_radius
from nuiitivet.modifiers.transform import translate
from nuiitivet.observable import State
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.testing import mount
from nuiitivet.widgeting.paint_replay import replay_safe
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box

SIZE = 400


class _Leaf(Box):
    """A 100x50 coloured leaf that declares its paint safe to replay and counts it."""

    def __init__(self, color: str = "#336699") -> None:
        super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(50), background_color=color)
        self.painted = 0

    @replay_safe
    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1
        super().paint(canvas, x, y, width, height)


class _Placed(Stack):
    """A Stack whose children sit where ``positions`` says."""

    def __init__(
        self, children: Sequence[Widget], positions: List[Tuple[int, int]], width: int = SIZE, height: int = SIZE
    ) -> None:
        super().__init__(children, width=Sizing.fixed(width), height=Sizing.fixed(height))
        self.positions = positions
        self.size = (width, height)

    def layout(self, width: int, height: int) -> None:
        Widget.layout(self, width, height)
        for child, (x, y) in zip(self.children_snapshot(), self.positions):
            w = int(child.width_sizing.value)
            h = int(child.height_sizing.value)
            layout_child_if_needed(child, w, h, sized_by_parent=True)
            child.set_layout_rect(x, y, w, h)

    def move(self, index: int, x: int, y: int) -> None:
        self.positions[index] = (x, y)
        self.mark_needs_layout()
        self.layout(*self.size)


def _surface(size: int = SIZE) -> Any:
    surface: Any = skia.Surface  # the local stub declares no constructor
    return surface(size, size)


class _Scene:
    def __init__(self, root: Widget, leaves: List[_Leaf], size: int = SIZE) -> None:
        self.root = root
        self.leaves = leaves
        self.size = size
        self.surface = _surface(size)
        self.canvas = self.surface.getCanvas()
        root.layout(size, size)

    def frame(self) -> list[int]:
        """Paint one frame and return how often each leaf was painted in it."""
        before = [leaf.painted for leaf in self.leaves]
        self.canvas.clear(0xFFFFFFFF)
        self.root.paint(self.canvas, 0, 0, self.size, self.size)
        return [leaf.painted - b for leaf, b in zip(self.leaves, before)]

    def color_at(self, x: int, y: int) -> int:
        red, green, blue = (int(v) for v in self.surface.makeImageSnapshot().toarray()[y, x, :3])
        return (red << 16) | (green << 8) | blue


def _stack(count: int = 3) -> _Scene:
    leaves = [_Leaf() for _ in range(count)]
    return _Scene(_Placed(leaves, [(10 + 60 * i, 10 + 60 * i) for i in range(count)]), leaves)


@pytest.mark.parametrize("container", [Column, Row, Stack], ids=["column", "row", "stack"])
def test_a_child_is_recorded_once_and_then_replayed(container) -> None:
    leaves = [_Leaf() for _ in range(3)]
    scene = _Scene(container(children=leaves), leaves)

    assert scene.frame() == [1, 1, 1]
    assert scene.frame() == [0, 0, 0]


def test_an_invalidation_repaints_the_changed_stack_child_only() -> None:
    scene = _stack()
    scene.frame()

    scene.leaves[1].invalidate()

    assert scene.frame() == [0, 1, 0]
    # Still on the next frame, it is recorded again.
    assert scene.frame() == [0, 1, 0]
    assert scene.frame() == [0, 0, 0]


def test_a_stack_child_that_only_moved_is_replayed_at_its_new_place() -> None:
    scene = _stack()
    scene.frame()
    assert scene.color_at(300, 20) == 0xFFFFFF

    scene.root.move(1, 280, 10)  # type: ignore[attr-defined]

    assert scene.frame() == [0, 0, 0]
    assert scene.color_at(300, 20) == 0x336699
    assert scene.color_at(80, 80) == 0xFFFFFF


def test_stack_children_that_overlap_are_replayed_in_their_order() -> None:
    leaves = [_Leaf("#FF0000"), _Leaf("#0000FF")]
    scene = _Scene(_Placed(leaves, [(10, 10), (40, 30)]), leaves)
    scene.frame()

    assert scene.frame() == [0, 0]
    assert scene.color_at(60, 40) == 0x0000FF
    assert scene.color_at(20, 20) == 0xFF0000


def test_a_stack_inside_the_clip_does_not_paint_a_child_outside_it() -> None:
    leaves = [_Leaf(), _Leaf()]
    board = _Placed(leaves, [(10, 10), (10, SIZE + 100)])
    scene = _Scene(Column(children=[board]), leaves)

    assert scene.frame() == [1, 0]
    assert leaves[1]._replay_picture is None


def test_a_child_that_overflows_a_parent_inside_the_clip_is_not_recorded() -> None:
    leaves = [_Leaf(), _Leaf()]
    scene = _Scene(_Placed(leaves, [(10, 10), (10, SIZE + 100)]), leaves)

    for _ in range(2):
        scene.canvas.clear(0xFFFFFFFF)
        layout_utils.paint_children_at_layout_rects(leaves, scene.canvas, 0, 0, inside_clip=True)

    assert leaves[0]._replay_picture is not None
    assert leaves[1]._replay_picture is None
    assert [leaf.painted for leaf in leaves] == [1, 2]


def test_a_child_recorded_with_a_widget_left_out_shows_it_once_moved_into_view() -> None:
    # The card sits at the right edge; the blue leaf, 150px to the right inside it, lies beyond the canvas.
    inside = _Leaf("#FF0000")
    beyond = _Leaf("#0000FF")
    card = _Placed([inside, beyond], [(0, 0), (150, 0)], width=100, height=50)
    board = _Placed([card], [(SIZE - 60, 10)])
    scene = _Scene(board, [inside, beyond])
    assert scene.frame() == [1, 0]

    board.move(0, 10, 10)

    scene.frame()
    assert scene.color_at(170, 20) == 0x0000FF
    assert scene.color_at(20, 20) == 0xFF0000


def test_a_child_larger_than_the_clip_is_recorded_once_the_clip_holds_it() -> None:
    leaves = [_Leaf()]
    scene = _Scene(Column(children=leaves), leaves)
    rect_type: Any = skia.Rect  # the local stub declares no factory
    scene.canvas.save()
    scene.canvas.clipRect(rect_type.MakeWH(100, 30))
    assert scene.frame() == [1]
    assert scene.frame() == [1]
    scene.canvas.restore()

    assert scene.frame() == [1]
    assert leaves[0]._replay_picture is not None
    assert scene.frame() == [0]


class _Undeclared(Box):
    def __init__(self) -> None:
        super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(50))

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        pass


def test_a_change_does_not_send_the_painter_looking_for_the_undeclared_widget_again() -> None:
    leaf = _Leaf()
    undeclared = _Undeclared()
    row = Row(children=[undeclared, leaf])
    scene = _Scene(Column(children=[row]), [leaf])
    scene.frame()

    with patch.object(layout_utils, "_subtree_replay_safe", wraps=layout_utils._subtree_replay_safe) as checks:
        for _ in range(2):
            leaf.invalidate()
            scene.frame()
            scene.frame()

    assert [call.args[0] for call in checks.call_args_list].count(row) == 0
    assert row._replay_picture is None


def test_a_child_is_recorded_once_the_undeclared_widget_below_it_is_gone() -> None:
    leaf = _Leaf()
    undeclared = _Undeclared()
    row = Row(children=[undeclared, leaf])
    scene = _Scene(Column(children=[row]), [leaf])
    scene.frame()
    assert row._replay_picture is None

    row.remove_child(undeclared)
    scene.root.layout(SIZE, SIZE)
    scene.frame()
    scene.frame()

    assert row._replay_picture is not None


def test_a_child_painted_for_its_outsets_gives_up_the_recordings_below_it_when_it_leaves() -> None:
    # The wrapper's rect is below the canvas; the translation draws its leaf 100px higher, inside.
    leaf = _Leaf()
    wrapper = Column(children=[leaf]).modifier(translate((0, -100)))
    board = _Placed([wrapper], [(10, SIZE + 40)])
    with mount(board, leak_check="off") as host:
        host.layout(SIZE, SIZE)
        scene = _Scene(board, [leaf])
        assert scene.frame() == [1]
        assert leaf._replay_picture is not None

        board.move(0, 10, SIZE + 500)
        scene.frame()

        assert leaf._replay_picture is None


def test_a_child_whose_scale_changes_every_frame_is_not_recorded() -> None:
    leaves = [_Leaf(), _Leaf()]
    scene = _Scene(Column(children=leaves), leaves)
    scene.frame()

    for step in (1, 2, 3):
        scene.canvas.save()
        scene.canvas.scale(1.0 + step / 10, 1.0 + step / 10)
        assert scene.frame() == [1, 1]
        scene.canvas.restore()
        assert leaves[0]._replay_picture is None

    # The scale it came back to is a change too; still on the frame after, it is recorded again.
    assert scene.frame() == [1, 1]
    assert leaves[0]._replay_picture is None
    assert scene.frame() == [1, 1]
    assert leaves[0]._replay_picture is not None
    assert scene.frame() == [0, 0]


def _two_rows() -> Tuple[_Scene, List[Row]]:
    leaves = [_Leaf() for _ in range(3)]
    rows = [Row(children=[leaves[0], leaves[1]]), Row(children=[leaves[2]])]
    return _Scene(Column(children=[rows[0], rows[1]]), leaves), rows


def test_no_recording_starts_inside_another() -> None:
    scene, rows = _two_rows()

    scene.frame()

    assert [row._replay_picture is not None for row in rows] == [True, True]
    assert [leaf._replay_picture is not None for leaf in scene.leaves] == [False, False, False]


def test_while_a_child_keeps_changing_the_children_beside_it_are_replayed() -> None:
    scene, rows = _two_rows()
    scene.frame()

    # Its row is painted directly, so the leaf beside it gets a recording of its own.
    scene.leaves[0].invalidate()
    assert scene.frame() == [1, 1, 0]

    for _ in range(3):
        scene.leaves[0].invalidate()
        assert scene.frame() == [1, 0, 0]
    assert rows[0]._replay_picture is None


def test_a_recording_replays_the_clean_children_below_it() -> None:
    scene, rows = _two_rows()
    scene.frame()
    scene.leaves[0].invalidate()
    scene.frame()

    # The row is still: it is recorded, and the leaf that has a recording is replayed into it.
    assert scene.frame() == [1, 0, 0]
    assert rows[0]._replay_picture is not None
    assert scene.frame() == [0, 0, 0]


def test_what_a_descendant_draws_far_outside_a_recorded_child_is_still_painted() -> None:
    # The first row is 50px tall; the leaf below it is drawn 150px lower, over the second row.
    # The Container between them reports no outsets, so the row's own bounds do not reach the leaf.
    moved = _Leaf("#FF0000")
    below = _Leaf("#0000FF")
    root = Column(
        children=[
            Row(children=[Container(Column(children=[moved]).modifier(translate((0, 150))))]),
            Row(children=[below]),
        ]
    )
    with mount(root, leak_check="off") as host:
        host.layout(SIZE, SIZE)
        scene = _Scene(root, [moved, below])

        assert scene.frame() == [1, 1]
        assert scene.color_at(50, 175) == 0xFF0000
        assert scene.frame() == [0, 0]
        assert scene.color_at(50, 175) == 0xFF0000


def test_a_stack_between_a_viewport_and_its_list_leaves_the_rows_replayed() -> None:
    leaves = [_Leaf() for _ in range(10)]
    controller = ScrollController()
    viewport = ScrollViewport(
        child=Stack([Column(children=[Row(children=[leaf]) for leaf in leaves])]),
        controller=controller,
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(100),
        height=Sizing.fixed(100),
    )
    scene = _Scene(viewport, leaves, size=100)
    scene.frame()

    controller.scroll_to(30, axis=ScrollDirection.VERTICAL)

    assert scene.frame() == [0, 0, 0, 1, 0, 0, 0, 0, 0, 0]


def test_a_scroll_inside_a_recorded_child_shows_on_the_next_frame() -> None:
    rows = [_Leaf("#FF0000"), _Leaf("#0000FF"), _Leaf("#FF0000"), _Leaf("#0000FF")]
    beside = _Leaf("#00FF00")
    controller = ScrollController()
    scrollable = VerticalScrollable(Column(children=rows), controller=controller, height=100)
    root = Column(children=[scrollable, beside])
    with mount(root, leak_check="off") as host:
        host.layout(SIZE, SIZE)
        scene = _Scene(root, [beside])
        scene.frame()
        assert scene.color_at(10, 10) == 0xFF0000

        controller.scroll_to(50, axis=ScrollDirection.VERTICAL)

        assert scene.frame() == [0]
        assert scene.color_at(10, 10) == 0x0000FF


def test_a_child_that_leaves_the_clip_gives_up_the_recordings_below_it() -> None:
    leaves = [_Leaf() for _ in range(11)]
    rows: List[Widget] = [Row(children=[leaves[0], leaves[1]]), *[Row(children=[leaf]) for leaf in leaves[2:]]]
    controller = ScrollController()
    viewport = ScrollViewport(
        child=Column(children=rows),
        controller=controller,
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(200),
        height=Sizing.fixed(100),
    )
    scene = _Scene(viewport, leaves, size=200)
    scene.frame()
    leaves[0].invalidate()
    scene.frame()
    assert leaves[1]._replay_picture is not None

    controller.scroll_to(400, axis=ScrollDirection.VERTICAL)
    scene.frame()

    assert leaves[1]._replay_picture is None


def _card(label: Any, checked: Any) -> Widget:
    row = Row(gap=8, padding=4, children=[Checkbox(checked), Text(label)])
    return Container(row, width=160, height=56).modifier(
        background("#FFE082") | border("#000000", 1) | corner_radius(6)
    )


def _hashes(replay: bool, scale: int) -> list[str]:
    class _Model:
        label = State("first")
        checked = State(False)

    model = _Model()
    cards: List[Widget] = [_card(f"card {i}", i % 2 == 0) for i in range(8)]
    cards[2] = _card(model.label, model.checked)
    inner = _Placed([_Leaf("#FF0000"), _Leaf("#0000FF")], [(0, 0), (30, 20)], width=160, height=80)
    board = _Placed([*cards, inner], [*[(10 + 35 * i, 10 + 30 * i) for i in range(8)], (200, 20)])
    root = Stack([Container(width=SIZE, height=SIZE).modifier(background("#90CAF9")), board])
    surface = _surface(SIZE * scale)
    canvas = surface.getCanvas()
    canvas.scale(scale, scale)
    out: list[str] = []

    with patch.object(layout_utils, "_REPLAY", replay):
        with mount(root, theme=MaterialThemeFactory.light("#6750A4"), leak_check="off") as host:
            host.layout(SIZE, SIZE)

            def frame() -> None:
                canvas.clear(0xFFFFFFFF)
                root.paint(canvas, 0, 0, SIZE, SIZE)
                out.append(hashlib.sha256(bytes(surface.makeImageSnapshot().tobytes())).hexdigest())

            frame()
            frame()
            for step in range(5):
                board.move(3, 40 + 23 * step, 150 - 17 * step)
                frame()
            board.move(8, 120, 200)
            frame()
            inner.move(1, 60, 5)
            frame()
            model.label.value = "second"
            model.checked.value = True
            host.settle()
            frame()
            frame()
            board.move(2, 210, 300)
            frame()
            host.push_theme(MaterialThemeFactory.dark("#6750A4"))
            frame()
            board.move(0, 5, 330)
            frame()
    return out


@pytest.mark.parametrize("scale", [1, 2])
def test_a_replayed_board_equals_a_direct_paint(scale) -> None:
    direct = _hashes(False, scale)
    replayed = _hashes(True, scale)

    assert len(set(direct)) > 8
    assert replayed == direct
