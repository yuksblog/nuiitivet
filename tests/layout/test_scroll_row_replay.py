"""The rows of a scroll viewport's content are recorded once and replayed while they are clean."""

from __future__ import annotations

import hashlib
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest
import skia

from nuiitivet.layout import layout_utils
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.layout.scroll_viewport import ScrollViewport
from nuiitivet.material.selection_controls import Checkbox
from nuiitivet.material.text import Text
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.observable import Observable
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime import app_events
from nuiitivet.scrolling import ScrollController, ScrollDirection
from nuiitivet.testing import mount
from nuiitivet.widgeting.paint_replay import replay_safe
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box

VIEW = 100


class _Leaf(Box):
    """A 100x50 leaf that declares its paint safe to replay and counts it."""

    def __init__(self, height: int = 50) -> None:
        super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(height))
        self.painted = 0

    @replay_safe
    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1


class _UndeclaredLeaf(Box):
    def __init__(self) -> None:
        super().__init__(width=Sizing.fixed(100), height=Sizing.fixed(50))
        self.painted = 0

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1


def _canvas(size: int = VIEW) -> Any:
    surface: Any = skia.Surface  # the local stub declares no constructor
    return surface(size, size).getCanvas()


class _Scene:
    def __init__(self, leaves: List[Any], *, wrap: bool = False) -> None:
        self.leaves = leaves
        self.rows = [Row(children=[leaf]) for leaf in leaves]
        self.controller = ScrollController()
        content: Widget = Column(children=self.rows)
        if wrap:
            content = Container(content)
        self.viewport = ScrollViewport(
            child=content,
            controller=self.controller,
            direction=ScrollDirection.VERTICAL,
            width=Sizing.fixed(100),
            height=Sizing.fixed(VIEW),
        )
        self.viewport.layout(100, VIEW)
        self.canvas = _canvas()

    def frame(self, offset: float | None = None) -> list[int]:
        """Paint one frame and return how often each leaf was painted in it."""
        if offset is not None:
            self.controller.scroll_to(offset, axis=ScrollDirection.VERTICAL)
        before = [leaf.painted for leaf in self.leaves]
        self.viewport.paint(self.canvas, 0, 0, 100, VIEW)
        return [leaf.painted - b for leaf, b in zip(self.leaves, before)]


def test_a_row_is_recorded_once_and_then_replayed() -> None:
    scene = _Scene([_Leaf() for _ in range(10)])

    # Rows 0-1 fill the viewport; row 2 lies in the slack band.
    assert scene.frame() == [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    assert scene.frame() == [0] * 10


def test_a_scroll_frame_paints_only_the_row_that_enters() -> None:
    scene = _Scene([_Leaf() for _ in range(10)])
    scene.frame()

    assert scene.frame(30) == [0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
    assert scene.frame(31) == [0] * 10


@pytest.mark.parametrize("wrap", [False, True], ids=["direct", "under a container"])
def test_the_content_container_is_found_through_a_passing_wrapper(wrap) -> None:
    scene = _Scene([_Leaf() for _ in range(10)], wrap=wrap)
    scene.frame()

    assert scene.frame() == [0] * 10


def test_an_invalidation_inside_a_row_repaints_that_row_only() -> None:
    scene = _Scene([_Leaf() for _ in range(10)])
    scene.frame()

    scene.leaves[1].invalidate()

    assert scene.frame() == [0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    assert scene.frame() == [0] * 10


def test_a_layout_change_inside_a_row_repaints_it() -> None:
    scene = _Scene([_Leaf() for _ in range(10)])
    scene.frame()

    scene.leaves[0].mark_needs_layout()
    scene.viewport.layout(100, VIEW)

    assert scene.frame() == [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]


def test_a_row_with_an_undeclared_widget_is_painted_every_frame() -> None:
    leaves: List[Any] = [_Leaf(), _UndeclaredLeaf(), _Leaf()]
    scene = _Scene(leaves)
    scene.frame()

    assert scene.frame() == [0, 1, 0]
    assert scene.frame(1) == [0, 1, 0]


def test_a_row_taller_than_the_viewport_is_painted_every_frame() -> None:
    scene = _Scene([_Leaf(height=300), _Leaf()])
    scene.frame()

    assert scene.frame()[0] == 1
    assert scene.rows[0]._replay_picture is None


def test_a_row_that_leaves_the_clip_gives_its_recording_up() -> None:
    scene = _Scene([_Leaf() for _ in range(10)])
    scene.frame()
    assert scene.rows[0]._replay_picture is not None

    scene.frame(400)

    assert scene.rows[0]._replay_picture is None
    # It is recorded again when it comes back.
    assert scene.frame(0)[0] == 1


def test_a_row_that_changes_every_frame_stops_being_recorded() -> None:
    scene = _Scene([_Leaf() for _ in range(4)])
    scene.frame()

    for _ in range(layout_utils._CHURN_LIMIT + 1):
        scene.leaves[0].invalidate()
        assert scene.frame()[0] == 1
    assert scene.rows[0]._replay_picture is None

    # Once it is still, it is recorded again and replayed.
    assert scene.frame()[0] == 1
    assert scene.rows[0]._replay_picture is not None
    assert scene.frame()[0] == 0


def test_a_stand_in_canvas_replays_nothing() -> None:
    scene = _Scene([_Leaf() for _ in range(3)])
    rect_type: Any = skia.Rect  # the local stub declares no factory
    scene.canvas = MagicMock()
    scene.canvas.getLocalClipBounds.return_value = rect_type.MakeWH(100, VIEW)

    assert scene.frame() == [1, 1, 1]
    assert scene.frame() == [1, 1, 1]


def test_only_the_function_that_draws_decides() -> None:
    class _Inherits(_Leaf):
        pass

    class _OverridesPaint(_Leaf):
        def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
            super().paint(canvas, x, y, width, height)

    class _OverridesAHook(_Leaf):
        def draw_children(self, canvas, x: int, y: int, width: int, height: int):
            return super().draw_children(canvas, x, y, width, height)

    assert layout_utils._type_replay_safe(_Leaf) is True
    assert layout_utils._type_replay_safe(_Inherits) is True
    assert layout_utils._type_replay_safe(_OverridesPaint) is False
    assert layout_utils._type_replay_safe(_OverridesAHook) is False
    assert layout_utils._type_replay_safe(_UndeclaredLeaf) is False


def test_a_handled_pointer_event_dirties_the_handler_and_its_ancestors() -> None:
    scene = _Scene([_Leaf() for _ in range(3)])
    scene.frame()
    assert scene.rows[1]._replay_dirty is False

    with patch.object(app_events, "_bubble_pointer_event", return_value=scene.leaves[1]):
        app_events._deliver_pointer_event(MagicMock(), scene.leaves[1], MagicMock())

    assert scene.rows[1]._replay_dirty is True
    assert scene.rows[0]._replay_dirty is False


def _hashes(replay: bool, scale: int) -> list[str]:
    class _Model:
        label = Observable("first")
        checked = Observable(False)

    model = _Model()
    rows: List[Widget] = [Row(gap=8, padding=4, children=[Checkbox(i % 2 == 0), Text(f"row {i}")]) for i in range(30)]
    rows[1] = Row(gap=8, padding=4, children=[Checkbox(model.checked), Text(model.label)])
    controller = ScrollController()
    viewport = ScrollViewport(
        child=Column(children=rows),
        controller=controller,
        direction=ScrollDirection.VERTICAL,
        width=Sizing.fixed(300),
        height=Sizing.fixed(200),
    )
    surface_type: Any = skia.Surface
    surface = surface_type(300 * scale, 200 * scale)
    canvas = surface.getCanvas()
    canvas.scale(scale, scale)
    out: list[str] = []

    with patch.object(layout_utils, "_ROW_REPLAY", replay):
        with mount(viewport, theme=MaterialThemeFactory.light("#6750A4"), leak_check="off") as host:
            host.layout(300, 200)

            def frame() -> None:
                canvas.clear(0xFFFFFFFF)
                viewport.paint(canvas, 0, 0, 300, 200)
                out.append(hashlib.sha256(bytes(surface.makeImageSnapshot().tobytes())).hexdigest())

            frame()
            for offset in (0, 1, 13, 13, 150, 700, 3):
                controller.scroll_to(offset, axis=ScrollDirection.VERTICAL)
                host.settle()
                frame()
            model.label.value = "second, and longer"
            model.checked.value = True
            host.settle()
            frame()
            frame()
            host.push_theme(MaterialThemeFactory.dark("#6750A4"))
            frame()
            controller.scroll_to(40, axis=ScrollDirection.VERTICAL)
            host.settle()
            frame()
    return out


@pytest.mark.parametrize("scale", [1, 2])
def test_a_replayed_frame_equals_a_direct_paint(scale) -> None:
    direct = _hashes(False, scale)
    replayed = _hashes(True, scale)

    assert len(set(direct)) > 5
    assert replayed == direct
